from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .district_views import _int
from .ent_com_models import Trap
from .models import Department
from .reg_models import FishPond, LandingSite
from .views import visible_activities

MONTHS = [
    (0, "Whole year"), (1, "January"), (2, "February"), (3, "March"), (4, "April"),
    (5, "May"), (6, "June"), (7, "July"), (8, "August"), (9, "September"),
    (10, "October"), (11, "November"), (12, "December"),
]


def _allowed(user, name):
    if user.is_superuser or user.role in ("admin", "dpo", "viewer"):
        return True
    return user.department_id is not None and user.department.name == name


@login_required
def map_view(request):
    user = request.user
    today = timezone.localdate()
    year = _int(request.GET.get("year"), today.year)
    month = _int(request.GET.get("month"), today.month)
    if not 0 <= month <= 12:
        month = today.month
    if not 2000 <= year <= 2100:
        year = today.year
    department = Department.objects.filter(pk=_int(request.GET.get("department"), 0)).first()

    qs = visible_activities(user).filter(
        status="approved",
        latitude__isnull=False,
        longitude__isnull=False,
        date__year=year,
    )
    if month:
        qs = qs.filter(date__month=month)
    if department:
        qs = qs.filter(department=department)

    activities = []
    for a in qs.select_related("department", "officer", "sub_county", "parish")[:1000]:
        place = str(a.sub_county) if a.sub_county else ""
        if a.parish:
            place += ", " + a.parish.name
        activities.append(
            {
                "lat": float(a.latitude),
                "lng": float(a.longitude),
                "type": a.activity_type,
                "date": a.date.strftime("%d %b %Y"),
                "sector": a.department.name,
                "officer": a.officer.get_full_name() or a.officer.username,
                "place": place,
                "url": reverse("activity_detail", args=[a.pk]),
            }
        )

    sites, ponds, traps = [], [], []
    if _allowed(user, "Fisheries"):
        for s in LandingSite.objects.filter(latitude__isnull=False, longitude__isnull=False).select_related("sub_county"):
            sites.append({"lat": float(s.latitude), "lng": float(s.longitude), "name": s.name,
                          "place": str(s.sub_county), "url": reverse("reg_detail", args=["landing-sites", s.pk])})
        for p in FishPond.objects.filter(latitude__isnull=False, longitude__isnull=False).select_related("owner", "sub_county"):
            ponds.append({"lat": float(p.latitude), "lng": float(p.longitude), "name": str(p),
                          "place": str(p.sub_county), "url": reverse("reg_detail", args=["fish-ponds", p.pk])})
    if _allowed(user, "Entomology"):
        for t in Trap.objects.filter(latitude__isnull=False, longitude__isnull=False).select_related("sub_county"):
            traps.append({"lat": float(t.latitude), "lng": float(t.longitude), "name": str(t),
                          "place": "%s (%s)" % (t.sub_county, t.get_status_display()),
                          "url": reverse("reg_detail", args=["trap-register", t.pk])})

    return render(
        request,
        "core/map.html",
        {
            "map_data": {"activities": activities, "sites": sites, "ponds": ponds, "traps": traps},
            "year": year,
            "month": month,
            "months": MONTHS,
            "departments": Department.objects.order_by("name"),
            "department_id": department.pk if department else 0,
            "count": len(activities),
        },
    )