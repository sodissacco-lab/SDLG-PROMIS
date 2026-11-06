import sqlite3
from datetime import datetime
from itertools import chain
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Back up the SQLite database and a JSON export of all system data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            help="Folder to save the backup in (default: backups folder in the project).",
        )
        parser.add_argument(
            "--keep",
            type=int,
            default=14,
            help="How many recent backups to keep (default 14).",
        )

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        if "sqlite" not in db["ENGINE"]:
            raise CommandError("This command only backs up SQLite databases.")

        if options["to"]:
            folder = Path(options["to"])
        else:
            folder = Path(settings.BASE_DIR) / "backups"
        folder.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        db_copy = folder / ("db_%s.sqlite3" % stamp)
        source = sqlite3.connect(str(db["NAME"]))
        target = sqlite3.connect(str(db_copy))
        with target:
            source.backup(target)
        target.close()
        source.close()

        json_copy = folder / ("data_%s.json" % stamp)
        models = apps.get_app_config("core").get_models()
        objects = list(chain.from_iterable(m.objects.all() for m in models))
        with open(json_copy, "w", encoding="utf-8") as handle:
            serializers.serialize("json", objects, stream=handle, indent=1)

        keep = max(options["keep"], 1)
        for pattern in ("db_*.sqlite3", "data_*.json"):
            for old in sorted(folder.glob(pattern))[:-keep]:
                old.unlink()

        self.stdout.write(self.style.SUCCESS("Backup saved in %s" % folder))