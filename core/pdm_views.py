from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .exports import make_docx, make_pdf
from .models import SubCounty
from .pdm_forms import BeneficiaryForm, GroupForm, VisitForm
from .pdm_models import PDMBeneficiary, PDMGroup, PDMVisit

DISTRICT_ROLES = ("admin", "dpo", "head", "viewer")


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _district(user):
    return user.is_superuser or user.role in DISTRICT_ROLES


def can_add(user):
    return user.is_superuser or user.role != "viewer"


def can_edit(user, obj):
    return (
        user.is_superuser
        or user.role in ("admin", "dpo")
        or obj.registered_by_id == user.id
    )


def visible_beneficiaries(user):
    qs = PDMBeneficiary.objects.select_related("sub_county", "parish", "group")
    if _district(user):
        return qs
    return qs.filter(registered_by=user)


def money(value):
    return "{:,}".format(value or 0)


@login_required
def pdm_list(request):
    user = request.user
    qs = visible_beneficiaries(user)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q))
    sub = _int(request.GET.get("sub_county"), 0)
    if sub:
        qs = qs.filter(sub_county_id=sub)
    loan = request.GET.get("loan", "")
    if loan in dict(PDMBeneficiary.LOAN):
        qs = qs.filter(loan_status=loan)
    else:
        loan = ""
    group_id = _int(request.GET.get("group"), 0)
    group = None
    if group_id:
        group = PDMGroup.objects.filter(pk=group_id).first()
        qs = qs.filter(group_id=group_id)
    totals = qs.aggregate(n=Count("id"), amount=Sum("amount_received"))
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "core/pdm_list.html",
        {
            "page": page,
            "q": q,
            "sub_county_id": sub,
            "loan": loan,
            "group": group,
            "sub_counties": SubCounty.objects.order_by("name"),
            "loans": PDMBeneficiary.LOAN,
            "total_count": totals["n"],
            "total_amount": totals["amount"] or 0,
            "params": params.urlencode(),
            "can_add": can_add(user),
        },
    )


@login_required
def pdm_new(request):
    if not can_add(request.user):
        return redirect("pdm_list")
    form = BeneficiaryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.registered_by = request.user
        obj.save()
        return redirect("pdm_detail", pk=obj.pk)
    return render(
        request,
        "core/pdm_form.html",
        {"form": form, "title": "Register PDM beneficiary", "cancel": reverse("pdm_list")},
    )


@login_required
def pdm_edit(request, pk):
    obj = get_object_or_404(visible_beneficiaries(request.user), pk=pk)
    if not can_edit(request.user, obj):
        return redirect("pdm_detail", pk=pk)
    form = BeneficiaryForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("pdm_detail", pk=pk)
    return render(
        request,
        "core/pdm_form.html",
        {
            "form": form,
            "title": "Edit beneficiary",
            "cancel": reverse("pdm_detail", args=[pk]),
        },
    )


@login_required
def pdm_detail(request, pk):
    user = request.user
    obj = get_object_or_404(visible_beneficiaries(user), pk=pk)
    visits = obj.visits.select_related("officer")
    totals = visits.aggregate(revenue=Sum("revenue"), spend=Sum("expenditure"))
    return render(
        request,
        "core/pdm_detail.html",
        {
            "b": obj,
            "visits": visits[:20],
            "visit_count": visits.count(),
            "revenue": totals["revenue"] or 0,
            "spend": totals["spend"] or 0,
            "can_edit": can_edit(user, obj),
            "can_add": can_add(user),
        },
    )


@login_required
def pdm_visit_new(request, pk):
    user = request.user
    obj = get_object_or_404(visible_beneficiaries(user), pk=pk)
    if not can_add(user):
        return redirect("pdm_detail", pk=pk)
    form = VisitForm(request.POST or None, initial={"date": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        visit = form.save(commit=False)
        visit.beneficiary = obj
        visit.officer = user
        visit.save()
        return redirect("pdm_detail", pk=pk)
    return render(
        request,
        "core/pdm_form.html",
        {
            "form": form,
            "title": "Monitoring visit: %s" % obj.name,
            "cancel": reverse("pdm_detail", args=[pk]),
        },
    )


@login_required
def pdm_groups(request):
    groups = (
        PDMGroup.objects.select_related("sub_county", "parish")
        .annotate(members_n=Count("members"))
        .order_by("sub_county__name", "parish__name", "name")
    )
    return render(
        request,
        "core/pdm_groups.html",
        {"groups": groups, "can_add": can_add(request.user)},
    )


@login_required
def pdm_group_new(request):
    if not can_add(request.user):
        return redirect("pdm_groups")
    form = GroupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.registered_by = request.user
        obj.save()
        return redirect("pdm_groups")
    return render(
        request,
        "core/pdm_form.html",
        {"form": form, "title": "Register PDM group", "cancel": reverse("pdm_groups")},
    )


def _rows(qs, fields):
    rows = (
        qs.order_by()
        .values(*fields)
        .annotate(
            n=Count("id"),
            women=Count("id", filter=Q(sex="F")),
            youth=Count("id", filter=Q(youth=True)),
            pwd=Count("id", filter=Q(pwd=True)),
            amount=Sum("amount_received"),
        )
        .order_by(*fields)
    )
    out = []
    for r in rows:
        if len(fields) == 1:
            name = r[fields[0]]
        else:
            name = "%s (%s)" % (r[fields[0]], r[fields[1]])
        out.append([name, r["n"], r["women"], r["youth"], r["pwd"], money(r["amount"])])
    return out


def _summary_tables(qs):
    agg = qs.aggregate(
        n=Count("id"),
        women=Count("id", filter=Q(sex="F")),
        youth=Count("id", filter=Q(youth=True)),
        pwd=Count("id", filter=Q(pwd=True)),
        amount=Sum("amount_received"),
    )
    visits = PDMVisit.objects.filter(beneficiary__in=qs.values("pk")).aggregate(
        n=Count("id"), revenue=Sum("revenue"), spend=Sum("expenditure")
    )
    groups = qs.exclude(group=None).order_by().values("group").distinct().count()
    header = ["Name", "Beneficiaries", "Women", "Youth", "PWD", "Amount received (UGX)"]
    return [
        {
            "title": "Summary",
            "header": ["Indicator", "Total"],
            "rows": [
                ["Beneficiaries registered", agg["n"]],
                ["Women", agg["women"]],
                ["Men", agg["n"] - agg["women"]],
                ["Youth", agg["youth"]],
                ["Persons with disability", agg["pwd"]],
                ["Groups represented", groups],
                ["Total amount received (UGX)", money(agg["amount"])],
                ["Monitoring visits recorded", visits["n"]],
                ["Revenue reported at visits (UGX)", money(visits["revenue"])],
                ["Expenditure reported at visits (UGX)", money(visits["spend"])],
            ],
        },
        {
            "title": "Loan status",
            "header": ["Status", "Beneficiaries"],
            "rows": [
                [label, qs.filter(loan_status=code).count()]
                for code, label in PDMBeneficiary.LOAN
            ],
        },
        {
            "title": "By sub-county",
            "header": ["Sub-county"] + header[1:],
            "rows": _rows(qs, ["sub_county__name"]),
        },
        {
            "title": "By parish",
            "header": ["Parish (sub-county)"] + header[1:],
            "rows": _rows(qs, ["parish__name", "parish__sub_county__name"]),
        },
    ]


def _summary_data():
    today = timezone.localdate()
    return {
        "title": "PDM BENEFICIARY SUMMARY REPORT",
        "period": "As at " + today.strftime("%d %B %Y"),
        "filters": "",
        "filename": "PDM-summary-" + today.isoformat(),
    }


@login_required
def pdm_summary(request):
    qs = visible_beneficiaries(request.user)
    return render(
        request,
        "core/pdm_summary.html",
        {"data": _summary_data(), "tables": _summary_tables(qs)},
    )


@login_required
def pdm_summary_docx(request):
    qs = visible_beneficiaries(request.user)
    data = _summary_data()
    response = HttpResponse(
        make_docx(data, _summary_tables(qs)),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    response["Content-Disposition"] = 'attachment; filename="%s.docx"' % data["filename"]
    return response


@login_required
def pdm_summary_pdf(request):
    qs = visible_beneficiaries(request.user)
    data = _summary_data()
    response = HttpResponse(
        make_pdf(data, _summary_tables(qs)), content_type="application/pdf"
    )
    response["Content-Disposition"] = 'attachment; filename="%s.pdf"' % data["filename"]
    return response