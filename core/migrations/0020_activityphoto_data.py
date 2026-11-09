from django.db import migrations, models


def fill_from_files(apps, schema_editor):
    """Copy pictures that still exist on disk into the database."""
    Photo = apps.get_model("core", "ActivityPhoto")
    for p in Photo.objects.filter(data__isnull=True).iterator():
        try:
            with p.image.open("rb") as fh:
                p.data = fh.read()
            p.save(update_fields=["data"])
        except Exception:
            continue


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_farmer_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="activityphoto",
            name="data",
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(fill_from_files, migrations.RunPython.noop),
    ]
