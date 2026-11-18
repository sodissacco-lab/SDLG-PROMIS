from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_loginthrottle"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dpo_email", models.EmailField(blank=True, help_text="District Production Officer's email address", max_length=254)),
                ("cc_emails", models.CharField(blank=True, help_text="Optional extra addresses, separated by commas", max_length=300)),
                ("auto_enabled", models.BooleanField(default=True)),
                ("remind_every_days", models.PositiveIntegerField(default=7)),
            ],
        ),
        migrations.CreateModel(
            name="ReportSendLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=120, unique=True)),
                ("kind", models.CharField(max_length=30)),
                ("label", models.CharField(blank=True, max_length=200)),
                ("ok", models.BooleanField(default=False)),
                ("note", models.CharField(blank=True, max_length=300)),
                ("sent_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-sent_at"]},
        ),
    ]
