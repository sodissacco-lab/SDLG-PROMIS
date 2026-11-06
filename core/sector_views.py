import calendar
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .activity_types import BY_DEPARTMENT
from .district_views import _donut, _group, _int, _reached, _shift, _tile
from .models import Department
from .photo_models import ActivityPhoto
from .reports import build_targets
from .views import visible_activities

DISTRICT_ROLES = ("admin", "dpo", "viewer")
TARGET_ROLES = ("admin", "dpo", "head", "viewer")
COLORS = ["green", "blue", "orange", "teal", "purple", "pink", "red"]


def can_open(user, department):
    if user.is_superuser or user.role in DISTRICT_ROLES:
        return True
    return user.department_id == department.pk


@login_required
def sector(request, pk):
    user = request.user
    department = get_object_or_404(Department, pk=pk)
    if not can_open(user, department):
        return redirect("dashboard")

    today = timezone.localdate()
    year = _int(request.GET.get("year"), today.year)
    month = _int(request.GET.get("month"), today.month)
    if not 1 <= month <= 12:
        month = today.month
    if not 2000 <= year <= 2100:
        year = today.year

    base = visible_activities(user).filter(department=department)
    approved = base.filter(status="approved")
    month_qs = approved.filter(date__year=year, date__month=month)
    prev_y, prev_m = _shift(year, month, 1)
    next_y, next_m = _shift(year, month, -1)
    prev_qs = approved.filter(date__year=prev_y, date__month=prev_m)

    key_tiles = [
        _tile("Activities this month", month_qs.count(), prev_qs.count(), "blue"),
        _tile("People reached", _reached(month_qs), _reached(prev_qs), "orange"),
        {
            "label": "Activities today",
            "value": approved.filter(date=today).count(),
            "sub": "approved so far",
            "dir": "flat",
            "color": "green",
        },
        {
            "label": "Awaiting review",
            "value": base.filter(status="submitted").count(),
            "sub": "in this sector",
            "dir": "flat",
            "color": "teal",
        },
    ]

    type_names = BY_DEPARTMENT.get(department.name, [])
    cur_counts = dict(month_qs.order_by().values_list("activity_type").annotate(n=Count("id")))
    prev_counts = dict(prev_qs.order_by().values_list("activity_type").annotate(n=Count("id")))
    type_tiles = [
        _tile(name, cur_counts.get(name, 0), prev_counts.get(name, 0), COLORS[i % len(COLORS)])
        for i, name in enumerate(type_names)
    ]
    other_now = month_qs.count() - sum(cur_counts.get(n, 0) for n in type_names)
    other_prev = prev_qs.count() - sum(prev_counts.get(n, 0) for n in type_names)
    if other_now or other_prev:
        type_tiles.append(_tile("Other (office, meetings)", other_now, other_prev, "red"))

    by_type = _group(month_qs, "activity_type")
    donut_rows = by_type[:6]
    rest = by_type[6:]
    if rest:
        donut_rows.append(
            {
                "name": "Others",
                "activities": sum(r["activities"] for r in rest),
                "reached": sum(r["reached"] for r in rest),
            }
        )
    donut_total, donut_gradient = _donut(donut_rows)

    series = []
    for back in range(5, -1, -1):
        y, m = _shift(year, month, back)
        series.append(
            {
                "label": calendar.month_abbr[m],
                "activities": approved.filter(date__year=y, date__month=m).count(),
            }
        )
    maxv = max(s["activities"] for s in series) or 1
    points = []
    for i, s in enumerate(series):
        s["x"] = 20 + i * 52
        s["y"] = 110 - round(95.0 * s["activities"] / maxv)
        points.append("%d,%d" % (s["x"], s["y"]))

    officer_rows = (
        month_qs.order_by()
        .values("officer__username", "officer__first_name", "officer__last_name")
        .annotate(n=Count("id"))
        .order_by("-n")[:8]
    )
    officers = []
    for r in officer_rows:
        name = ("%s %s" % (r["officer__first_name"], r["officer__last_name"])).strip()
        officers.append({"name": name or r["officer__username"], "activities": r["n"]})

    targets = None
    if user.is_superuser or user.role in TARGET_ROLES:
        end = date(year, month, calendar.monthrange(year, month)[1])
        found = build_targets(visible_activities(user), end, department)
        if found["rows"]:
            targets = found

    photos = (
        ActivityPhoto.objects.filter(activity__in=month_qs.values("pk"))
        .select_related("activity")
        .order_by("-id")[:6]
    )

    context = {
        "department": department,
        "period": "%s %s" % (calendar.month_name[month], year),
        "prev_query": "year=%s&month=%s" % (prev_y, prev_m),
        "next_query": "year=%s&month=%s" % (next_y, next_m),
        "key_tiles": key_tiles,
        "type_tiles": type_tiles,
        "by_type": by_type[:8],
        "donut_rows": donut_rows,
        "donut_total": donut_total,
        "donut_gradient": donut_gradient,
        "by_sub_county": _group(month_qs, "sub_county__name")[:8],
        "by_parish": _group(month_qs, "parish__name")[:8],
        "trend": series,
        "line": " ".join(points),
        "officers": officers,
        "recent": month_qs.select_related("sub_county", "parish", "officer")[:8],
        "photos": photos,
        "targets": targets,
    }
    return render(request, "core/sector.html", context)