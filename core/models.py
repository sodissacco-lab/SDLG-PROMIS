from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLES = [
        ("admin", "System Administrator"),
        ("dpo", "District Production Officer"),
        ("head", "Section Head"),
        ("subcounty", "Sub-county Officer"),
        ("extension", "Extension Officer"),
        ("clerk", "Data Clerk"),
        ("viewer", "Viewer"),
    ]
    role = models.CharField(max_length=20, choices=ROLES, default="extension")
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL
    )
    sub_county = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)


class SubCounty(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Sub-counties"

    def __str__(self):
        return self.name


class Parish(models.Model):
    sub_county = models.ForeignKey(
        SubCounty, on_delete=models.CASCADE, related_name="parishes"
    )
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("sub_county", "name")
        verbose_name_plural = "Parishes"

    def __str__(self):
        return f"{self.name} ({self.sub_county})"


class Activity(models.Model):
    STATUS = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("returned", "Returned for correction"),
    ]
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="activities"
    )
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    activity_type = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    sub_county = models.ForeignKey(
        SubCounty, null=True, blank=True, on_delete=models.SET_NULL
    )
    parish = models.ForeignKey(
        Parish, null=True, blank=True, on_delete=models.SET_NULL
    )
    village = models.CharField(max_length=100, blank=True)
    landing_site = models.ForeignKey(
        "core.LandingSite",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities",
        verbose_name="Landing site (if the activity concerns one)",
    )
    farmer = models.ForeignKey(
        "core.Farmer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities",
        limit_choices_to=~models.Q(status="merged"),
        verbose_name="Farmer (if the activity concerns one)",
    )
    pond = models.ForeignKey(
        "core.FishPond",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities",
        verbose_name="Fish pond (if the activity concerns one)",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    male = models.PositiveIntegerField(default=0)
    female = models.PositiveIntegerField(default=0)
    youth = models.PositiveIntegerField(default=0)
    pwd = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    findings = models.TextField(blank=True)
    action_taken = models.TextField(blank=True)
    follow_up = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_activities",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name_plural = "Activities"

    @property
    def total_beneficiaries(self):
        return self.male + self.female

    def __str__(self):
        return f"{self.date} - {self.activity_type} ({self.officer})"


class Target(models.Model):
    MEASURES = [
        ("activities", "Number of activities"),
        ("reached", "People reached"),
    ]
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    activity_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Leave empty to count every activity type in the department.",
    )
    measure = models.CharField(max_length=20, choices=MEASURES, default="activities")
    fiscal_year = models.PositiveIntegerField(
        help_text="Year the financial year starts, e.g. 2026 for July 2026 to June 2027."
    )
    q1 = models.PositiveIntegerField("Quarter 1 target (Jul-Sep)", default=0)
    q2 = models.PositiveIntegerField("Quarter 2 target (Oct-Dec)", default=0)
    q3 = models.PositiveIntegerField("Quarter 3 target (Jan-Mar)", default=0)
    q4 = models.PositiveIntegerField("Quarter 4 target (Apr-Jun)", default=0)

    class Meta:
        ordering = ["-fiscal_year", "department__name", "activity_type"]

    @property
    def annual(self):
        return self.q1 + self.q2 + self.q3 + self.q4

    def __str__(self):
        what = self.activity_type or "All activities"
        return f"FY {self.fiscal_year}: {self.department} - {what}"


from .pdm_models import PDMBeneficiary, PDMGroup, PDMVisit  # noqa: E402,F401
from .photo_models import ActivityPhoto  # noqa: E402,F401
from . import reg_models  # noqa: E402,F401
from . import reg_extra_models  # noqa: E402,F401
from . import crop_vet_models  # noqa: E402,F401
from . import ent_com_models  # noqa: E402,F401
from . import ent2_models  # noqa: E402,
from . import vet2_models  # noqa: E402,F401
from . import admin2_models  # noqa: E402,F401
from . import permit_models  # noqa: E402,F401
from . import pwa_models  # noqa: E402,F401