from django.db import models

from .crop_vet_models import (
    AIService,
    LivestockCount,
    LivestockMarket,
    SlaughterRecord,
    TreatmentRecord,
)
from .reg_models import Farmer, Place

SPECIES = [
    ("cattle", "Cattle"),
    ("goat", "Goat"),
    ("sheep", "Sheep"),
    ("pig", "Pig"),
    ("chicken", "Chicken"),
    ("dog", "Dog"),
    ("cat", "Cat"),
    ("other", "Other"),
]
SEX = [("M", "Male"), ("F", "Female")]


class DiseaseSurveillance(Place):
    RECORD_TYPES = [
        ("case", "Sick animal case"),
        ("outbreak", "Outbreak"),
        ("mortality", "Deaths"),
        ("report", "Surveillance report"),
    ]
    STATUS = [
        ("suspected", "Suspected"),
        ("confirmed", "Confirmed"),
        ("ruled_out", "Ruled out"),
    ]
    OUTBREAK = [
        ("ongoing", "Ongoing"),
        ("controlled", "Under control"),
        ("closed", "Closed"),
    ]
    date = models.DateField()
    record_type = models.CharField("Record type", max_length=10, choices=RECORD_TYPES, default="case")
    species = models.CharField(max_length=10, choices=SPECIES, default="cattle")
    disease = models.CharField("Disease or suspected disease", max_length=150)
    diagnosis_status = models.CharField("Diagnosis", max_length=10, choices=STATUS, default="suspected")
    farmer = models.ForeignKey(Farmer, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    animals_at_risk = models.PositiveIntegerField("Animals at risk", default=0)
    animals_sick = models.PositiveIntegerField("Animals sick", default=0)
    animals_dead = models.PositiveIntegerField("Animals dead", default=0)
    sample_taken = models.BooleanField("Sample sent to laboratory", default=False)
    lab_result = models.CharField("Laboratory result", max_length=200, blank=True)
    action_taken = models.TextField("Action taken (treatment, quarantine, vaccination)", blank=True)
    outbreak_status = models.CharField("Outbreak status", max_length=10, choices=OUTBREAK, blank=True)
    reported_upward = models.BooleanField("Reported to the Ministry or region", default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "disease surveillance record"

    def __str__(self):
        return "%s - %s (%s)" % (self.disease, self.get_species_display(), self.date)


# ---- new fields on existing Veterinary registers (no edits to your old files) ----
AIService.add_to_class("service_time", models.TimeField("Time of service", null=True, blank=True))
AIService.add_to_class(
    "heat_type",
    models.CharField("Heat", max_length=8, blank=True,
                     choices=[("natural", "Natural heat"), ("induced", "Induced heat")]),
)
AIService.add_to_class("semen_breed", models.CharField("Semen breed", max_length=80, blank=True))
AIService.add_to_class("bull_name", models.CharField("Bull name", max_length=80, blank=True))
AIService.add_to_class("calves_produced", models.PositiveIntegerField("Calves produced", null=True, blank=True))

TreatmentRecord.add_to_class("animal_sex", models.CharField("Sex", max_length=1, choices=SEX, blank=True))
TreatmentRecord.add_to_class("age_value", models.PositiveIntegerField("Age", null=True, blank=True))
TreatmentRecord.add_to_class(
    "age_unit",
    models.CharField("Age unit", max_length=6, blank=True,
                     choices=[("months", "Months"), ("years", "Years")]),
)

LivestockCount.add_to_class("dogs", models.PositiveIntegerField("Dogs", default=0))
LivestockCount.add_to_class("cats", models.PositiveIntegerField("Cats", default=0))
LivestockCount.add_to_class("chicken", models.PositiveIntegerField("Chicken", default=0))

LivestockMarket.add_to_class(
    "animal_category",
    models.CharField("Animal category", max_length=10, blank=True,
                     choices=[("cattle", "Cattle"), ("goats", "Goats"), ("sheep", "Sheep"),
                              ("pigs", "Pigs"), ("chicken", "Chicken"), ("other", "Other")]),
)
LivestockMarket.add_to_class("number_sold", models.PositiveIntegerField("Number sold", default=0))
LivestockMarket.add_to_class("price_per_animal", models.PositiveBigIntegerField("Price per animal (UGX)", null=True, blank=True))
LivestockMarket.add_to_class("destination", models.CharField("Where the animals are travelling to", max_length=150, blank=True))

SlaughterRecord.add_to_class(
    "judgement",
    models.CharField("Inspection j" \
    "udgement", max_length=20, blank=True,
                     choices=[("passed", "Passed fit"),
                              ("condemned_carcase", "Condemned: whole carcase"),
                              ("condemned_organ", "Condemned: organ"),
                              ("trimmed_organ", "Trimmed: organ"),
                              ("trimmed_carcase", "Trimmed: carcase")]),
)
SlaughterRecord.add_to_class("organ_affected", models.CharField("Organ affected (specify)", max_length=100, blank=True))
SlaughterRecord.add_to_class("number_affected", models.PositiveIntegerField("Number of animals affected", default=0))

VET2_MODELS = [DiseaseSurveillance]