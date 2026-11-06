from django.conf import settings
from django.db import models


class PDMGroup(models.Model):
    name = models.CharField(max_length=150)
    sub_county = models.ForeignKey("core.SubCounty", on_delete=models.PROTECT)
    parish = models.ForeignKey("core.Parish", on_delete=models.PROTECT)
    village = models.CharField(max_length=100, blank=True)
    enterprise = models.CharField(
        max_length=150, blank=True, help_text="Main enterprise of the group"
    )
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pdm_groups"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "parish")
        verbose_name = "PDM group"

    def __str__(self):
        return "%s (%s)" % (self.name, self.parish.name)


class PDMBeneficiary(models.Model):
    SEX = [("F", "Female"), ("M", "Male")]
    LOAN = [
        ("none", "No loan yet"),
        ("ongoing", "Loan ongoing"),
        ("repaid", "Fully repaid"),
        ("overdue", "Overdue"),
    ]
    name = models.CharField(max_length=150)
    sex = models.CharField(max_length=1, choices=SEX)
    phone = models.CharField(max_length=20, blank=True)
    group = models.ForeignKey(
        PDMGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    sub_county = models.ForeignKey("core.SubCounty", on_delete=models.PROTECT)
    parish = models.ForeignKey("core.Parish", on_delete=models.PROTECT)
    village = models.CharField(max_length=100, blank=True)
    enterprise = models.CharField(max_length=150, blank=True)
    youth = models.BooleanField(default=False)
    pwd = models.BooleanField("Person with disability", default=False)
    amount_received = models.PositiveBigIntegerField(
        "Amount received (UGX)", default=0
    )
    date_received = models.DateField(null=True, blank=True)
    loan_status = models.CharField(max_length=10, choices=LOAN, default="none")
    notes = models.TextField(blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pdm_beneficiaries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "PDM beneficiary"
        verbose_name_plural = "PDM beneficiaries"

    def __str__(self):
        return "%s (%s)" % (self.name, self.parish.name)


class PDMVisit(models.Model):
    STATUS = [
        ("good", "Doing well"),
        ("fair", "Fair"),
        ("poor", "Struggling"),
        ("collapsed", "Collapsed"),
    ]
    beneficiary = models.ForeignKey(
        PDMBeneficiary, on_delete=models.CASCADE, related_name="visits"
    )
    date = models.DateField()
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pdm_visits"
    )
    enterprise_status = models.CharField(max_length=10, choices=STATUS)
    revenue = models.PositiveBigIntegerField("Revenue (UGX)", default=0)
    expenditure = models.PositiveBigIntegerField("Expenditure (UGX)", default=0)
    production = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    action_taken = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "PDM monitoring visit"

    def __str__(self):
        return "%s - %s" % (self.beneficiary.name, self.date)