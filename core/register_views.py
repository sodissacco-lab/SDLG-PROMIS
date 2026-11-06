from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse

from .models import Department
from .registers import CATALOG, KIND_LABELS, register_href, siblings


@login_required
def register_page(request, slug):
    entry = CATALOG.get(slug)
    if entry is None:
        raise Http404
    raw = request.GET.get("s", "")
    sector = Department.objects.filter(pk=int(raw)).first() if raw.isdigit() else None

    new_activity = reverse("activity_new")
    if sector:
        new_activity += "?department=%s" % sector.pk
    related = [
        {"label": CATALOG[s]["label"], "href": register_href(s, sector.pk if sector else None)}
        for s in siblings(slug)
    ]
    return render(
        request,
        "core/register_page.html",
        {
            "entry": entry,
            "kind_label": KIND_LABELS.get(entry["kind"], ""),
            "sector": sector,
            "new_activity": new_activity,
            "related": related,
        },
    )