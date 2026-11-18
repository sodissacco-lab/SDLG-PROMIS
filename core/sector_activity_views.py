import csv
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Activity
from .views import is_reviewer, visible_activities

PAGE = 40


def _month(value, today):
    """'YYYY-MM' -> (year, month); '' or 'all' -> None; bad text -> this month."""
    if value == "all":
        return None
    try:
        y, m = value.split("-")
        y, m = int(y), int(m)
        if 2000 <= y <= 2100 and 1 <= m <= 12:
            return y, m
    except (ValueError, AttributeError):
        pass
    return today.year, today.month


@login_required
def sector_activities(request):
    """Every activity of the head's sector (all sectors for DPO and admin),
    submitted, approved or returned. Drafts are the officer's own work in progress."""
    user = request.user
    if not is_reviewer(user):
        return redirect("dashboard")

    today = timezone.localdate()
    base = visible_activities(user).exclude(status="draft")
    get = request.GET

    ym = _month(get.get("month", today.strftime("%Y-%m")), today)
    qs = base
    if ym:
        qs = qs.filter(date__year=ym[0], date__month=ym[1])

    officer = get.get("officer", "")
    if officer.isdigit():
        qs = qs.filter(officer_id=int(officer))
    status = get.get("status", "")
    if status in dict(Activity.STATUS) and status != "draft":
        qs = qs.filter(status=status)
    else:
        status = ""
    atype = get.get("type", "")
    if atype:
        qs = qs.filter(activity_type=atype)
    else:
        atype = ""

    qs = qs.select_related("officer", "department", "sub_county", "parish").order_by("-date", "-pk")

    if get.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="sector-activities.csv"'
        w = csv.writer(resp)
        w.writerow(["Date", "Officer", "Sector", "Activity", "Sub-county", "Parish", "Village",
                    "Male", "Female", "Status"])
        for a in qs:
            w.writerow([
                a.date.isoformat(), a.officer.get_full_name() or a.officer.username,
                a.department, a.activity_label,
                "District HQ" if a.at_district_hq else a.sub_county or "",
                a.parish.name if a.parish else "", a.village or "",
                a.male or 0, a.female or 0, a.get_status_display(),
            ])
        return resp

    totals = qs.aggregate(m=Sum("male"), f=Sum("female"))
    people = (totals["m"] or 0) + (totals["f"] or 0)

    User = get_user_model()
    officers = User.objects.filter(pk__in=base.values("officer")).order_by("first_name", "last_name", "username")
    types = sorted(set(base.values_list("activity_type", flat=True)))

    page = Paginator(qs, PAGE).get_page(get.get("page"))
    keep = get.copy()
    keep.pop("page", None)

    return render(request, "core/sector_activities.html", {
        "page": page,
        "count": page.paginator.count,
        "people": people,
        "officers": officers,
        "types": types,
        "statuses": [(v, l) for v, l in Activity.STATUS if v != "draft"],
        "month_value": "" if ym is None else "%04d-%02d" % ym,
        "all_months": ym is None,
        "f_officer": officer,
        "f_status": status,
        "f_type": atype,
        "query": keep.urlencode(),
        "title": ("%s sector activities" % user.department.name)
        if (user.role == "head" and not user.is_superuser and user.department_id)
        else "All activities",
    })
