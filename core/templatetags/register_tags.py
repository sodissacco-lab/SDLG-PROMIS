from datetime import timedelta

from django import template
from django.db.models import Max, Sum
from django.urls import reverse
from django.utils import timezone

from core.models import Activity
from core.pdm_models import PDMBeneficiary
from core.reg_models import (
    Boat,
    BoatOwner,
    CageFarm,
    DailyCatch,
    Farmer,
    Fisher,
    FishingLicence,
    FishPond,
    HarvestRecord,
    Household,
    IllegalFishingIncident,
    LandingSite,
    LandingSiteRevenue,
    StockingRecord,
)

register = template.Library()


def _row(label, url_name, qs, active=None):
    today = timezone.localdate()
    return {
        "label": label,
        "url": reverse(url_name),
        "total": qs.count(),
        "new": qs.filter(
            created_at__year=today.year, created_at__month=today.month
        ).count(),
        "active": qs.filter(**active).count() if active else None,
    }


def _month(qs, field="date"):
    today = timezone.localdate()
    return qs.filter(**{field + "__year": today.year, field + "__month": today.month})


def _sum(qs, field):
    return qs.aggregate(t=Sum(field))["t"] or 0


def _stale_sites(today):
    cutoff = today - timedelta(days=30)
    last = dict(
        Activity.objects.filter(
            status="approved",
            activity_type="Landing site inspection",
            landing_site__isnull=False,
        )
        .order_by()
        .values_list("landing_site")
        .annotate(last=Max("date"))
    )
    stale = []
    for site in LandingSite.objects.filter(status="active").order_by("name"):
        d = last.get(site.pk)
        if d is None or d < cutoff:
            stale.append(
                {
                    "name": site.name,
                    "url": reverse("reg_detail", args=["landing-sites", site.pk]),
                    "last": d,
                }
            )
    return stale


def _panel(name):
    today = timezone.localdate()
    active = {"status": "active"}
    farmers = Farmer.objects.exclude(status="merged")
    rows, measures, stale = [], [], []

    if name is None:
        rows += [
            _row("Farmers (all sectors)", "r_farmer_registry", farmers, active),
            _row("Households", "r_households", Household.objects.all()),
        ]
    elif name == "Crops":
        rows.append(_row("Farmers who grow crops", "r_farmer_registry", farmers.filter(grows_crops=True), active))
    elif name == "Veterinary":
        rows.append(_row("Farmers who keep livestock", "r_farmer_registry", farmers.filter(keeps_livestock=True), active))

    if name in (None, "Fisheries"):
        rows += [
            _row("Landing sites", "r_landing_sites", LandingSite.objects.all(), active),
            _row("Boats", "r_boats", Boat.objects.all(), active),
            _row("Boat owners", "r_boat_owners", BoatOwner.objects.all()),
            _row("Fishers", "r_fishers", Fisher.objects.all(), active),
            _row("Fish farmers", "r_fish_farmers", farmers.filter(fish_farming=True), active),
            _row("Fish ponds", "r_fish_ponds", FishPond.objects.all(), active),
            _row("Cage farms", "r_cage_farms", CageFarm.objects.all(), active),
        ]
        licences = FishingLicence.objects.all()
        soon = today + timedelta(days=30)
        measures = [
            {"label": "Catch recorded this month (kg)", "value": _sum(_month(DailyCatch.objects.all()), "quantity_kg"), "color": "blue"},
            {"label": "Revenue collected this month (UGX)", "value": "{:,}".format(_sum(_month(LandingSiteRevenue.objects.all()), "amount")), "color": "green"},
            {"label": "Fish harvested this month (kg)", "value": _sum(_month(HarvestRecord.objects.all()), "quantity_kg"), "color": "teal"},
            {"label": "Fingerlings stocked this month", "value": _sum(_month(StockingRecord.objects.all()), "fingerlings"), "color": "purple"},
            {"label": "Illegal fishing incidents this month", "value": _month(IllegalFishingIncident.objects.all()).count(), "color": "red"},
            {"label": "Licences valid now", "value": licences.filter(expiry_date__gte=today).count(), "color": "green"},
            {"label": "Licences expiring in 30 days", "value": licences.filter(expiry_date__gte=today, expiry_date__lte=soon).count(), "color": "orange"},
            {"label": "Licences expired", "value": licences.filter(expiry_date__lt=today).count(), "color": "pink"},
        ]
        stale = _stale_sites(today)

    if name is None:
        rows.append(_row("PDM beneficiaries", "pdm_list", PDMBeneficiary.objects.all()))

    return {
        "rows": rows,
        "measures": measures,
        "stale": stale,
        "title": "Registers across the district" if name is None else "Registers",
    }


@register.inclusion_tag("core/_register_panel.html")
def register_panel(department):
    return _panel(department.name)


@register.inclusion_tag("core/_register_panel.html")
def district_registers():
    return _panel(None)