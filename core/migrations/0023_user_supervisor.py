import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_report_schedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="supervisor",
            field=models.ForeignKey(
                blank=True,
                help_text="Who reviews and approves this officer's entries",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reports",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
