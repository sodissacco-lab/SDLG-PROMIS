import calendar
from datetime import date, timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from .models import Target

KINDS = [
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("annual", "Annual"),
]
QUARTERS = [
    (1, "Quarter 1 (Jul - Sep)"),
    (2, "Quarter 2 (Oct - Dec)"),
    (3, "Quarter 3 (Jan - Mar)"),
    (4, "Quarter 4 (Apr - Jun)"),
]
_QUARTER_START = {1: 7, 2: 10, 3: 1, 4: 4}


def fiscal_year_of(d):
    return d.year if d.month >= 7 else d.year - 1


def quarter_of(d):
    if d.month >= 7:
        return 1 if d.month <= 9 else 2
    return 3 if d.month <= 3 else 4


def fy_label(fy):
    return "%d/%s" % (fy, str(fy + 1)[-2:])


def quarter_bounds(fy, quarter):
    start_month = _QUARTER_START[quarter]
    year = fy if quarter in (1, 2) else fy + 1
    end_month = start_month + 2
    start = date(year, start_month, 1)
    end = date(year, end_month, calendar.monthrange(year, end_month)[1])
    return start, end


def resolve_period(kind, today, day=None, year=None, month=None, fy=None, quarter=None):
    if kind == "daily":
        d = day or today
        return {
            "kind": kind,
            "start": d,
            "end": d,
            "title": "DAILY ACTIVITY REPORT",
            "label": d.strftime("%A %d %B %Y"),
            "filename": "Daily-report-%s" % d.isoformat(),
        }
    if kind == "weekly":
        d = day or today
        start = d - timedelta(days=d.weekday())
        end = start + timedelta(days=6)
        return {
            "kind": kind,
            "start": start,
            "end": end,
            "title": "WEEKLY ACTIVITY SUMMARY",
            "label": "%s to %s"
            % (start.strftime("%A %d %B %Y"), end.strftime("%A %d %B %Y")),
            "filename": "Weekly-report-%s" % start.isoformat(),
        }
    if kind == "quarterly":
        fy = fy or fiscal_year_of(today)
        quarter = quarter if quarter in (1, 2, 3, 4) else quarter_of(today)
        start, end = quarter_bounds(fy, quarter)
        return {
            "kind": kind,
            "start": start,
            "end": end,
            "title": "QUARTERLY PERFORMANCE REPORT",
            "label": "Quarter %d, FY %s (%s - %s)"
            % (quarter, fy_label(fy), start.strftime("%B"), end.strftime("%B %Y")),
            "filename": "Quarterly-report-FY%d-Q%d" % (fy, quarter),
        }
    if kind == "annual":
        fy = fy or fiscal_year_of(today)
        return {
            "kind": kind,
            "start": date(fy, 7, 1),
            "end": date(fy + 1, 6, 30),
            "title": "ANNUAL PERFORMANCE REPORT",
            "label": "FY %s (July %d - June %d)" % (fy_label(fy), fy, fy + 1),
            "filename": "Annual-report-FY%d" % fy,
        }
    year = year or today.year
    month = month or today.month
    return {
        "kind": "monthly",
        "start": date(year, month, 1),
        "end": date(year, month, calendar.monthrange(year, month)[1]),
        "title": "MONTHLY PROGRESS REPORT",
        "label": "%s %s" % (calendar.month_name[month], year),
        "filename": "Production-report-%s-%02d" % (year, month),
    }


def percent(achieved, target):
    if not target:
        return "-"
    return "%.1f%%" % (100.0 * achieved / target)


def build_targets(base, end, department=None, annual_only=False):
    fy = fiscal_year_of(end)
    quarter = quarter_of(end)
    q_start, _ = quarter_bounds(fy, quarter)
    fy_start = date(fy, 7, 1)
    base = base.filter(status="approved")
    targets = Target.objects.filter(fiscal_year=fy).select_related("department")
    if department:
        targets = targets.filter(department=department)

    rows = []
    for t in targets:
        acts = base.filter(department=t.department)
        if t.activity_type:
            acts = acts.filter(activity_type=t.activity_type)

        def achieved(start):
            part = acts.filter(date__gte=start, date__lte=end)
            if t.measure == "reached":
                s = part.aggregate(m=Sum("male"), f=Sum("female"))
                return (s["m"] or 0) + (s["f"] or 0)
            return part.count()

        unit = "people reached" if t.measure == "reached" else "activities"
        label = "%s: %s (%s)" % (
            t.department.name,
            t.activity_type or "All activities",
            unit,
        )
        y_done = achieved(fy_start)
        if annual_only:
            rows.append([label, t.annual, y_done, percent(y_done, t.annual)])
        else:
            q_target = getattr(t, "q%d" % quarter)
            q_done = achieved(q_start)
            rows.append(
                [
                    label,
                    q_target,
                    q_done,
                    percent(q_done, q_target),
                    t.annual,
                    y_done,
                    percent(y_done, t.annual),
                ]
            )

    if annual_only:
        return {
            "title": "Performance against annual targets (FY %s)" % fy_label(fy),
            "header": ["Indicator", "Annual target", "Achieved", "Achievement %"],
            "weights": [0.46, 0.18, 0.18, 0.18],
            "rows": rows,
        }
    return {
        "title": "Performance against targets (FY %s, quarter %d, to %s)"
        % (fy_label(fy), quarter, end.strftime("%d %B %Y")),
        "header": [
            "Indicator",
            "Quarter target",
            "Quarter achieved",
            "Quarter %",
            "Annual target",
            "Year to date",
            "Annual %",
        ],
        "weights": [0.28, 0.12, 0.12, 0.10, 0.13, 0.13, 0.12],
        "rows": rows,
    }


def build_report(qs, period, department=None, sub_county=None, include_targets=False):
    base_qs = qs
    qs = qs.filter(status="approved", date__gte=period["start"], date__lte=period["end"])
    if department:
        qs = qs.filter(department=department)
    if sub_county:
        qs = qs.filter(sub_county=sub_county)

    totals = qs.aggregate(
        m=Sum("male"), f=Sum("female"), y=Sum("youth"), p=Sum("pwd")
    )
    men = totals["m"] or 0
    women = totals["f"] or 0
    summary = {
        "activities": qs.count(),
        "men": men,
        "women": women,
        "reached": men + women,
        "youth": totals["y"] or 0,
        "pwd": totals["p"] or 0,
    }

    def group(field):
        rows = (
            qs.order_by()
            .values(field)
            .annotate(n=Count("id"), m=Sum("male"), f=Sum("female"))
            .order_by(field)
        )
        return [
            {
                "name": r[field] or "Not specified",
                "activities": r["n"],
                "reached": (r["m"] or 0) + (r["f"] or 0),
            }
            for r in rows
        ]

    breakdown = None
    kind = period["kind"]
    if kind in ("quarterly", "annual"):
        month_rows = (
            qs.order_by()
            .annotate(mon=TruncMonth("date"))
            .values("mon")
            .annotate(n=Count("id"), m=Sum("male"), f=Sum("female"))
            .order_by("mon")
        )
        breakdown = {
            "title": "By month",
            "label": "Month",
            "rows": [
                {
                    "name": r["mon"].strftime("%B %Y"),
                    "activities": r["n"],
                    "reached": (r["m"] or 0) + (r["f"] or 0),
                }
                for r in month_rows
            ],
        }
    elif kind == "weekly":
        day_rows = (
            qs.order_by()
            .values("date")
            .annotate(n=Count("id"), m=Sum("male"), f=Sum("female"))
            .order_by("date")
        )
        breakdown = {
            "title": "By day",
            "label": "Day",
            "rows": [
                {
                    "name": r["date"].strftime("%A %d %b"),
                    "activities": r["n"],
                    "reached": (r["m"] or 0) + (r["f"] or 0),
                }
                for r in day_rows
            ],
        }

    activities = []
    items = qs.select_related("department", "sub_county", "parish", "officer")
    for a in items.order_by("date", "id"):
        if a.at_district_hq:
            place = "District HQ"
        else:
            place = str(a.sub_county) if a.sub_county else "Not specified"
            if a.parish and a.parish.name.strip().lower() != place.strip().lower():
                place += ", " + a.parish.name
        when = ""
        if a.start_time:
            when = a.start_time.strftime("%H:%M")
            if a.end_time:
                when += "-" + a.end_time.strftime("%H:%M")
        activities.append(
            {
                "date": a.date.strftime("%d %b %Y"),
                "time": when or "-",
                "type": a.activity_label,
                "department": str(a.department),
                "officer": a.officer.get_full_name() or a.officer.username,
                "location": place,
                "reached": a.total_beneficiaries,
            }
        )

    by_type = {}
    for t, other, m, f in qs.order_by().values_list(
        "activity_type", "other_activity", "male", "female"
    ):
        name = other if (t or "").startswith("Other") and other else (t or "Not specified")
        row = by_type.setdefault(name, {"name": name, "activities": 0, "reached": 0})
        row["activities"] += 1
        row["reached"] += (m or 0) + (f or 0)
    by_type = sorted(by_type.values(), key=lambda r: r["name"])

    parts = []
    if department:
        parts.append("Department: " + department.name)
    if sub_county:
        parts.append("Sub-county: " + sub_county.name)

    targets = None
    if include_targets and kind in ("monthly", "quarterly", "annual"):
        targets = build_targets(
            base_qs, period["end"], department, annual_only=(kind == "annual")
        )

    return {
        "title": period["title"],
        "period": period["label"],
        "filters": " | ".join(parts),
        "filename": period["filename"],
        "summary": summary,
        "by_department": group("department__name"),
        "by_sub_county": group("sub_county__name"),
        "by_type": by_type,
        "breakdown": breakdown,
        "activities": activities,
        "targets": targets,
    }
