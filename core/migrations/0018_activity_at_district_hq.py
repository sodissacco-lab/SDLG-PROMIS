from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_offlinesync"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="other_activity",
            field=models.CharField(
                blank=True,
                help_text="Used when the activity type is Other. This is what shows on the record.",
                max_length=120,
                verbose_name="Describe the activity",
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="at_district_hq",
            field=models.BooleanField(
                default=False,
                help_text="Tick for meetings, office work or training at the district headquarters. Sub-county and parish are then not needed.",
                verbose_name="Held at the district headquarters",
            ),
        ),
    ]
