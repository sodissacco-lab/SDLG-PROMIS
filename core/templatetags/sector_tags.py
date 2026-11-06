from datetime import timedelta

from django import template
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from core.crop_vet_models import (
    LIVESTOCK,
    AgriInput,
    CropGrown,
    CropHarvest,
    DemonstrationFarm,
    DiseaseReport,
    FarmerGroup,
    LivestockCount,
    MarketPrice,
    Outbreak,
    PestDiseaseReport,
    TreatmentRecord,
    VaccinationCampaign,
)
from core.ent_com_models import (
    MSME,
    Enterprise,
    EnterprisePerformance,
    LoanIntervention,
    Market,
    MarketLinkage,
    Trap,
    TrapInspection,
    ValueAdditionVenture,
    VectorCount,
    VectorIncident,
)

register = template.Library()


def _row(label, url_name, qs, active=None):
    today = timezone.localdate()
    return {
        "label": label,
        "url": reverse(url_name),
        "total": qs.count(),
        "new": qs.filter(created_at__year=today.year, created_at__month=today.month).count(),
        "active": qs.filter(**active).count() if active else None,
    }


def _month(qs, field="date"):
    today = timezone.localdate()
    return qs.filter(**{field + "__year": today.year, field + "__month": today.month})


def _sum(qs, field):
    return qs.aggregate(t=Sum(field))["t"] or 0


def _money(n):
    return "{:,}".format(n or 0)


@register.inclusion_tag("core/_sector_extras.html")
def sector_extras(department):
    today = timezone.localdate()
    rows, measures, species, alerts = [], [], [], []
    name = department.name
    active = {"status": "active"}

    if name == "Crops":
        rows = [
            _row("Farmer groups & cooperatives", "r_farmer_groups", FarmerGroup.objects.all(), active),
            _row("Demonstration farms", "r_demonstration_farms", DemonstrationFarm.objects.all(), active),
            _row("Crop records (growing)", "r_crops_grown", CropGrown.objects.all(), active),
        ]
        pests = _month(PestDiseaseReport.objects.all())
        high = pests.filter(severity="high")
        measures = [
            {"label": "Acreage under crops now", "value": _sum(CropGrown.objects.filter(status="active"), "acreage"), "color": "green"},
            {"label": "Harvest recorded this month (kg)", "value": _sum(_month(CropHarvest.objects.all()), "quantity_kg"), "color": "orange"},
            {"label": "Pest and disease reports this month", "value": pests.count(), "color": "pink"},
            {"label": "High-severity reports this month", "value": high.count(), "color": "red"},
            {"label": "Input distributions this month", "value": _month(AgriInput.objects.all()).count(), "color": "blue"},
            {"label": "Crop prices recorded this month", "value": _month(MarketPrice.objects.filter(category="crop")).count(), "color": "teal"},
        ]
        for r in high.select_related("sub_county").order_by("-date")[:5]:
            alerts.append({
                "text": "%s on %s in %s" % (r.pest_or_disease, r.crop, r.sub_county),
                "date": r.date,
                "url": reverse("reg_detail", args=["pest-disease-surveillance", r.pk]),
            })

    elif name == "Veterinary":
        reports = _month(DiseaseReport.objects.all())
        campaigns = _month(VaccinationCampaign.objects.all())
        eligible = _sum(campaigns, "animals_eligible")
        vaccinated = _sum(campaigns, "animals_vaccinated")
        coverage = "%d%%" % round(100.0 * vaccinated / eligible) if eligible else "-"
        outbreaks = Outbreak.objects.filter(status="active")
        measures = [
            {"label": "Suspected disease reports this month", "value": reports.filter(status="suspected").count(), "color": "orange"},
            {"label": "Confirmed disease reports this month", "value": reports.filter(status="confirmed").count(), "color": "red"},
            {"label": "Active outbreaks", "value": outbreaks.count(), "color": "pink"},
            {"label": "Animals vaccinated this month", "value": vaccinated, "color": "green"},
            {"label": "Vaccination coverage this month", "value": coverage, "color": "teal"},
            {"label": "Animals treated this month", "value": _sum(_month(TreatmentRecord.objects.all()), "animals_treated"), "color": "blue"},
        ]
        latest = {}
        for fid, sp, cnt in LivestockCount.objects.order_by("-date", "-id").values_list("farmer_id", "species", "count"):
            latest.setdefault((fid, sp), cnt)
        totals = {}
        for (fid, sp), cnt in latest.items():
            totals[sp] = totals.get(sp, 0) + cnt
        species = [{"label": label, "value": totals.get(code, 0)} for code, label in LIVESTOCK]
        for o in outbreaks.select_related("sub_county").order_by("-start_date")[:5]:
            alerts.append({
                "text": "Outbreak: %s in %s (%s confirmed cases)" % (o.disease, o.sub_county, o.confirmed_cases),
                "date": o.start_date,
                "url": reverse("reg_detail", args=["outbreak-management", o.pk]),
            })

    elif name == "Entomology":
        traps = Trap.objects.all()
        rows = [
            _row("Traps", "r_trap_register", traps, active),
            _row("Vector incidents", "r_vector_incidents", VectorIncident.objects.all(), active),
        ]
        inspections = _month(TrapInspection.objects.all())
        n_inspections = inspections.count()
        caught = _sum(_month(VectorCount.objects.all(), "inspection__date"), "number_caught")
        average = "%.1f" % (float(caught) / n_inspections) if n_inspections else "-"
        measures = [
            {"label": "Operational traps", "value": traps.filter(status="active").count(), "color": "green"},
            {"label": "Inspections this month", "value": n_inspections, "color": "blue"},
            {"label": "Traps inspected this month", "value": inspections.values("trap").distinct().count(), "color": "teal"},
            {"label": "Vectors caught this month", "value": caught, "color": "red"},
            {"label": "Average caught per inspection", "value": average, "color": "orange"},
            {"label": "Open vector incidents", "value": VectorIncident.objects.filter(status="active").count(), "color": "pink"},
        ]
        cutoff = today - timedelta(days=30)
        recent = set(TrapInspection.objects.filter(date__gte=cutoff).values_list("trap_id", flat=True))
        for t in traps.filter(status="active", installed_date__lte=cutoff).order_by("code"):
            if t.pk not in recent and len(alerts) < 5:
                alerts.append({
                    "text": "Trap %s has not been inspected in 30 days" % t.code,
                    "date": t.installed_date,
                    "url": reverse("reg_detail", args=["trap-register", t.pk]),
                })

    elif name == "Commercial":
        rows = [
            _row("Enterprises", "r_enterprises", Enterprise.objects.all(), active),
            _row("MSMEs", "r_msmes", MSME.objects.all(), active),
            _row("Markets", "r_markets", Market.objects.all(), active),
            _row("Value addition ventures", "r_value_addition", ValueAdditionVenture.objects.all(), active),
        ]
        loans = LoanIntervention.objects.all()
        perf = _month(EnterprisePerformance.objects.all())
        measures = [
            {"label": "Capital invested in enterprises (UGX)", "value": _money(_sum(Enterprise.objects.all(), "capital_ugx")), "color": "blue"},
            {"label": "Loans and support given (UGX)", "value": _money(_sum(loans, "amount_ugx")), "color": "green"},
            {"label": "Repaid so far (UGX)", "value": _money(_sum(loans, "repaid_ugx")), "color": "teal"},
            {"label": "Overdue loans", "value": loans.filter(status="overdue").count(), "color": "red"},
            {"label": "Revenue reported this month (UGX)", "value": _money(_sum(perf, "revenue_ugx")), "color": "orange"},
            {"label": "Market linkages this month", "value": _month(MarketLinkage.objects.all()).count(), "color": "purple"},
        ]
        for l in loans.filter(status="overdue").order_by("-date")[:5]:
            alerts.append({
                "text": "Overdue: %s (balance UGX %s)" % (l.description, _money(l.balance)),
                "date": l.date,
                "url": reverse("reg_detail", args=["loans-interventions", l.pk]),
            })

    return {"rows": rows, "measures": measures, "species": species, "alerts": alerts}