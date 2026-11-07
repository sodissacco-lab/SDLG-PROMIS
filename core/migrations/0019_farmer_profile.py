from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_activity_at_district_hq"),
    ]

    operations = [
        migrations.AddField(model_name="farmer", name="does_entomology", field=models.BooleanField(default=False, verbose_name="Bee-keeping or sericulture")),
        migrations.AddField(model_name="farmer", name="is_fisher", field=models.BooleanField(default=False, verbose_name="Fisher or boat owner")),
        migrations.AddField(model_name="farmer", name="national_id", field=models.CharField(blank=True, max_length=20, verbose_name="National ID (NIN)")),
        migrations.AddField(model_name="farmer", name="age_group", field=models.CharField(blank=True, choices=[("youth", "Youth (18 to 30)"), ("adult", "Adult (31 to 59)"), ("elder", "Elder (60 and above)")], max_length=10)),
        migrations.AddField(model_name="farmer", name="farm_size", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Farm size")),
        migrations.AddField(model_name="farmer", name="farm_size_unit", field=models.CharField(blank=True, choices=[("ponds", "Ponds"), ("boats", "Boats"), ("acres", "Acres"), ("animals", "Animals"), ("hives", "Beehives")], max_length=10, verbose_name="Unit of farm size")),
        migrations.AddField(model_name="farmer", name="years_farming", field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Years farming")),
        migrations.AddField(model_name="farmer", name="production_notes", field=models.TextField(blank=True, verbose_name="Production and inputs used")),
        migrations.AddField(model_name="farmer", name="group_name", field=models.CharField(blank=True, max_length=150, verbose_name="Farmer group")),
        migrations.AddField(model_name="farmer", name="pdm_beneficiary", field=models.BooleanField(default=False, verbose_name="PDM beneficiary")),
        migrations.AddField(model_name="farmer", name="support_received", field=models.TextField(blank=True, verbose_name="Support received")),
        migrations.AddField(model_name="farmer", name="trainings", field=models.TextField(blank=True, verbose_name="Trainings attended")),
        migrations.AddField(model_name="farmer", name="latitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="farmer", name="longitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="farmer", name="client_id", field=models.CharField(blank=True, editable=False, max_length=64, null=True, unique=True)),
    ]
