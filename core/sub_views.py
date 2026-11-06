import calendar

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .district_views import _donut, _group, _int, _reached, _shift, _tile
from .models import Activity, Parish, SubCounty
from .pdm_models import PDMBeneficiary, PDMGroup
from .photo_models import ActivityPhoto
from .sectors import other_departments, sectors

DISTRICT_ROLES = ("admin", "dpo", "head", "viewer")
COLORS = ["green", "blue", "orange", "teal", "purple", "pink", "red"]


def own_subcounty(user):
    if user.role == "subcounty" and user.sub_county:
        return SubCounty.objects.filter(name__iexact=user.sub_county.strip()).first()
    return None


def can_open(user, sub_county):
    if user.is_superuser or user.role in DISTRICT_ROLES:
        return True
    mine = own_subcounty(user)
    return mine is not None and mine.pk == sub_county.pk


def _scope(user, qs):
    if not user.is_superuser and user.role == "head" and user.department_id:
        return qs.filter(department=user.department)
    return qs


def _month(request):
    today = timezone.localdate()
    year = _int(request.GET.get("year"), today.year)
    month = _int(request.GET.get("month"), today.month)
    if not 1 <= month <= 12:
        month = today.month
    if not 2000 <= year <= 2100:
        year = today.year
    return today, year, month


@login_required
def subcounty_list(request):
    user = request.user
    if not (user.is_superuser or user.role in DISTRICT_ROLES):
        mine = own_subcounty(user)
        if mine:
            return redirect("subcounty", pk=mine.pk)
        return redirect("dashboard")

    today, year, month = _month(request)
    prev_y, prev_m = _shift(year, month, 1)
    next_y, next_m = _shift(year, month, -1)
    qs = _scope(
        user,
        Activity.objects.filter(status="approved", date__year=year, date__month=month),
    )
    rows = {
        r["sub_county"]: r
        for r in qs.order_by()
        .values("sub_county")
        .annotate(n=Count("id"), m=Sum("male"), f=Sum("female"))
    }
    parish_counts = dict(
        Parish.objects.order_by().values_list("sub_county").annotate(n=Count("id"))
    )
    cards = []
    for sc in SubCounty.objects.order_by("name"):
        r = rows.get(sc.pk)
        cards.append(
            {
                "sc": sc,
                "activities": r["n"] if r else 0,
                "reached": ((r["m"] or 0) + (r["f"] or 0)) if r else 0,
                "parishes": parish_counts.get(sc.pk, 0),
            }
        )
    return render(
        request,
        "core/subcounty_list.html",
        {
            "cards": cards,
            "period": "%s %s" % (calendar.month_name[month], year),
            "query": "year=%s&month=%s" % (year, month),
            "prev_query": "year=%s&month=%s" % (prev_y, prev_m),
            "next_query": "year=%s&month=%s" % (next_y, next_m),
        },
    )


@login_required
def subcounty(request, pk):
    user = request.user
    sc = get_object_or_404(SubCounty, pk=pk)
    if not can_open(user, sc):
        return redirect("dashboard")

    today, year, month = _month(request)
    prev_y, prev_m = _shift(year, month, 1)
    next_y, next_m = _shift(year, month, -1)

    scoped = _scope(user, Activity.objects.filter(sub_county=sc))
    approved = scoped.filter(status="approved")
    month_qs = approved.filter(date__year=year, date__month=month)
    prev_qs = approved.filter(date__year=prev_y, date__month=prev_m)

    totals = month_qs.aggregate(
        m=Sum("male"), f=Sum("female"), y=Sum("youth"), p=Sum("pwd")
    )
    men, women = totals["m"] or 0, totals["f"] or 0
    reached = men + women

    def share(part):
        return "%d%%" % round(100.0 * part / reached) if reached else "-"

    parish_list = list(Parish.objects.filter(sub_county=sc).order_by("name"))
    stats = {
        r["parish"]: r
        for r in month_qs.order_by()
        .values("parish")
        .annotate(n=Count("id"), m=Sum("male"), f=Sum("female"))
    }
    last = dict(
        approved.exclude(parish=None)
        .order_by()
        .values_list("parish")
        .annotate(last=Max("date"))
    )
    parish_rows = []
    covered = 0
    for p in parish_list:
        r = stats.get(p.pk)
        if r:
            covered += 1
        parish_rows.append(
            {
                "name": p.name,
                "activities": r["n"] if r else 0,
                "reached": ((r["m"] or 0) + (r["f"] or 0)) if r else 0,
                "last": last.get(p.pk),
            }
        )
    top = max([r["activities"] for r in parish_rows] or [0]) or 1
    bars = sorted(parish_rows, key=lambda r: -r["activities"])[:8]
    for r in bars:
        r["width"] = round(100.0 * r["activities"] / top)

    counts = dict(
        Activity.objects.filter(status="approved", date__year=year, date__month=month)
        .order_by()
        .values_list("sub_county")
        .annotate(n=Count("id"))
    )
    mine_n = counts.get(sc.pk, 0)
    rank = 1 + sum(
        1 for k, v in counts.items() if k not in (None, sc.pk) and v > mine_n
    )

    coverage_sub = (
        "%d%% of parishes" % round(100.0 * covered / len(parish_list))
        if parish_list
        else "no parishes registered"
    )
    key_tiles = [
        _tile("Activities this month", month_qs.count(), prev_qs.count(), "blue"),
        _tile("People reached", reached, _reached(prev_qs), "orange"),
        {
            "label": "Parish coverage",
            "value": "%d of %d" % (covered, len(parish_list)),
            "sub": coverage_sub,
            "dir": "flat",
            "color": "green",
        },
        {
            "label": "District ranking",
            "value": "%d of %d" % (rank, SubCounty.objects.count()),
            "sub": "by approved activities",
            "dir": "flat",
            "color": "teal",
        },
    ]
    people_tiles = [
        {"label": "Women reached", "value": share(women), "sub": "%d women" % women, "dir": "flat", "color": "pink"},
        {"label": "Youth", "value": share(totals["y"] or 0), "sub": "%d youth" % (totals["y"] or 0), "dir": "flat", "color": "purple"},
        {"label": "Persons with disability", "value": share(totals["p"] or 0), "sub": "%d persons" % (totals["p"] or 0), "dir": "flat", "color": "red"},
    ]

    cur_by = dict(month_qs.order_by().values_list("department__name").annotate(n=Count("id")))
    prev_by = dict(prev_qs.order_by().values_list("department__name").annotate(n=Count("id")))
    sector_tiles = [
        _tile(d.name, cur_by.get(d.name, 0), prev_by.get(d.name, 0), COLORS[i % len(COLORS)])
        for i, d in enumerate(sectors() + other_departments())
    ]
    sector_tiles.append(
        _tile(
            "PDM programme activities",
            month_qs.filter(activity_type__startswith="PDM:").count(),
            prev_qs.filter(activity_type__startswith="PDM:").count(),
            "purple",
        )
    )

    by_sector = _group(month_qs, "department__name")
    donut_total, donut_gradient = _donut(by_sector)

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

    ben = PDMBeneficiary.objects.filter(sub_county=sc).aggregate(
        n=Count("id"),
        women=Count("id", filter=Q(sex="F")),
        youth=Count("id", filter=Q(youth=True)),
        amount=Sum("amount_received"),
    )
    pdm_rows = [
        ["Beneficiaries registered", ben["n"]],
        ["Women", ben["women"]],
        ["Youth", ben["youth"]],
        ["Amount received (UGX)", "{:,}".format(ben["amount"] or 0)],
        ["PDM groups", PDMGroup.objects.filter(sub_county=sc).count()],
    ]

    photos = (
        ActivityPhoto.objects.filter(activity__in=month_qs.values("pk"))
        .select_related("activity")
        .order_by("-id")[:6]
    )

    context = {
        "sc": sc,
        "period": "%s %s" % (calendar.month_name[month], year),
        "prev_query": "year=%s&month=%s" % (prev_y, prev_m),
        "next_query": "year=%s&month=%s" % (next_y, next_m),
        "key_tiles": key_tiles,
        "people_tiles": people_tiles,
        "sector_tiles": sector_tiles,
        "by_sector": by_sector,
        "donut_total": donut_total,
        "donut_gradient": donut_gradient,
        "bars": bars,
        "parish_rows": parish_rows,
        "trend": series,
        "line": " ".join(points),
        "officers": officers,
        "pdm_rows": pdm_rows,
        "recent": month_qs.select_related("department", "parish", "officer")[:8],
        "photos": photos,
    }
    return render(request, "core/subcounty.html", context)