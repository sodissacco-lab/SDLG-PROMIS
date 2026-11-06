from django.db import models

from .crop_vet_models import FarmerGroup
from .reg_models import ACTIVE, Farmer, Place, Stamped


class Apiary(Place):
    HIVE_TYPES = [
        ("langstroth", "Langstroth hive"),
        ("top_bar", "Kenya top-bar hive"),
        ("traditional", "Traditional or log hive"),
        ("other", "Other"),
    ]
    name = models.CharField("Apiary name", max_length=150, blank=True)
    owner = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="apiaries")
    group = models.ForeignKey(FarmerGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="apiaries")
    hive_type = models.CharField("Hive type", max_length=12, choices=HIVE_TYPES, default="top_bar")
    hives = models.PositiveIntegerField("Number of hives", default=0)
    colonised_hives = models.PositiveIntegerField("Hives with bees", default=0)
    started_date = models.DateField("Date started", null=True, blank=True)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["-id"]
        verbose_name_plural = "apiaries"

    def __str__(self):
        return self.name or "Apiary %s" % self.pk


class BSFUnit(Place):
    TYPES = [
        ("rearing", "Larvae rearing unit"),
        ("processing", "Waste processing unit"),
        ("both", "Rearing and processing"),
    ]
    owner = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="bsf_units")
    group = models.ForeignKey(FarmerGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="bsf_units")
    unit_type = models.CharField("Unit type", max_length=12, choices=TYPES, default="rearing")
    waste_kg_per_week = models.DecimalField("Organic waste processed (kg per week)", max_digits=8, decimal_places=1, null=True, blank=True)
    larvae_use = models.CharField("What the larvae are used for", max_length=150, blank=True)
    started_date = models.DateField("Date started", null=True, blank=True)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["-id"]
        verbose_name = "black soldier fly unit"

    def __str__(self):
        return "BSF unit %s" % self.pk


class VerminReport(Place):
    VERMIN = [
        ("rats", "Rats and mice"),
        ("quelea", "Quelea birds"),
        ("monkeys", "Monkeys"),
        ("wild_pigs", "Wild pigs"),
        ("other", "Other"),
    ]
    WHERE = [
        ("crops", "Crops in the field"),
        ("stores", "Stores"),
        ("homes", "Homes"),
        ("other", "Other"),
    ]
    SEVERITY = [("low", "Low"), ("moderate", "Moderate"), ("high", "High")]
    date = models.DateField()
    vermin = models.CharField("Vermin", max_length=12, choices=VERMIN)
    where_found = models.CharField("Where found", max_length=10, choices=WHERE, default="crops")
    severity = models.CharField(max_length=10, choices=SEVERITY, default="low")
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    control_action = models.CharField("Control action taken", max_length=200, blank=True)
    controlled = models.BooleanField("Control carried out", default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class Collaboration(Stamped):
    PARTNER_TYPES = [
        ("ngo", "NGO or development partner"),
        ("department", "Government department"),
        ("research", "Research or training institution"),
        ("private", "Private company"),
        ("community", "Community group"),
        ("other", "Other"),
    ]
    date = models.DateField()
    partner = models.CharField(max_length=150)
    partner_type = models.CharField("Partner type", max_length=12, choices=PARTNER_TYPES, default="other")
    topic = models.CharField(max_length=200)
    outcome = models.TextField(blank=True)
    sub_county = models.ForeignKey(
        "core.SubCounty", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-date", "-id"]


ENT2_MODELS = [Apiary, BSFUnit, VerminReport, Collaboration]