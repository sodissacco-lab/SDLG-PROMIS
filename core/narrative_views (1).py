from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .letterhead import sector_line
from .narrative import FIELDS, KEYS, build_sections
from .narrative_exports import make_narrative_docx, make_narrative_pdf
from .narrative_registers import keep_nonzero, register_text
from .report_photos import collect_photos
from .report_registers import register_tables
from .report_registers_more import more_register_tables
from .report_views import DISTRICT_ROLES, _parse, _tables
from .reports import build_report
from .views import visible_activities

EXTRA = ("register_text", "Registers and measured results", 7)
ALL_KEYS = KEYS + ["register_text"]


def _keyed(tables):
    keys = {"registers": [], "measured": []}
    for t in tables:
        title = t["title"]
        if title.startswith("Performance"):
            keys["targets"] = t
        elif title in ("By month", "By day"):
            keys["breakdown"] = t
        elif title == "Summary":
            keys["summary"] = t
        elif title == "By department":
            keys["by_department"] = t
        elif title == "By sub-county":
            keys["by_sub_county"] = t
        elif title == "By activity type":
            keys["by_type"] = t
        elif title == "Activities implemented":
            keys["activities"] = t
        elif title.startswith("Register statistics"):
            keys["registers"].append(dict(t, rows=keep_nonzero(t["rows"])))
        elif title.startswith("Measured results"):
            keys["measured"].append(t)
    return keys


def _load(request):
    form, period, department, sub_county = _parse(request)
    user = request.user
    base = visible_activities(user)
    district = user.is_superuser or user.role in DISTRICT_ROLES
    data = build_report(base, period, department, sub_county, sub_county is None and district)
    data["sector_line"] = sector_line(department, sub_county)
    data["photos"] = collect_photos(base, period, department, sub_county)
    if district:
        data["register_tables"] = register_tables(period, department, sub_county) + more_register_tables(
            period, department, sub_county
        )
    else:
        data["register_tables"] = []
    qs = base.filter(date__gte=period["start"], date__lte=period["end"])
    if department:
        qs = qs.filter(department=department)
    if sub_county:
        qs = qs.filter(sub_county=sub_county)
    return period, department, sub_county, data, qs, _keyed(_tables(data))


@login_required
def narrative(request):
    period, department, sub_county, data, qs, tables = _load(request)
    sections = build_sections(data, period, department, sub_county, qs)
    sections["register_text"] = register_text(data)
    fields = []
    for key, label, rows in FIELDS:
        fields.append({"key": key, "label": label, "rows": rows, "text": sections.get(key, "")})
        if key == "coverage_text":
            fields.append(
                {
                    "key": EXTRA[0],
                    "label": EXTRA[1],
                    "rows": EXTRA[2],
                    "text": sections.get(EXTRA[0], ""),
                }
            )
    return render(
        request,
        "core/narrative.html",
        {
            "data": data,
            "fields": fields,
            "query": request.GET.urlencode(),
            "photo_count": len(data["photos"]),
        },
    )


def _posted(request):
    return {k: request.POST.get(k, "") for k in ALL_KEYS}


@login_required
@require_POST
def narrative_docx(request):
    period, department, sub_county, data, qs, tables = _load(request)
    content = make_narrative_docx(data, tables, _posted(request))
    response = HttpResponse(
        content,
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = (
        'attachment; filename="Narrative-%s.docx"' % data["filename"]
    )
    return response


@login_required
@require_POST
def narrative_pdf(request):
    period, department, sub_county, data, qs, tables = _load(request)
    content = make_narrative_pdf(data, tables, _posted(request))
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="Narrative-%s.pdf"' % data["filename"]
    )
    return response