from django.db import models


class ReportSettings(models.Model):
    """One row. Who receives the automatic reports."""

    dpo_email = models.EmailField(blank=True, help_text="District Production Officer's email address")
    cc_emails = models.CharField(max_length=300, blank=True, help_text="Optional extra addresses, separated by commas")
    auto_enabled = models.BooleanField(default=True)
    remind_every_days = models.PositiveIntegerField(default=7)
    require_approval = models.BooleanField(
        default=True, help_text="When off, submitted entries are approved automatically"
    )

    @classmethod
    def get(cls):
        obj = cls.objects.first()
        return obj or cls.objects.create()

    def cc_list(self):
        return [e.strip() for e in self.cc_emails.split(",") if e.strip()]

    def __str__(self):
        return "Report settings"


class ReportSendLog(models.Model):
    """Remembers what was sent, so nothing is sent twice."""

    key = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=30)
    label = models.CharField(max_length=200, blank=True)
    ok = models.BooleanField(default=False)
    note = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return self.key
