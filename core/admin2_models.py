from django.conf import settings
from django.db import models


class SystemSetting(models.Model):
    district_name = models.CharField(max_length=150, default="Soroti District Local Government")
    department_name = models.CharField(max_length=150, default="Production Department")
    cao_name = models.CharField("Chief Administrative Officer", max_length=150, blank=True)
    dpo_name = models.CharField("District Production Officer", max_length=150, blank=True)
    report_footer = models.CharField("Report footer text", max_length=250, blank=True)
    stale_draft_days = models.PositiveIntegerField("Warn about drafts older than (days)", default=7)
    licence_warning_days = models.PositiveIntegerField("Warn about licences expiring within (days)", default=30)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "System settings"


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=10)
    model_name = models.CharField(max_length=60, blank=True)
    object_id = models.CharField(max_length=30, blank=True)
    summary = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Document(models.Model):
    CATEGORIES = [
        ("policy", "Policy or guideline"),
        ("report", "Report"),
        ("workplan", "Work plan or budget"),
        ("form", "Form or template"),
        ("minutes", "Meeting minutes"),
        ("training", "Training material"),
        ("other", "Other"),
    ]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=10, choices=CATEGORIES, default="other")
    department = models.ForeignKey("core.Department", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    year = models.PositiveIntegerField("Year", null=True, blank=True)
    file = models.FileField(upload_to="documents/%Y/")
    description = models.CharField(max_length=250, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Partner(models.Model):
    TYPES = [
        ("ngo", "NGO or development partner"),
        ("government", "Government agency"),
        ("private", "Private company"),
        ("research", "Research or training institution"),
        ("community", "Community organisation"),
        ("other", "Other"),
    ]
    name = models.CharField(max_length=150)
    partner_type = models.CharField("Type", max_length=10, choices=TYPES, default="ngo")
    focus_area = models.CharField("Focus area", max_length=200, blank=True)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    STATUS = [
        ("planned", "Planned"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("stalled", "Stalled"),
    ]
    name = models.CharField(max_length=200)
    partner = models.ForeignKey(Partner, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="projects")
    department = models.ForeignKey("core.Department", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    sub_counties = models.ManyToManyField("core.SubCounty", blank=True, related_name="+")
    funder = models.CharField(max_length=150, blank=True)
    budget = models.PositiveBigIntegerField("Budget (UGX)", null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="ongoing")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date", "name"]

    def __str__(self):
        return self.name


from . import audit  # noqa: E402,F401