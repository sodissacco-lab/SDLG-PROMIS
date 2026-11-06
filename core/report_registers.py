from datetime import timedelta

from django.db.models import Sum

from .crop_vet_models import (
    AgriInput,
    CropGrown,
    CropHarvest,
    DemonstrationFarm,
    DiseaseReport,
    FarmerGroup,
    LivestockCount,
    Outbreak,
    PestDiseaseReport,
    TreatmentRecord,
    VaccinationCampaign,
)
from .reg_models import (
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
    MortalityRecord,
    StockingRecord,
)


def _row(label, qs, start, end, active=None):
    return [
        label,
        qs.filter(created_at__date__lte=end).count(),
        qs.filter(created_at__date__gte=start, created_at__date__lte=end).count(),
        qs.filter(**active).count() if active else "-",
    ]


def _in(qs, start, end, field="date"):
    return qs.filter(**{field + "__gte": start, field + "__lte": end})


def _sum(qs, field):
    return qs.aggregate(t=Sum(field))["t"] or 0


def register_tables(period, department=None, sub_county=None):
    start, end = period["start"], period["end"]
    name = department.name if department else None

    def sc(qs, path):
        return qs.filter(**{path: sub_county}) if sub_county else qs

    active = {"status": "active"}
    farmers = sc(Farmer.objects.exclude(status="merged"), "sub_county")
    rows, measured = [], []

    if name is None:
        rows += [
            _row("Farmers (all sectors)", farmers, start, end, active),
            _row("Households", sc(Household.objects.all(), "sub_county"), start, end),
        ]

    if name in (None, "Crops"):
        rows += [
            _row("Farmers who grow crops", farmers.filter(grows_crops=True), start, end, active),
            _row("Farmer groups & cooperatives", sc(FarmerGroup.objects.all(), "sub_county"), start, end, active),
            _row("Demonstration farms", sc(DemonstrationFarm.objects.all(), "sub_county"), start, end, active),
            _row("Crop records", sc(CropGrown.objects.all(), "farmer__sub_county"), start, end, active),
        ]
        pests = _in(sc(PestDiseaseReport.objects.all(), "sub_county"), start, end)
        measured += [
            ["Acreage under crops now", _sum(sc(CropGrown.objects.filter(status="active"), "farmer__sub_county"), "acreage")],
            ["Harvest recorded (kg)", _sum(_in(sc(CropHarvest.objects.all(), "crop_grown__farmer__sub_county"), start, end), "quantity_kg")],
            ["Input distributions", _in(sc(AgriInput.objects.all(), "sub_county"), start, end).count()],
            ["Pest and disease reports", pests.count()],
            ["High-severity pest and disease reports", pests.filter(severity="high").count()],
        ]

    if name in (None, "Veterinary"):
        rows.append(_row("Farmers who keep livestock", farmers.filter(keeps_livestock=True), start, end, active))
        reports = _in(sc(DiseaseReport.objects.all(), "sub_county"), start, end)
        campaigns = _in(sc(VaccinationCampaign.objects.all(), "sub_county"), start, end)
        eligible = _sum(campaigns, "animals_eligible")
        vaccinated = _sum(campaigns, "animals_vaccinated")
        measured += [
            ["Suspected disease reports", reports.filter(status="suspected").count()],
            ["Confirmed disease reports", reports.filter(status="confirmed").count()],
            ["Outbreaks started", _in(sc(Outbreak.objects.all(), "sub_county"), start, end, "start_date").count()],
            ["Outbreaks active now", sc(Outbreak.objects.filter(status="active"), "sub_county").count()],
            ["Animals vaccinated", vaccinated],
            ["Vaccination coverage", "%d%%" % round(100.0 * vaccinated / eligible) if eligible else "-"],
            ["Animals treated", _sum(_in(sc(TreatmentRecord.objects.all(), "sub_county"), start, end), "animals_treated")],
            ["Livestock counts recorded", _in(sc(LivestockCount.objects.all(), "farmer__sub_county"), start, end).count()],
        ]

    if name in (None, "Fisheries"):
        rows += [
            _row("Landing sites", sc(LandingSite.objects.all(), "sub_county"), start, end, active),
            _row("Boats", sc(Boat.objects.all(), "landing_site__sub_county"), start, end, active),
            _row("Boat owners", sc(BoatOwner.objects.all(), "sub_county"), start, end),
            _row("Fishers", sc(Fisher.objects.all(), "sub_county"), start, end, active),
            _row("Fish farmers", farmers.filter(fish_farming=True), start, end, active),
            _row("Fish ponds", sc(FishPond.objects.all(), "sub_county"), start, end, active),
            _row("Cage farms", sc(CageFarm.objects.all(), "sub_county"), start, end, active),
        ]
        licences = sc(FishingLicence.objects.all(), "boat__landing_site__sub_county")
        measured += [
            ["Catch recorded (kg)", _sum(_in(sc(DailyCatch.objects.all(), "landing_site__sub_county"), start, end), "quantity_kg")],
            ["Revenue collected (UGX)", "{:,}".format(_sum(_in(sc(LandingSiteRevenue.objects.all(), "landing_site__sub_county"), start, end), "amount"))],
            ["Fish harvested (kg)", _sum(_in(sc(HarvestRecord.objects.all(), "pond__sub_county"), start, end), "quantity_kg")],
            ["Fingerlings stocked", _sum(_in(sc(StockingRecord.objects.all(), "pond__sub_county"), start, end), "fingerlings")],
            ["Fish deaths recorded", _sum(_in(sc(MortalityRecord.objects.all(), "pond__sub_county"), start, end), "number_dead")],
            ["Illegal fishing incidents", _in(sc(IllegalFishingIncident.objects.all(), "sub_county"), start, end).count()],
            ["Licences issued", _in(licences, start, end, "issue_date").count()],
            ["Licences valid at the end of the period", licences.filter(issue_date__lte=end, expiry_date__gte=end).count()],
            ["Licences expiring within 30 days of the end", licences.filter(expiry_date__gte=end, expiry_date__lte=end + timedelta(days=30)).count()],
        ]

    tables = []
    if rows:
        tables.append(
            {
                "title": "Register statistics (registered to date, new in the period, active now)",
                "header": ["Register", "Registered to date", "New in the period", "Active now"],
                "rows": rows,
            }
        )
    if measured:
        tables.append(
            {"title": "Measured results in the period", "header": ["Indicator", "Total"], "rows": measured}
        )
    return tables