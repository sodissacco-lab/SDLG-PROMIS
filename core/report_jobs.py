"""Builds and emails the consolidated reports. Called by the daily timer (schedule_views.cron_run)
or by the Send now buttons on the Report emails page."""
import os
from datetime import date, timedelta

from django.contrib.auth import get_user_model

from .exports import make_docx, make_pdf
from .letterhead import sector_line
from .mailer import send_email
from .models import Activity, Department
from .report_registers import register_tables
from .report_registers_more import more_register_tables
from .narrative_registers import keep_nonzero
from .report_views import _tables
from .reports import build_report, fy_label, quarter_bounds, quarter_of, fiscal_year_of, resolve_period
from .schedule_models import ReportSendLog, ReportSettings

MONTHLY_WINDOW_DAYS = 15     # send last month's report in the first 15 days of a month
QUARTERLY_WINDOW_DAYS = 31   # send last quarter's report in the first 31 days of a quarter


def site_url():
    return os.environ.get("SITE_URL", "https://sorotidlg-prodn.com").rstrip("/")


def recipients():
    cfg = ReportSettings.get()
    to = [cfg.dpo_email] if cfg.dpo_email else []
    if not to:
        User = get_user_model()
        to = list(
            User.objects.filter(role="dpo", is_active=True).exclude(email="").values_list("email", flat=True)
        )
    return to, cfg.cc_list()


def _data(period, department=None):
    data = build_report(Activity.objects.all(), period, department, None, True)
    data["sector_line"] = sector_line(department, None)
    data["prepared_by"] = "SDLG-Production MIS (automatic)"
    data["photos"] = []
    data["photo_note"] = "Photographs are not attached to e-mailed copies. Open the online report to include them."
    tables = register_tables(period, department, None) + more_register_tables(period, department, None)
    data["register_tables"] = [dict(t, rows=keep_nonzero(t["rows"])) for t in tables if keep_nonzero(t["rows"])]
    return data


def _log(key, kind, label, ok, note=""):
    obj, _ = ReportSendLog.objects.get_or_create(key=key, defaults={"kind": kind})
    obj.kind, obj.label, obj.ok, obj.note = kind, label, ok, note[:300]
    obj.save()


def _done(key):
    return ReportSendLog.objects.filter(key=key, ok=True).exists()


def _mail(subject, body, attachments=None):
    to, cc = recipients()
    if not to:
        return False, "No District Production Officer email is set (Report emails page)."
    link = "\n\nOpen the system: %s\n\nSDLG-Production MIS (automatic message)" % site_url()
    return send_email(to, subject, body + link, attachments=attachments, cc=cc)


def send_monthly(year, month, force=False):
    key = "monthly-%d-%02d" % (year, month)
    if _done(key) and not force:
        return "already sent"
    period = resolve_period("monthly", date(year, month, 1), None, year, month)
    data = _data(period)
    tables = _tables(data)
    files = [
        (data["filename"] + ".pdf", make_pdf(data, tables)),
        (data["filename"] + ".docx", make_docx(data, tables)),
    ]
    s = data["summary"]
    body = (
        "Dear District Production Officer,\n\nAttached is the consolidated monthly report for %s "
        "covering all sectors (PDF and Word).\n\nApproved activities: %s\nPeople reached: %s\n"
        % (period["label"], s["activities"], s["reached"])
    )
    ok, note = _mail("Consolidated monthly report: %s" % period["label"], body, files)
    _log(key, "monthly", period["label"], ok, note)
    return "sent" if ok else "failed: " + note


def send_quarterly(fy, quarter, force=False):
    key = "quarterly-%d-%d" % (fy, quarter)
    if _done(key) and not force:
        return "already sent"
    period = resolve_period("quarterly", date.today(), None, None, None, fy, quarter)
    data = _data(period)
    tables = _tables(data)
    files = [
        (data["filename"] + ".pdf", make_pdf(data, tables)),
        (data["filename"] + ".docx", make_docx(data, tables)),
    ]
    s = data["summary"]
    body = (
        "Dear District Production Officer,\n\nAttached is the consolidated quarterly report for %s "
        "covering all sectors (PDF and Word).\n\nApproved activities: %s\nPeople reached: %s\n\n"
        "Sector quarterly reports follow in separate e-mails.\n" % (period["label"], s["activities"], s["reached"])
    )
    ok, note = _mail("Consolidated quarterly report: %s" % period["label"], body, files)
    if not ok:
        _log(key, "quarterly", period["label"], False, note)
        return "failed: " + note
    sent_sectors, failed = 0, 0
    for dept in Department.objects.order_by("name"):
        sdata = _data(period, dept)
        if not sdata["summary"]["activities"]:
            continue
        sfiles = [("%s-%s.pdf" % (sdata["filename"], dept.name.replace(" ", "-")), make_pdf(sdata, _tables(sdata)))]
        sbody = "Sector quarterly report for %s, %s.\n\nApproved activities: %s\nPeople reached: %s\n" % (
            dept.name, period["label"], sdata["summary"]["activities"], sdata["summary"]["reached"])
        ok2, _n = _mail("Sector quarterly report: %s, %s" % (dept.name, period["label"]), sbody, sfiles)
        sent_sectors += 1 if ok2 else 0
        failed += 0 if ok2 else 1
    _log(key, "quarterly", period["label"], failed == 0, "%d sector reports sent, %d failed" % (sent_sectors, failed))
    if failed == 0:
        _ministry_reminder(fy, quarter, period["label"], first=True)
    return "sent (%d sector reports)" % sent_sectors


def _ministry_reminder(fy, quarter, label, first=False):
    n = ReportSendLog.objects.filter(key__startswith="ministry-remind-%d-%d-" % (fy, quarter)).count() + 1
    body = (
        "Reminder: the %s has been compiled. Please review it and send it to the Ministry headquarters.\n\n"
        "When it has been sent, open Report emails in the system and tap \"Mark as sent to Ministry\" "
        "so these reminders stop." % label
    )
    ok, note = _mail("Reminder: send the quarterly report to the Ministry (%s)" % label, body)
    _log("ministry-remind-%d-%d-%d" % (fy, quarter, n), "reminder", label, ok, note)


def ministry_ack(fy, quarter):
    _log("ministry-%d-%d" % (fy, quarter), "ministry", "Quarter %d FY %s sent to Ministry" % (quarter, fy_label(fy)), True)


def run_due(today=None):
    """Runs everything that is due today. Safe to call every day."""
    today = today or date.today()
    cfg = ReportSettings.get()
    if not cfg.auto_enabled:
        return ["automatic sending is switched off"]
    out = []
    first_this_month = today.replace(day=1)
    if today.day <= MONTHLY_WINDOW_DAYS:
        last = first_this_month - timedelta(days=1)
        out.append("monthly %d-%02d: %s" % (last.year, last.month, send_monthly(last.year, last.month)))
    fy, q = fiscal_year_of(today), quarter_of(today)
    q_start, _e = quarter_bounds(fy, q)
    prev = q_start - timedelta(days=1)
    pfy, pq = fiscal_year_of(prev), quarter_of(prev)
    if (today - q_start).days < QUARTERLY_WINDOW_DAYS:
        out.append("quarterly FY%d Q%d: %s" % (pfy, pq, send_quarterly(pfy, pq)))
    # follow-up reminders until the Ministry copy is marked as sent
    if _done("quarterly-%d-%d" % (pfy, pq)) and not _done("ministry-%d-%d" % (pfy, pq)):
        mine = ReportSendLog.objects.filter(key__startswith="ministry-remind-%d-%d-" % (pfy, pq))
        last = mine.order_by("-sent_at").first()
        if last and mine.count() < 5 and (today - last.sent_at.date()).days >= cfg.remind_every_days:
            _ministry_reminder(pfy, pq, "quarterly report FY %s Q%d" % (fy_label(pfy), pq))
            out.append("ministry reminder sent")
    return out
