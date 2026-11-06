import csv
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import SubCounty
from .permit_forms import PermitForm
from .permit_models import (
    ANIMAL_OTHER,
    ANIMAL_SLAUGHTER,
    ANIMAL_SUB,
    ANIMAL_TYPES,
    FISH,
    TYPES,
    MovementPermit,
)
from .permit_pdf import make_permit_pdf

KINDS = {"subcounty": ANIMAL_SUB, "slaughter": ANIMAL_SLAUGHTER, "other": ANIMAL_OTHER, "fish": FISH}
KIND_SLUG = {v: k for k, v in KINDS.items()}
TYPE_LABEL = dict(TYPES)


# ------------------------------------------------------------------ access
def is_manager(user):
    return user.is_superuser or getattr(user, "role", "") in ("admin", "dpo")


def can_issue(user, permit_type):
    """Who may issue which permit. Administrators and the DPO may issue any.
    Otherwise the officer must belong to the Veterinary (animals) or Fisheries (fish) department."""
    if not user.is_authenticated:
        return False
    if is_manager(user):
        return True
    if getattr(user, "role", "") == "viewer":
        return False
    dept = getattr(getattr(user, "department", None), "name", "")
    return dept == ("Fisheries" if permit_type == FISH else "Veterinary")


def can_change(user, permit):
    if not can_issue(user, permit.permit_type):
        return False
    return is_manager(user) or permit.registered_by_id == user.pk


# -------------------------------------------------------------------- list
def _filtered(request):
    today = timezone.localdate()
    qs = MovementPermit.objects.select_related("origin_sub_county", "registered_by", "origin_landing_site")
    kind = request.GET.get("type", "")
    if kind == "animal":
        qs = qs.filter(permit_type__in=ANIMAL_TYPES)
    elif kind in TYPE_LABEL:
        qs = qs.filter(permit_type=kind)
    base = qs
    state = request.GET.get("state", "")
    if state == "valid":
        qs = qs.filter(status="issued", valid_until__gte=today)
    elif state == "expired":
        qs = qs.filter(status="issued", valid_until__lt=today)
    elif state in ("used", "cancelled"):
        qs = qs.filter(status=state)
    month = request.GET.get("month", "")
    if month:
        try:
            y, m = month.split("-")
            qs = qs.filter(issue_date__year=int(y), issue_date__month=int(m))
        except ValueError:
            month = ""
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(holder_name__icontains=q) | Q(code__icontains=q) | Q(book_number__icontains=q)
            | Q(from_place__icontains=q) | Q(to_place__icontains=q) | Q(vehicle_reg__icontains=q)
            | Q(fish_species__icontains=q)
        )
    return base, qs, {"type": kind, "state": state, "month": month, "q": q}


@login_required
def permit_list(request):
    base, qs, filters = _filtered(request)
    today = timezone.localdate()

    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="movement_permits.csv"'
        resp.write("﻿")
        w = csv.writer(resp)
        w.writerow(["Reference", "Book number", "Type", "Name", "Phone", "What", "Quantity", "From",
                    "To", "Via", "Purpose", "Date of issue", "Valid until", "Status", "Fee (UGX)",
                    "Receipt", "Issued by"])
        for p in qs:
            w.writerow([p.code, p.book_number, p.get_permit_type_display(), p.holder_name, p.holder_phone,
                        p.what, p.quantity_text, p.from_place, p.destination, p.via, p.purpose,
                        p.issue_date, p.valid_until, p.state, p.fee, p.receipt_number, p.issued_by])
        return resp

    month_start = today.replace(day=1)
    tiles = [
        ("Issued this month", base.filter(issue_date__gte=month_start).exclude(status="cancelled").count(), "green"),
        ("Valid now", base.filter(status="issued", valid_until__gte=today).count(), "blue"),
        ("Past date, not marked completed", base.filter(status="issued", valid_until__lt=today).count(), "orange"),
        ("Cancelled this month", base.filter(status="cancelled", issue_date__gte=month_start).count(), "red"),
    ]
    by_type = [(TYPE_LABEL.get(r["permit_type"], r["permit_type"]), r["n"])
               for r in qs.values("permit_type").annotate(n=Count("id")).order_by("-n")]
    by_dest = [(r["to_place"], r["n"]) for r in qs.values("to_place").annotate(n=Count("id")).order_by("-n")[:8]]
    by_sub = [(r["origin_sub_county__name"], r["n"]) for r in
              qs.exclude(origin_sub_county=None).values("origin_sub_county__name")
              .annotate(n=Count("id")).order_by("-n")[:8]]

    page = Paginator(qs, 40).get_page(request.GET.get("page"))
    keep = request.GET.copy()
    keep.pop("page", None)
    keep.pop("export", None)
    issue_links = []
    for slug, ptype in KINDS.items():
        if can_issue(request.user, ptype):
            issue_links.append((TYPE_LABEL[ptype], reverse("permit_new", args=[slug])))
    return render(request, "core/permit_list.html", {
        "page": page, "tiles": tiles, "filters": filters, "keep": keep.urlencode(),
        "by_type": by_type, "by_dest": by_dest, "by_sub": by_sub,
        "issue_links": issue_links, "type_labels": TYPES,
        "heading": {"animal": "Animal movement permits", "fish": "Fish movement permits"}.get(
            filters["type"], "Movement permits"),
    })


# ------------------------------------------------------------- issue / edit
@login_required
def permit_new(request, kind):
    ptype = KINDS.get(kind)
    if ptype is None:
        raise Http404
    if not can_issue(request.user, ptype):
        raise PermissionDenied
    initial = {"issue_date": timezone.localdate()}
    sub = getattr(request.user, "sub_county", None)
    if sub is not None and ptype != FISH:
        origin_sub_county = SubCounty.objects.filter(name__iexact=sub.strip()).first()
        if origin_sub_county is not None:
            initial["origin_sub_county"] = origin_sub_county.pk
    if ptype == FISH:
        initial["origin_district"] = "Soroti"
    form = PermitForm(request.POST or None, kind=ptype, initial=initial)
    if request.method == "POST" and form.is_valid():
        permit = form.save(commit=False)
        permit.permit_type = ptype
        permit.registered_by = request.user
        permit.save()
        messages.success(request, "Permit %s recorded. You can print it below." % permit.code)
        return redirect("permit_detail", pk=permit.pk)
    return render(request, "core/permit_form.html", {
        "form": form, "title": "Issue: " + TYPE_LABEL[ptype], "kind": ptype,
        "back": reverse("permit_list"), "landing_lakes": _lakes(),
    })


@login_required
def permit_edit(request, pk):
    permit = get_object_or_404(MovementPermit, pk=pk)
    if not can_change(request.user, permit) or permit.status != "issued":
        raise PermissionDenied
    form = PermitForm(request.POST or None, instance=permit, kind=permit.permit_type)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Permit %s updated." % permit.code)
        return redirect("permit_detail", pk=permit.pk)
    return render(request, "core/permit_form.html", {
        "form": form, "title": "Edit permit %s" % permit.code, "kind": permit.permit_type,
        "back": reverse("permit_detail", args=[permit.pk]), "landing_lakes": _lakes(),
    })


def _lakes():
    """Landing site id -> water body, so the form can fill in the lake."""
    try:
        from .reg_models import LandingSite
        return {str(s.pk): s.water_body for s in LandingSite.objects.exclude(water_body="")}
    except Exception:
        return {}


# ------------------------------------------------------------------ detail
def _rows(p):
    rows = [("Reference", p.code), ("Serial number in the permit book", p.book_number),
            ("Type", p.get_permit_type_display()), ("Name", p.holder_name), ("Address", p.address),
            ("County of", p.county), ("Phone", p.holder_phone), ("Farmer ID", p.farmer_code)]
    if p.permit_type == FISH:
        rows += [("Fish species", p.fish_species), ("Quantity (kg)", p.quantity_text),
                 ("Form", p.get_fish_form_display()), ("Lake", p.origin_lake),
                 ("Landing site", p.origin_landing_site.name if p.origin_landing_site_id else ""),
                 ("Fish market", p.origin_market), ("District of origin", p.origin_district),
                 ("Destination", p.to_place), ("Destination district", p.dest_district),
                 ("Mode of transport", p.transport_mode), ("Vehicle registration", p.vehicle_reg)]
    else:
        rows += [("Moving", p.movement_text), ("Brand", p.brand),
                 ("Sub-county of origin", p.origin_sub_county or ""), ("From", p.from_place),
                 ("To", p.to_place), ("Via", p.via), ("Purpose", p.purpose),
                 ("To be slaughtered within (days)", p.slaughter_within_days or ""),
                 ("Vehicle registration", p.vehicle_reg)]
    rows += [("Date of issue", p.issue_date), ("Valid for (days)", p.valid_days), ("Valid until", p.valid_until),
             ("Fees paid (UGX)", "{:,}".format(p.fee) if p.fee else ""), ("Receipt number", p.receipt_number),
             ("Inspection notes", p.inspection_notes), ("Issued by", p.issued_by), ("Title", p.officer_post),
             ("Outbreak area checked with the DVO", "Yes" if p.outbreak_confirmed else ""),
             ("Status note", p.status_note)]
    return [(a, b) for a, b in rows if b not in ("", None)]


@login_required
def permit_detail(request, pk):
    p = get_object_or_404(MovementPermit.objects.select_related("registered_by", "origin_sub_county"), pk=pk)
    return render(request, "core/permit_detail.html", {
        "p": p, "rows": _rows(p),
        "can_act": can_change(request.user, p) and p.status == "issued",
        "can_status": can_issue(request.user, p.permit_type) and p.status == "issued",
    })


@login_required
@require_POST
def permit_action(request, pk):
    p = get_object_or_404(MovementPermit, pk=pk)
    if not can_issue(request.user, p.permit_type):
        raise PermissionDenied
    action = request.POST.get("action")
    note = request.POST.get("note", "").strip()[:250]
    if p.status != "issued":
        messages.error(request, "This permit is already %s." % p.state.lower())
    elif action == "used":
        p.status, p.status_note, p.status_changed_at = "used", note, timezone.now()
        p.save()
        messages.success(request, "Marked as completed.")
    elif action == "cancel":
        if not note:
            messages.error(request, "Write the reason for cancelling.")
        else:
            p.status, p.status_note, p.status_changed_at = "cancelled", note, timezone.now()
            p.save()
            messages.success(request, "Permit cancelled.")
    return redirect("permit_detail", pk=p.pk)


# --------------------------------------------------------------------- pdf
@login_required
def permit_pdf(request, pk):
    p = get_object_or_404(MovementPermit.objects.select_related("registered_by", "origin_landing_site"), pk=pk)
    url = request.build_absolute_uri(reverse("permit_verify", args=[p.code]))
    resp = HttpResponse(make_permit_pdf(p, url), content_type="application/pdf")
    resp["Content-Disposition"] = 'inline; filename="permit_%s.pdf"' % p.code
    return resp


# ------------------------------------------------------------------ verify
def permit_verify(request, code):
    """Public page for a checkpoint officer who scans the QR code. Shows only what is needed to
    check the permit; no phone numbers or addresses."""
    p = MovementPermit.objects.filter(code__iexact=code).first()
    return render(request, "core/permit_verify.html", {"p": p, "code": code, "today": date.today()})
