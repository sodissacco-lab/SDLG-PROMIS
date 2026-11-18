import hmac
import os
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from .mailer import is_configured, send_email
from .report_jobs import (
    ministry_ack,
    recipients,
    run_due,
    send_monthly,
    send_quarterly,
    site_url,
)
from .reports import fiscal_year_of, quarter_of
from .schedule_models import ReportSendLog, ReportSettings


def _allowed(user):
    return user.is_superuser or getattr(user, "role", "") in ("admin", "dpo")


def _int(v, d=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return d


@login_required
def report_emails(request):
    if not _allowed(request.user):
        messages.error(request, "Only the administrator or the District Production Officer can open this page.")
        return redirect("dashboard")
    cfg = ReportSettings.get()
    today = date.today()
    if request.method == "POST":
        act = request.POST.get("action")
        if act == "save":
            cfg.dpo_email = request.POST.get("dpo_email", "").strip()
            cfg.cc_emails = request.POST.get("cc_emails", "").strip()
            cfg.auto_enabled = request.POST.get("auto_enabled") == "on"
            cfg.remind_every_days = max(1, _int(request.POST.get("remind_every_days"), 7))
            cfg.save()
            messages.success(request, "Saved.")
        elif act == "test":
            to, cc = recipients()
            ok, note = send_email(to, "Test message from SDLG-Production MIS",
                                  "This is a test. If you can read it, report e-mails will reach this address.\n%s" % site_url(), cc=cc) if to else (False, "Enter the DPO email first.")
            (messages.success if ok else messages.error)(request, "Test email sent." if ok else "Test failed: %s" % note)
        elif act == "send_monthly":
            res = send_monthly(_int(request.POST.get("year"), today.year), _int(request.POST.get("month"), today.month), force=True)
            messages.info(request, "Monthly report: %s" % res)
        elif act == "send_quarterly":
            res = send_quarterly(_int(request.POST.get("fy"), fiscal_year_of(today)), _int(request.POST.get("quarter"), quarter_of(today)), force=True)
            messages.info(request, "Quarterly reports: %s" % res)
        elif act == "backup":
            from .backup_drive import run_backup
            messages.info(request, "Backup: %s" % run_backup(force=True))
        elif act == "ministry":
            ministry_ack(_int(request.POST.get("fy"), fiscal_year_of(today)), _int(request.POST.get("quarter"), quarter_of(today)))
            messages.success(request, "Marked as sent to the Ministry. Reminders for that quarter will stop.")
        return redirect("report_emails")
    token_set = bool(os.environ.get("CRON_TOKEN"))
    to, _cc = recipients()
    return render(request, "core/report_emails.html", {
        "cfg": cfg,
        "log": ReportSendLog.objects.all()[:25],
        "mail_ready": is_configured(),
        "backup_ready": __import__("core.backup_drive", fromlist=["x"]).is_configured(),
        "token_set": token_set,
        "cron_url": "%s/cron/run/YOUR_CRON_TOKEN/" % site_url(),
        "effective_to": ", ".join(to),
        "year": today.year, "month": today.month,
        "fy": fiscal_year_of(today), "quarter": quarter_of(today),
        "months": list(range(1, 13)),
    })


def cron_run(request, token):
    """Hit once a day by cron-job.org. The secret token in the address is the password."""
    expected = os.environ.get("CRON_TOKEN", "")
    if not expected or not hmac.compare_digest(expected, token):
        raise Http404
    try:
        return JsonResponse({"ok": True, "did": run_due()})
    except Exception as exc:  # report the problem to the timer instead of a blank 500
        return JsonResponse({"ok": False, "error": str(exc)[:300]}, status=500)
