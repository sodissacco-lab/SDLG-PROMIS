from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_activityphoto_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="LoginThrottle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=120, unique=True)),
                ("fails", models.PositiveIntegerField(default=0)),
                ("window_start", models.DateTimeField()),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
