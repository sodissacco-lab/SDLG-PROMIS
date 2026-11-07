import calendar

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from . import indicators as ind
from .models import Department, Parish, SubCounty
from .views import visible_activities

DISTRICT_ROLES = ("admin", "dpo", "head", "viewer")
PALETTE = ["#2e9b4f", "#1e6fd9", "#f39c12", "#7b4bc7", "#d8456b", "#14a89d", "#6b7c93"]


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _shift(year, month, back):
    index = year * 12 + (month - 1) - back
    return index // 12, index % 12 + 1


def _reached(qs):
    s = qs.aggregate(m=Sum("male"), f=Sum("female"))
    return (s["m"] or 0) + (s["f"] or 0)


def _group(qs, field):
    rows = (
        qs.order_by()
        .values(field)
        .annotate(n=Count("id"), m=Sum("male"), f=Sum("female"))
        .order_by("-n")
    )
    out = [
        {
            "name": r[field] or "Not specified",
            "activities": r["n"],
            "reached": (r["m"] or 0) + (r["f"] or 0),
        }
        for r in rows
    ]
    top = max([r["activities"] for r in out] or [0]) or 1
    for r in out:
        r["width"] = round(100.0 * r["activities"] / top)
    return out


def _stats(qs):
    fisheries = qs.filter(department__name="Fisheries")
    return {
        "activities": qs.count(),
        "extension": qs.filter(activity_type__in=ind.EXTENSION_VISIT_TYPES).count(),
        "pdm_trained": _reached(
            qs.filter(
             activity_type__in=ind.PDM_TRAINING_TYPES
            )
        ),
        "fish_farmers": _reached(
            fisheries.filter(activity_type__in=ind.FISH_FARMER_TYPES)
        ),
        "fisheries_inspections": fisheries.filter(
            activity_type__in=ind.FISHERIES_INSPECTION_TYPES
        ).count(),
        "crop": qs.filter(department__name="Crops").count(),
        "vet": qs.filter(department__name="Veterinary").count(),
        "subcounties": qs.exclude(sub_county=None)
        .order_by()
        .values("sub_county")
        .distinct()
        .count(),
        "parishes": qs.exclude(parish=None)
        .order_by()
        .values("parish")
        .distinct()
        .count(),
    }


def _tile(label, cur, prev, color):
    if prev and not cur:
        direction, sub = "flat", "none this month"
    elif prev:
        pct = round(100.0 * (cur - prev) / prev)
        direction = "up" if pct > 0 else "down" if pct < 0 else "flat"
        sub = "%d%% vs last month" % abs(pct)
    elif cur:
        direction, sub = "up", "new this month"
    else:
        direction, sub = "flat", "no data yet"
    return {"label": label, "value": cur, "sub": sub, "dir": direction, "color": color}


def _donut(rows):
    total = sum(r["activities"] for r in rows)
    parts = []
    start = 0.0
    for i, r in enumerate(rows):
        r["color"] = PALETTE[i % len(PALETTE)]
        share = 100.0 * r["activities"] / total if total else 0
        r["pct"] = round(share)
        parts.append("%s %.2f%% %.2f%%" % (r["color"], start, start + share))
        start += share
    gradient = "conic-gradient(%s)" % ", ".join(parts) if parts else "#e6ece6"
    return total, gradient


@login_required
def district(request):
    user = request.user
    if not (user.is_superuser or user.role in DISTRICT_ROLES):
        return redirect("dashboard")

    today = timezone.localdate()
    year = _int(request.GET.get("year"), today.year)
    month = _int(request.GET.get("month"), today.month)
    if not 1 <= month <= 12:
        month = today.month
    if not 2000 <= year <= 2100:
        year = today.year

    base = visible_activities(user)
    approved = base.filter(status="approved")
    month_qs = approved.filter(date__year=year, date__month=month)
    prev_y, prev_m = _shift(year, month, 1)
    next_y, next_m = _shift(year, month, -1)
    prev_qs = approved.filter(date__year=prev_y, date__month=prev_m)

    cur = _stats(month_qs)
    prev = _stats(prev_qs)
    pending = base.filter(status="submitted").count()
    today_count = approved.filter(date=today).count()
    total_sc = SubCounty.objects.count()
    total_parishes = Parish.objects.count()

    key_tiles = [
        _tile("Activities this month", cur["activities"], prev["activities"], "blue"),
        {
            "label": "Activities today",
            "value": today_count,
            "sub": "approved so far",
            "dir": "flat",
            "color": "green",
        },
        _tile("People reached", _reached(month_qs), _reached(prev_qs), "orange"),
        {
            "label": "Awaiting review",
            "value": pending,
            "sub": "submitted by officers",
            "dir": "flat",
            "color": "teal",
        },
    ]
    indicator_tiles = [
        _tile("Extension visits", cur["extension"], prev["extension"], "green"),
        _tile("PDM beneficiaries trained", cur["pdm_trained"], prev["pdm_trained"], "orange"),
        _tile("Fish farmers reached", cur["fish_farmers"], prev["fish_farmers"], "teal"),
        _tile("Fisheries inspections", cur["fisheries_inspections"], prev["fisheries_inspections"], "purple"),
        _tile("Crop activities", cur["crop"], prev["crop"], "pink"),
        _tile("Veterinary activities", cur["vet"], prev["vet"], "red"),
        {
            "label": "Sub-counties covered",
            "value": cur["subcounties"],
            "sub": "of %d" % total_sc,
            "dir": "flat",
            "color": "blue",
        },
        {
            "label": "Parishes covered",
            "value": cur["parishes"],
            "sub": "of %d" % total_parishes,
            "dir": "flat",
            "color": "teal",
        },
    ]

    by_department = _group(month_qs, "department__name")
    donut_total, donut_gradient = _donut(by_department)

    series = []
    for back in range(5, -1, -1):
        y, m = _shift(year, month, back)
        part = approved.filter(date__year=y, date__month=m)
        series.append(
            {
                "label": calendar.month_abbr[m],
                "activities": part.count(),
                "extension": part.filter(
                    activity_type__in=ind.EXTENSION_VISIT_TYPES
                ).count(),
            }
        )
    maxv = max([max(s["activities"], s["extension"]) for s in series] or [0]) or 1
    pts_a, pts_e = [], []
    for i, s in enumerate(series):
        s["x"] = 20 + i * 52
        s["ya"] = 110 - round(95.0 * s["activities"] / maxv)
        s["ye"] = 110 - round(95.0 * s["extension"] / maxv)
        pts_a.append("%d,%d" % (s["x"], s["ya"]))
        pts_e.append("%d,%d" % (s["x"], s["ye"]))

    officer_rows = (
        month_qs.order_by()
        .values("officer__username", "officer__first_name", "officer__last_name")
        .annotate(n=Count("id"), m=Sum("male"), f=Sum("female"))
        .order_by("-n")[:8]
    )
    officers = []
    for r in officer_rows:
        name = ("%s %s" % (r["officer__first_name"], r["officer__last_name"])).strip()
        officers.append(
            {
                "name": name or r["officer__username"],
                "activities": r["n"],
                "reached": (r["m"] or 0) + (r["f"] or 0),
            }
        )

    context = {
        "active": "district",
        "period": "%s %s" % (calendar.month_name[month], year),
        "prev_query": "year=%s&month=%s" % (prev_y, prev_m),
        "next_query": "year=%s&month=%s" % (next_y, next_m),
        "key_tiles": key_tiles,
        "indicator_tiles": indicator_tiles,
        "by_department": by_department,
        "donut_total": donut_total,
        "donut_gradient": donut_gradient,
        "by_sub_county": _group(month_qs, "sub_county__name")[:8],
        "by_type": _group(month_qs, "activity_type")[:8],
        "trend": series,
        "line_activities": " ".join(pts_a),
        "line_extension": " ".join(pts_e),
        "officers": officers,
        "recent": month_qs.select_related(
            "department", "sub_county", "parish", "officer"
        )[:8],
        "departments": Department.objects.order_by("name"),
        "pending": pending,
        "is_reviewer": user.is_superuser or user.role in ("admin", "dpo", "head"),
        "can_admin": user.is_staff,
    }
    return render(request, "core/district.html", context)
