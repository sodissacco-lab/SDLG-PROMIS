import calendar

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from . import indicators as ind
from .district_views import _donut, _group, _int, _reached, _shift, _stats, _tile
from .models import Activity, Department, Parish, SubCounty
from .views import reviewable_activities

COUNTED = ("submitted", "approved")


@login_required
def my_dashboard(request):
    user = request.user
    today = timezone.localdate()
    year = _int(request.GET.get("year"), today.year)
    month = _int(request.GET.get("month"), today.month)
    if not 1 <= month <= 12:
        month = today.month
    if not 2000 <= year <= 2100:
        year = today.year

    mine = Activity.objects.filter(officer=user)
    counted = mine.filter(status__in=COUNTED)
    month_qs = counted.filter(date__year=year, date__month=month)
    prev_y, prev_m = _shift(year, month, 1)
    next_y, next_m = _shift(year, month, -1)
    prev_qs = counted.filter(date__year=prev_y, date__month=prev_m)

    cur = _stats(month_qs)
    prev = _stats(prev_qs)
    list_url = reverse("activity_list")
    drafts = mine.filter(status="draft").count()
    returned = mine.filter(status="returned").count()
    waiting = mine.filter(status="submitted").count()

    key_tiles = [
        _tile("Activities this month", cur["activities"], prev["activities"], "blue"),
        _tile("People reached", _reached(month_qs), _reached(prev_qs), "orange"),
        {
            "label": "Activities today",
            "value": counted.filter(date=today).count(),
            "sub": "submitted or approved",
            "dir": "flat",
            "color": "green",
        },
        {
            "label": "Approved this month",
            "value": month_qs.filter(status="approved").count(),
            "sub": "signed off by supervisor",
            "dir": "flat",
            "color": "teal",
        },
    ]
    action_tiles = [
        {
            "label": "Drafts to finish",
            "value": drafts,
            "sub": "tap to open",
            "dir": "flat",
            "color": "grey",
            "href": list_url + "?status=draft",
        },
        {
            "label": "Returned for correction",
            "value": returned,
            "sub": "needs your attention",
            "dir": "flat",
            "color": "red",
            "href": list_url + "?status=returned",
        },
        {
            "label": "Awaiting review",
            "value": waiting,
            "sub": "with your supervisor",
            "dir": "flat",
            "color": "orange",
            "href": list_url + "?status=submitted",
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
            "sub": "of %d" % SubCounty.objects.count(),
            "dir": "flat",
            "color": "blue",
        },
        {
            "label": "Parishes covered",
            "value": cur["parishes"],
            "sub": "of %d" % Parish.objects.count(),
            "dir": "flat",
            "color": "teal",
        },
    ]

    # only show indicators that have something to report
    indicator_tiles = [
        t for t in indicator_tiles
        if t["value"] or t["label"].endswith("covered")
    ]

    by_department = _group(month_qs, "department__name")
    donut_total, donut_gradient = _donut(by_department)

    series = []
    for back in range(5, -1, -1):
        y, m = _shift(year, month, back)
        part = counted.filter(date__year=y, date__month=m)
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

    context = {
        "active": "mine",
        "period": "%s %s" % (calendar.month_name[month], year),
        "prev_query": "year=%s&month=%s" % (prev_y, prev_m),
        "next_query": "year=%s&month=%s" % (next_y, next_m),
        "key_tiles": key_tiles,
        "action_tiles": action_tiles,
        "indicator_tiles": indicator_tiles,
        "returned_count": returned,
        "returned_url": list_url + "?status=returned",
        "by_department": by_department,
        "donut_total": donut_total,
        "donut_gradient": donut_gradient,
        "by_sub_county": _group(month_qs, "sub_county__name")[:8],
        "trend": series,
        "line_activities": " ".join(pts_a),
        "line_extension": " ".join(pts_e),
        "recent": mine.select_related("department", "sub_county", "parish")[:8],
        "departments": Department.objects.order_by("name"),
        "pending": reviewable_activities(user).count(),
        "is_reviewer": user.is_superuser or user.role in ("admin", "dpo", "head"),
        "can_admin": user.is_staff,
    }
    return render(request, "core/my_dashboard.html", context)
