from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from .district_views import _int
from .models import Department, Target
from .reports import fiscal_year_of, fy_label, quarter_bounds
from .views import visible_activities

ROLES = ("admin", "dpo", "head", "viewer")


def _achieved(acts, measure, start, end):
    part = acts.filter(date__gte=start, date__lte=end)
    if measure == "reached":
        s = part.aggregate(m=Sum("male"), f=Sum("female"))
        return (s["m"] or 0) + (s["f"] or 0)
    return part.count()


def _pct(done, target):
    return round(100.0 * done / target) if target else None


def _expected(target, bounds, today):
    total = 0.0
    for q, (start, end) in enumerate(bounds, 1):
        value = getattr(target, "q%d" % q)
        if end < today:
            total += value
        elif start <= today <= end:
            span = (end - start).days + 1
            total += value * ((today - start).days + 1) / float(span)
    return total


def _status(done, expected):
    if expected <= 0:
        return "-"
    ratio = done / expected
    if ratio >= 1:
        return "Ahead"
    if ratio >= 0.8:
        return "On track"
    return "Behind"


@login_required
def workplan(request):
    user = request.user
    if not (user.is_superuser or user.role in ROLES):
        return redirect("dashboard")
    today = timezone.localdate()
    fy = _int(request.GET.get("fy"), fiscal_year_of(today))
    if not 2000 <= fy <= 2100:
        fy = fiscal_year_of(today)
    department = Department.objects.filter(pk=_int(request.GET.get("department"), 0)).first()

    base = visible_activities(user).filter(status="approved")
    targets = Target.objects.filter(fiscal_year=fy).select_related("department")
    if not user.is_superuser and user.role == "head" and user.department_id:
        targets = targets.filter(department=user.department)
    elif department:
        targets = targets.filter(department=department)

    bounds = [quarter_bounds(fy, q) for q in (1, 2, 3, 4)]
    rows = []
    for t in targets:
        acts = base.filter(department=t.department)
        if t.activity_type:
            acts = acts.filter(activity_type=t.activity_type)
        quarters = []
        for q, (start, end) in enumerate(bounds, 1):
            target_q = getattr(t, "q%d" % q)
            done = _achieved(acts, t.measure, start, end)
            quarters.append(
                {"target": target_q, "done": done, "pct": _pct(done, target_q), "future": start > today}
            )
        done_total = sum(q["done"] for q in quarters)
        unit = "people reached" if t.measure == "reached" else "activities"
        status = _status(done_total, _expected(t, bounds, today))
        rows.append(
            {
                "label": "%s: %s" % (t.department.name, t.activity_type or "All activities"),
                "unit": unit,
                "quarters": quarters,
                "annual": t.annual,
                "done": done_total,
                "pct": _pct(done_total, t.annual),
                "bar": min(100, _pct(done_total, t.annual) or 0),
                "status": status,
            }
        )
    return render(
        request,
        "core/workplan.html",
        {
            "rows": rows,
            "fy": fy,
            "fy_label": fy_label(fy),
            "departments": Department.objects.order_by("name"),
            "department_id": department.pk if department else 0,
            "can_manage": user.is_staff,
            "quarter_names": ["Q1 Jul-Sep", "Q2 Oct-Dec", "Q3 Jan-Mar", "Q4 Apr-Jun"],
        },
    )