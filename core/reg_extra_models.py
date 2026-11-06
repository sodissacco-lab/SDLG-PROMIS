from django.db import models

from .reg_models import FishPond, LandingSite, Stamped


class PondMeasurement(Stamped):
    pond = models.ForeignKey(FishPond, on_delete=models.PROTECT, related_name="measurements")
    date = models.DateField()
    length_m = models.DecimalField("Length (m)", max_digits=7, decimal_places=1)
    width_m = models.DecimalField("Width (m)", max_digits=7, decimal_places=1)
    depth_m = models.DecimalField("Water depth (m)", max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    @property
    def area_sqm(self):
        return self.length_m * self.width_m


class FeedingRecord(Stamped):
    pond = models.ForeignKey(FishPond, on_delete=models.PROTECT, related_name="feedings")
    date = models.DateField()
    feed_type = models.CharField("Feed type", max_length=100)
    quantity_kg = models.DecimalField("Quantity (kg)", max_digits=8, decimal_places=1)

    class Meta:
        ordering = ["-date", "-id"]


class WaterQualityRecord(Stamped):
    pond = models.ForeignKey(FishPond, on_delete=models.PROTECT, related_name="water_checks")
    date = models.DateField()
    temperature_c = models.DecimalField("Temperature (C)", max_digits=4, decimal_places=1, null=True, blank=True)
    ph = models.DecimalField("pH", max_digits=3, decimal_places=1, null=True, blank=True)
    dissolved_oxygen = models.DecimalField("Dissolved oxygen (mg/L)", max_digits=4, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class FishProductionEstimate(Stamped):
    pond = models.ForeignKey(FishPond, on_delete=models.PROTECT, related_name="estimates")
    period_label = models.CharField("Period or season", max_length=50)
    estimated_kg = models.DecimalField("Estimated production (kg)", max_digits=10, decimal_places=1)
    basis = models.CharField("How it was estimated", max_length=200, blank=True)

    class Meta:
        ordering = ["-id"]


class FishingGear(Stamped):
    GEARS = [
        ("gillnet", "Gillnet"),
        ("hook", "Hook and line"),
        ("seine", "Seine net"),
        ("trap", "Trap or basket"),
        ("other", "Other"),
    ]
    LEGAL = [
        ("legal", "Legal"),
        ("illegal", "Illegal"),
        ("review", "Under review"),
    ]
    landing_site = models.ForeignKey(LandingSite, on_delete=models.PROTECT, related_name="gears")
    date = models.DateField()
    gear_type = models.CharField("Gear type", max_length=10, choices=GEARS)
    quantity = models.PositiveIntegerField(default=1)
    mesh_size_mm = models.PositiveIntegerField("Mesh size (mm)", null=True, blank=True)
    legal_status = models.CharField("Legal status", max_length=10, choices=LEGAL, default="legal")

    class Meta:
        ordering = ["-date", "-id"]


EXTRA_MODELS = [
    PondMeasurement,
    FeedingRecord,
    WaterQualityRecord,
    FishProductionEstimate,
    FishingGear,
]