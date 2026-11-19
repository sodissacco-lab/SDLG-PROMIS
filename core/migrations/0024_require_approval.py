from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_user_supervisor"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportsettings",
            name="require_approval",
            field=models.BooleanField(
                default=True, help_text="When off, submitted entries are approved automatically"
            ),
        ),
    ]
