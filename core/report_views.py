from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .exports import build_tables, make_docx, make_pdf
from .models import Department, SubCounty
from .report_photos import collect_photos
from .report_registers import register_tables; from .report_registers_more import more_register_tables
from .reports import (
    KINDS,
    QUARTERS,
    build_report,
    fiscal_year_of,
    quarter_of,
    resolve_period,
)
from .views import visible_activities

DISTRICT_ROLES = ("admin", "dpo", "head", "viewer")


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse(request):
    today = timezone.localdate()
    get = request.GET
    kind = get.get("type")
    if kind not in dict(KINDS):
        kind = "monthly"
    try:
        day = date.fromisoformat(get.get("day", ""))
    except ValueError:
        day = today
    month = _int(get.get("month"), today.month)
    if not 1 <= month <= 12:
        month = today.month
    year = _int(get.get("year"), today.year)
    if not 2000 <= year <= 2100:
        year = today.year
    fy = _int(get.get("fy"), fiscal_year_of(today))
    if not 2000 <= fy <= 2100:
        fy = fiscal_year_of(today)
    quarter = _int(get.get("quarter"), quarter_of(today))
    if quarter not in (1, 2, 3, 4):
        quarter = quarter_of(today)

    period = resolve_period(kind, today, day, year, month, fy, quarter)
    department = Department.objects.filter(
        pk=_int(get.get("department"), 0)
    ).first()
    sub_county = SubCounty.objects.filter(
        pk=_int(get.get("sub_county"), 0)
    ).first()
    form = {
        "kind": kind,
        "day": day.isoformat(),
        "month": month,
        "year": year,
        "fy": fy,
        "quarter": quarter,
    }
    return form, period, department, sub_county


def _prepare(request):
    form, period, department, sub_county = _parse(request)
    user = request.user
    base = visible_activities(user)
    include_targets = sub_county is None and (
        user.is_superuser or user.role in DISTRICT_ROLES
    )
    data = build_report(base, period, department, sub_county, include_targets)
    data["photos"] = collect_photos(base, period, department, sub_county)
    if user.is_superuser or user.role in DISTRICT_ROLES:
        data["register_tables"] = register_tables(period, department, sub_county) + more_register_tables(period, department, sub_county)
    else:
        data["register_tables"] = []
    return form, department, sub_county, data


def _tables(data):
    tables = build_tables(data)
    extra = []
    targets = data.get("targets")
    if targets and targets["rows"]:
        extra.append(targets)
    breakdown = data.get("breakdown")
    if breakdown and breakdown["rows"]:
        extra.append(
            {
                "title": breakdown["title"],
                "header": [breakdown["label"], "Activities", "People reached"],
                "rows": [
                    [r["name"], r["activities"], r["reached"]]
                    for r in breakdown["rows"]
                ],
            }
        )
    tables[1:1] = extra + data.get("register_tables", [])
    return tables


@login_required
def report(request):
    form, department, sub_county, data = _prepare(request)
    user = request.user
    context = {
        "f": form,
        "kinds": KINDS,
        "quarters": QUARTERS,
        "months": list(
            enumerate(
                [
                    "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December",
                ],
                start=1,
            )
        ),
        "departments": Department.objects.order_by("name"),
        "sub_counties": SubCounty.objects.order_by("name"),
        "department_id": department.pk if department else 0,
        "sub_county_id": sub_county.pk if sub_county else 0,
        "data": data,
        "tables": _tables(data),
        "query": request.GET.urlencode(),
        "can_pack": user.is_superuser or user.role in DISTRICT_ROLES,
    }
    return render(request, "core/report.html", context)


@login_required
def report_docx(request):
    data = _prepare(request)[3]
    content = make_docx(data, _tables(data))
    response = HttpResponse(
        content,
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = 'attachment; filename="%s.docx"' % data["filename"]
    return response


@login_required
def report_pdf(request):
    data = _prepare(request)[3]
    content = make_pdf(data, _tables(data))
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="%s.pdf"' % data["filename"]
    return response