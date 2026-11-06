from django.db import models

from .crop_vet_models import FarmerGroup
from .reg_models import ACTIVE, Coded, Farmer, Place, Stamped

# ---------------------------------------------------------- Entomology


class Trap(Coded, Place):
    CODE_PREFIX = "TRP"
    TYPES = [
        ("biconical", "Biconical trap"),
        ("ngu", "NGU trap"),
        ("pyramidal", "Pyramidal trap"),
        ("odour", "Odour-baited trap"),
        ("other", "Other"),
    ]
    STATUS = [("active", "Operational"), ("damaged", "Damaged"), ("removed", "Removed")]
    trap_name = models.CharField("Trap name or description", max_length=100, blank=True)
    trap_type = models.CharField("Trap type", max_length=12, choices=TYPES, default="biconical")
    target_vector = models.CharField("Target vector", max_length=100, default="Tsetse fly")
    installed_date = models.DateField("Installation date")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="active")

    class Meta:
        ordering = ["code"]

    def __str__(self):
        label = self.code or "new trap"
        return "%s - %s" % (label, self.trap_name) if self.trap_name else label


class TrapInspection(Stamped):
    CONDITIONS = [("good", "Good"), ("damaged", "Damaged"), ("missing", "Missing")]
    trap = models.ForeignKey(Trap, on_delete=models.PROTECT, related_name="inspections")
    date = models.DateField()
    condition = models.CharField(max_length=10, choices=CONDITIONS, default="good")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return "%s on %s" % (self.trap.code, self.date)


class VectorCount(Stamped):
    inspection = models.ForeignKey(TrapInspection, on_delete=models.PROTECT, related_name="counts")
    species = models.CharField(max_length=100, default="Tsetse fly")
    number_caught = models.PositiveIntegerField("Number caught", default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-inspection__date", "-id"]


class SurveillanceRound(Place):
    date = models.DateField()
    vector = models.CharField(max_length=100, default="Tsetse fly")
    method = models.CharField(max_length=100, blank=True)
    traps_set = models.PositiveIntegerField("Traps set", default=0)
    traps_recovered = models.PositiveIntegerField("Traps recovered", default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class VectorIncident(Place):
    TYPES = [
        ("disease_case", "Disease case linked to a vector"),
        ("infestation", "Infestation"),
        ("human_case", "Human case"),
        ("animal_case", "Animal case"),
        ("other", "Other"),
    ]
    STATUS = [("active", "Open"), ("closed", "Closed")]
    date = models.DateField()
    vector = models.CharField(max_length=100)
    incident_type = models.CharField("Incident type", max_length=14, choices=TYPES, default="other")
    cases = models.PositiveIntegerField(default=0)
    response_actions = models.TextField("Response actions", blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="active")

    class Meta:
        ordering = ["-date", "-id"]


class Equipment(Stamped):
    SECTORS = [
        ("Fisheries", "Fisheries"),
        ("Entomology", "Entomology"),
        ("Crops", "Crops"),
        ("Veterinary", "Veterinary"),
        ("Commercial", "Commercial"),
    ]
    STATUS = [("active", "In use"), ("repair", "Needs repair"), ("lost", "Lost or disposed")]
    sector = models.CharField(max_length=12, choices=SECTORS)
    item = models.CharField(max_length=100)
    category = models.CharField(max_length=60, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    date_received = models.DateField("Date received")
    holder = models.CharField("Held by or kept at", max_length=150, blank=True)
    sub_county = models.ForeignKey(
        "core.SubCounty", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    status = models.CharField(max_length=10, choices=STATUS, default="active")

    class Meta:
        ordering = ["-id"]


# ---------------------------------------------------------- Commercial


class Enterprise(Coded, Place):
    CODE_PREFIX = "EN"
    TYPES = [
        ("crop", "Crop enterprise"),
        ("livestock", "Livestock enterprise"),
        ("fish", "Fish enterprise"),
        ("processing", "Agro-processing"),
        ("trading", "Trading"),
        ("other", "Other"),
    ]
    name = models.CharField(max_length=150)
    enterprise_type = models.CharField("Enterprise type", max_length=12, choices=TYPES, default="other")
    description = models.TextField(blank=True)
    owner = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="enterprises")
    owner_name = models.CharField("Owner name (if not in the farmer registry)", max_length=150, blank=True)
    group = models.ForeignKey(FarmerGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="enterprises")
    pdm_beneficiary = models.ForeignKey(
        "core.PDMBeneficiary", null=True, blank=True, on_delete=models.SET_NULL, related_name="enterprises"
    )
    started_date = models.DateField("Date started", null=True, blank=True)
    capital_ugx = models.PositiveBigIntegerField("Capital invested (UGX)", default=0)
    employees = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return "%s (%s)" % (self.name, self.code or "new")


class Market(Place):
    TYPES = [("produce", "Produce"), ("livestock", "Livestock"), ("fish", "Fish"), ("general", "General")]
    name = models.CharField(max_length=150)
    market_type = models.CharField("Market type", max_length=10, choices=TYPES, default="general")
    market_day = models.CharField("Market day", max_length=40, blank=True)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ValueAdditionVenture(Place):
    name = models.CharField(max_length=150)
    product = models.CharField(max_length=150)
    raw_material = models.CharField("Raw material", max_length=150, blank=True)
    capacity = models.CharField("Capacity per month", max_length=60, blank=True)
    owner = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    group = models.ForeignKey(FarmerGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MSME(Place):
    name = models.CharField("Business name", max_length=150)
    owner_name = models.CharField("Owner name", max_length=150, blank=True)
    owner = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    business_type = models.CharField("Type of business", max_length=100, blank=True)
    registered = models.BooleanField("Formally registered", default=False)
    employees = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["name"]
        verbose_name = "MSME"
        verbose_name_plural = "MSMEs"

    def __str__(self):
        return self.name


class LoanIntervention(Stamped):
    STATUS = [("active", "Ongoing"), ("repaid", "Repaid"), ("overdue", "Overdue")]
    date = models.DateField()
    description = models.CharField(max_length=200)
    source = models.CharField("Source of funds or support", max_length=100, blank=True)
    enterprise = models.ForeignKey(Enterprise, null=True, blank=True, on_delete=models.SET_NULL, related_name="loans")
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    group = models.ForeignKey(FarmerGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    amount_ugx = models.PositiveBigIntegerField("Amount (UGX)", default=0)
    repaid_ugx = models.PositiveBigIntegerField("Repaid so far (UGX)", default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="active")

    class Meta:
        ordering = ["-date", "-id"]

    @property
    def balance(self):
        return max(self.amount_ugx - self.repaid_ugx, 0)


class EnterprisePerformance(Stamped):
    enterprise = models.ForeignKey(Enterprise, on_delete=models.PROTECT, related_name="performance")
    date = models.DateField()
    period_label = models.CharField("Period", max_length=40, help_text="For example: October 2026")
    revenue_ugx = models.PositiveBigIntegerField("Revenue (UGX)", default=0)
    expenditure_ugx = models.PositiveBigIntegerField("Expenditure (UGX)", default=0)
    production_note = models.TextField("Production note", blank=True)
    employees = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    @property
    def profit(self):
        return self.revenue_ugx - self.expenditure_ugx


class MarketLinkage(Stamped):
    date = models.DateField()
    description = models.CharField(max_length=200)
    enterprise = models.ForeignKey(Enterprise, null=True, blank=True, on_delete=models.SET_NULL, related_name="linkages")
    group = models.ForeignKey(FarmerGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    buyer = models.CharField("Buyer or market", max_length=150)
    commodity = models.CharField(max_length=100)
    quantity = models.CharField(max_length=60, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


ENTCOM_MODELS = [
    Trap, TrapInspection, VectorCount, SurveillanceRound, VectorIncident, Equipment,
    Enterprise, Market, ValueAdditionVenture, MSME, LoanIntervention,
    EnterprisePerformance, MarketLinkage,
]