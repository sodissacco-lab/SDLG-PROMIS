from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect

from .models import SubCounty
from .pack import make_pack_docx, make_pack_pdf
from .report_registers import register_tables
from .report_registers_more import more_register_tables
from .report_views import DISTRICT_ROLES, _parse
from .reports import build_report
from .views import visible_activities


def _data(base, period, department, sub_county):
    data = build_report(base, period, department, sub_county, False)
    data["register_tables"] = register_tables(
        period, department, sub_county
    ) + more_register_tables(period, department, sub_county)
    return data


def _build(request):
    _, period, department, _ = _parse(request)
    base = visible_activities(request.user)
    sections = [("District summary", _data(base, period, department, None))]
    empty = []
    for sub_county in SubCounty.objects.order_by("name"):
        data = _data(base, period, department, sub_county)
        if data["summary"]["activities"]:
            sections.append(("Sub-county: " + sub_county.name, data))
        else:
            empty.append(sub_county.name)
    label = period["label"]
    if department:
        label += " | Department: " + department.name
    title = "SUB-COUNTY REPORT PACK: " + period["title"]
    return period, title, label, sections, empty


def _allowed(user):
    return user.is_superuser or user.role in DISTRICT_ROLES


@login_required
def pack_pdf(request):
    if not _allowed(request.user):
        return redirect("report")
    period, title, label, sections, empty = _build(request)
    response = HttpResponse(
        make_pack_pdf(title, label, sections, empty), content_type="application/pdf"
    )
    response["Content-Disposition"] = (
        'attachment; filename="Subcounty-pack-%s.pdf"' % period["filename"]
    )
    return response


@login_required
def pack_docx(request):
    if not _allowed(request.user):
        return redirect("report")
    period, title, label, sections, empty = _build(request)
    response = HttpResponse(
        make_pack_docx(title, label, sections, empty),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = (
        'attachment; filename="Subcounty-pack-%s.docx"' % period["filename"]
    )
    return response