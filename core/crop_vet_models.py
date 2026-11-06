from django.db import models

from .reg_models import ACTIVE, Farmer, Place, Stamped

LIVESTOCK = [
    ("cattle", "Cattle"),
    ("goats", "Goats"),
    ("sheep", "Sheep"),
    ("pigs", "Pigs"),
    ("poultry", "Poultry"),
]
SPECIES = LIVESTOCK + [("other", "Other")]


def _sub_county():
    return models.ForeignKey("core.SubCounty", on_delete=models.PROTECT, related_name="+")


# ---------------------------------------------------------------- Crops


class FarmerGroup(Place):
    TYPES = [("group", "Farmer group"), ("sacco", "SACCO"), ("coop", "Cooperative")]
    name = models.CharField(max_length=150)
    group_type = models.CharField("Type", max_length=10, choices=TYPES, default="group")
    chairperson = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    members_count = models.PositiveIntegerField("Number of members", default=0)
    focus = models.CharField("Main enterprise", max_length=150, blank=True)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GroupMember(Stamped):
    group = models.ForeignKey(FarmerGroup, on_delete=models.PROTECT, related_name="members")
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="group_memberships")
    role = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["group__name", "farmer__name"]
        unique_together = ("group", "farmer")


class CropVariety(models.Model):
    crop = models.CharField(max_length=100)
    name = models.CharField("Variety", max_length=100)
    characteristics = models.TextField(blank=True)

    class Meta:
        ordering = ["crop", "name"]
        unique_together = ("crop", "name")
        verbose_name_plural = "crop varieties"

    def __str__(self):
        return "%s - %s" % (self.crop, self.name)


class CropGrown(Stamped):
    STATUS = [("active", "Growing"), ("harvested", "Harvested"), ("failed", "Failed")]
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="crops")
    crop = models.CharField(max_length=100)
    variety = models.ForeignKey(
        CropVariety, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    season = models.CharField(max_length=40, help_text="For example: 2026 first rains")
    acreage = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    planting_date = models.DateField("Planting date", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="active")

    class Meta:
        ordering = ["-id"]
        verbose_name_plural = "crops grown"

    def __str__(self):
        return "%s - %s (%s)" % (self.farmer.name, self.crop, self.season)


class PlantingRecord(Stamped):
    crop_grown = models.ForeignKey(CropGrown, on_delete=models.PROTECT, related_name="plantings")
    date = models.DateField()
    seed_kg = models.DecimalField("Seed used (kg)", max_digits=8, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class CropHarvest(Stamped):
    crop_grown = models.ForeignKey(CropGrown, on_delete=models.PROTECT, related_name="harvests")
    date = models.DateField()
    quantity_kg = models.DecimalField("Quantity (kg)", max_digits=10, decimal_places=1)

    class Meta:
        ordering = ["-date", "-id"]


class CropProductionEstimate(Stamped):
    sub_county = _sub_county()
    crop = models.CharField(max_length=100)
    season = models.CharField(max_length=40)
    estimated_tonnes = models.DecimalField("Estimated production (tonnes)", max_digits=10, decimal_places=1)
    basis = models.CharField("How it was estimated", max_length=200, blank=True)

    class Meta:
        ordering = ["-id"]


class AgriInput(Stamped):
    TYPES = [
        ("seed", "Seed or planting material"),
        ("fertiliser", "Fertiliser"),
        ("chemical", "Pesticide or chemical"),
        ("tools", "Tools or equipment"),
        ("other", "Other"),
    ]
    date = models.DateField()
    input_type = models.CharField("Type", max_length=12, choices=TYPES)
    item = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=1)
    unit = models.CharField(max_length=20, default="kg")
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="inputs")
    group = models.ForeignKey(FarmerGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="inputs")
    sub_county = _sub_county()

    class Meta:
        ordering = ["-date", "-id"]


class DemonstrationFarm(Place):
    host = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="demo_farms")
    crop = models.CharField(max_length=100)
    technology = models.CharField("Technology shown", max_length=200, blank=True)
    established = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["-id"]


class PestDiseaseReport(Stamped):
    SEVERITY = [("low", "Low"), ("moderate", "Moderate"), ("high", "High")]
    date = models.DateField()
    crop = models.CharField(max_length=100)
    pest_or_disease = models.CharField("Pest or disease", max_length=100)
    severity = models.CharField(max_length=10, choices=SEVERITY, default="low")
    area_affected_acres = models.DecimalField("Area affected (acres)", max_digits=8, decimal_places=1, default=0)
    sub_county = _sub_county()
    parish = models.ForeignKey("core.Parish", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action_taken = models.TextField("Action taken", blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class PostHarvestRecord(Stamped):
    date = models.DateField()
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    crop = models.CharField(max_length=100)
    storage_method = models.CharField("Storage method", max_length=100, blank=True)
    loss_kg = models.DecimalField("Loss (kg)", max_digits=8, decimal_places=1, default=0)
    sub_county = _sub_county()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class MarketPrice(Stamped):
    CATEGORIES = [("crop", "Crop"), ("livestock", "Livestock"), ("fish", "Fish")]
    date = models.DateField()
    market = models.CharField(max_length=100)
    sub_county = _sub_county()
    category = models.CharField(max_length=10, choices=CATEGORIES, default="crop")
    commodity = models.CharField(max_length=100)
    unit = models.CharField(max_length=30, default="kg")
    price_ugx = models.PositiveBigIntegerField("Price (UGX)")

    class Meta:
        ordering = ["-date", "-id"]


class AgriIntervention(Stamped):
    date = models.DateField()
    description = models.CharField(max_length=200)
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="interventions")
    group = models.ForeignKey(FarmerGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="interventions")
    sub_county = _sub_county()
    cost_ugx = models.PositiveBigIntegerField("Cost (UGX)", default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class PDMEnterpriseLink(Stamped):
    beneficiary = models.ForeignKey("core.PDMBeneficiary", on_delete=models.PROTECT, related_name="crop_links")
    crop_grown = models.ForeignKey(CropGrown, on_delete=models.PROTECT, related_name="pdm_links")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-id"]


# ---------------------------------------------------------- Veterinary


class LivestockCount(Stamped):
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="livestock_counts")
    species = models.CharField(max_length=10, choices=LIVESTOCK)
    date = models.DateField()
    count = models.PositiveIntegerField("Number of animals")
    breed = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class AnimalHealthCase(Place):
    date = models.DateField()
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="health_cases")
    species = models.CharField(max_length=10, choices=SPECIES)
    animals_affected = models.PositiveIntegerField("Animals affected", default=1)
    signs = models.TextField("Clinical signs", blank=True)
    diagnosis = models.CharField(max_length=150, blank=True)
    treatment = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class VaccinationCampaign(Place):
    date = models.DateField()
    disease = models.CharField(max_length=100)
    species = models.CharField(max_length=10, choices=SPECIES)
    animals_eligible = models.PositiveIntegerField("Animals eligible", default=0)
    animals_vaccinated = models.PositiveIntegerField("Animals vaccinated", default=0)
    vaccine_batch = models.CharField("Vaccine batch", max_length=60, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    @property
    def coverage(self):
        if not self.animals_eligible:
            return "-"
        return "%d%%" % round(100.0 * self.animals_vaccinated / self.animals_eligible)


class DiseaseReport(Place):
    STATUS = [
        ("suspected", "Suspected"),
        ("confirmed", "Confirmed"),
        ("ruled_out", "Ruled out"),
    ]
    date = models.DateField()
    disease = models.CharField(max_length=100)
    species = models.CharField(max_length=10, choices=SPECIES)
    status = models.CharField(max_length=10, choices=STATUS, default="suspected")
    animals_affected = models.PositiveIntegerField("Animals affected", default=0)
    animals_dead = models.PositiveIntegerField("Animals dead", default=0)
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class Outbreak(Place):
    STATUS = [("active", "Active"), ("contained", "Contained"), ("closed", "Closed")]
    disease = models.CharField(max_length=100)
    start_date = models.DateField("Start date")
    end_date = models.DateField("End date", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="active")
    confirmed_cases = models.PositiveIntegerField("Confirmed cases", default=0)
    animals_dead = models.PositiveIntegerField("Animals dead", default=0)
    response_actions = models.TextField("Response actions", blank=True)

    class Meta:
        ordering = ["-start_date", "-id"]


class TreatmentRecord(Place):
    date = models.DateField()
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    species = models.CharField(max_length=10, choices=SPECIES)
    drug = models.CharField(max_length=100)
    animals_treated = models.PositiveIntegerField("Animals treated", default=1)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class AIService(Place):
    date = models.DateField()
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="ai_services")
    animal_tag = models.CharField("Animal tag or name", max_length=40, blank=True)
    semen_used = models.CharField("Semen used", max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class LivestockMarket(Place):
    name = models.CharField(max_length=150)
    market_day = models.CharField("Market day", max_length=40, blank=True)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SlaughterRecord(Place):
    date = models.DateField()
    slaughter_place = models.CharField("Slaughter place", max_length=150)
    species = models.CharField(max_length=10, choices=SPECIES)
    number_slaughtered = models.PositiveIntegerField("Number slaughtered", default=0)
    number_inspected = models.PositiveIntegerField("Number inspected", default=0)

    class Meta:
        ordering = ["-date", "-id"]


class LivestockMortality(Place):
    date = models.DateField()
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    species = models.CharField(max_length=10, choices=SPECIES)
    number_dead = models.PositiveIntegerField("Number dead", default=1)
    suspected_cause = models.CharField("Suspected cause", max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name_plural = "livestock mortality"


class DrugVaccineStock(Stamped):
    ITEMS = [("drug", "Drug"), ("vaccine", "Vaccine")]
    TRANSACTIONS = [
        ("received", "Received"),
        ("used", "Used"),
        ("expired", "Expired"),
        ("adjusted", "Adjusted"),
    ]
    date = models.DateField()
    item = models.CharField(max_length=100)
    item_type = models.CharField("Type", max_length=10, choices=ITEMS)
    transaction = models.CharField(max_length=10, choices=TRANSACTIONS)
    quantity = models.PositiveIntegerField()
    batch_number = models.CharField("Batch number", max_length=60, blank=True)
    expiry_date = models.DateField("Expiry date", null=True, blank=True)

    class Meta:
        ordering = ["-date", "-id"]


CROPVET_MODELS = [
    FarmerGroup, GroupMember, CropVariety, CropGrown, PlantingRecord, CropHarvest,
    CropProductionEstimate, AgriInput, DemonstrationFarm, PestDiseaseReport,
    PostHarvestRecord, MarketPrice, AgriIntervention, PDMEnterpriseLink,
    LivestockCount, AnimalHealthCase, VaccinationCampaign, DiseaseReport, Outbreak,
    TreatmentRecord, AIService, LivestockMarket, SlaughterRecord, LivestockMortality,
    DrugVaccineStock,
]