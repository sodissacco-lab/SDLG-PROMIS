import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Parish, SubCounty, User
from core.reg_models import Boat, BoatOwner, Farmer, FishPond, LandingSite

# Where each landing site is: (sub-county, parish). Edit a line here if it is wrong.
SITES = {
    "Abango": ("Ocokican", "Abaango"),
    "Aboket": ("Kamuda", "Aboket"),
    "Lalle": ("Lalle", "Lalle"),
}
SITE_ALIASES = {
    "abaango": "Abango",
    "abango": "Abango",
    "aboket": "Aboket",
    "lalle": "Lalle",
}
SUBCOUNTY_ALIASES = {"katine": "Katine Town Council", "lale": "Lalle"}


class DryRun(Exception):
    pass


def clean(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def clean_farm_text(value):
    text = clean(value).replace("$", "&")
    return re.sub(r"^[.\s,]+", "", text)


def clean_phone(value):
    text = clean(value)
    if text.endswith(".0"):
        text = text[:-2]
    numbers = []
    for part in re.split(r"[/,;]", text):
        digits = re.sub(r"\D", "", part)
        if not digits:
            continue
        if len(digits) == 9 and digits[0] == "7":
            digits = "0" + digits
        numbers.append(digits)
    return " / ".join(numbers)[:40]


def to_int(value, default=0):
    digits = re.sub(r"\D", "", clean(value))
    return int(digits) if digits else default


class Command(BaseCommand):
    help = "Import the boat registry (Excel) and the fish farmer census list (Word)."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Your username in the system.")
        parser.add_argument("--boats", default="imports/boats.xlsx")
        parser.add_argument("--farmers", default="imports/farmers.docx")
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen, save nothing.")

    # ------------------------------------------------------------ helpers

    def count(self, label, n=1):
        self.counts[label] = self.counts.get(label, 0) + n

    def issue(self, text):
        self.issues.append(text)

    def site_for(self, raw):
        name = SITE_ALIASES.get(clean(raw).lower())
        if not name:
            self.issue("Unknown landing site name: %r" % clean(raw))
            return None
        if name not in self.sites:
            sub_name, parish_name = SITES[name]
            sub = SubCounty.objects.filter(name__iexact=sub_name).first()
            if sub is None:
                raise CommandError("Sub-county %r for landing site %s does not exist." % (sub_name, name))
            parish = Parish.objects.filter(sub_county=sub, name__iexact=parish_name).first()
            if parish is None:
                parish = Parish.objects.create(sub_county=sub, name=parish_name)
                self.count("parishes created")
            site = LandingSite.objects.filter(name__iexact=name).first()
            if site is None:
                site = LandingSite.objects.create(
                    name=name, sub_county=sub, parish=parish, gazetted=True, registered_by=self.user
                )
                self.count("landing sites created")
            self.sites[name] = site
        return self.sites[name]

    # --------------------------------------------------------------- main

    def handle(self, *args, **options):
        try:
            self.user = User.objects.get(username=options["user"])
        except User.DoesNotExist:
            raise CommandError("There is no user called %r." % options["user"])
        self.sites, self.counts, self.issues, self.city = {}, {}, [], []
        self.stdout.write("Landing sites will be placed like this (sub-county, parish):")
        for site, place in SITES.items():
            self.stdout.write("  %s -> %s, %s" % (site, place[0], place[1]))
        try:
            with transaction.atomic():
                boats, farmers = Path(options["boats"]), Path(options["farmers"])
                if boats.exists():
                    self.import_boats(boats)
                else:
                    self.issue("Boat file not found, skipped: %s" % boats)
                if farmers.exists():
                    self.import_farmers(farmers)
                else:
                    self.issue("Farmer file not found, skipped: %s" % farmers)
                if options["dry_run"]:
                    raise DryRun()
        except DryRun:
            self.stdout.write(self.style.WARNING("DRY RUN: nothing was saved."))
        self.report()

    # -------------------------------------------------------------- boats

    def import_boats(self, path):
        from openpyxl import load_workbook

        wb = load_workbook(str(path), data_only=True)
        ws = wb["Boat Registry"] if "Boat Registry" in wb.sheetnames else wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            self.issue("The boat registry sheet is empty.")
            return
        pos = {clean(h).upper(): i for i, h in enumerate(rows[0])}

        def get(row, name):
            i = pos.get(name)
            return row[i] if i is not None and i < len(row) else None

        owners, boats = {}, {}
        for line, row in enumerate(rows[1:], start=2):
            name = clean(get(row, "BOAT OWNER")).title()
            plate = clean(get(row, "PLATE NUMBER")).upper()
            if not name or not plate:
                continue
            site = self.site_for(get(row, "LANDING SITE"))
            if site is None:
                continue
            key = clean(get(row, "NIN")).upper() or "%s|%s" % (name.lower(), site.name)
            if plate in boats:
                if boats[plate]["owner_key"] == key:
                    self.count("repeated boat rows skipped")
                else:
                    self.issue(
                        "Plate %s is used by two owners: %s (kept) and %s (row %d, not imported)."
                        % (plate, boats[plate]["owner_name"], name, line)
                    )
                continue
            phone = clean_phone(get(row, "PHONE"))
            if phone and not re.fullmatch(r"0\d{9}( / 0\d{9})*", phone):
                self.issue("Row %d (%s): unusual phone number %s" % (line, name, phone))
            sex = clean(get(row, "SEX")).upper()[:1]
            owners.setdefault(
                key,
                {"name": name, "sex": sex if sex in ("M", "F") else "", "phone": phone, "site": site},
            )
            propulsion = clean(get(row, "PROPULSION"))
            gear = clean(get(row, "FISHING GEAR"))
            if gear.lower() == "gill nets":
                gear = "Gill net"
            vessel = clean(get(row, "VESSEL TYPE"))
            boats[plate] = {
                "owner_key": key,
                "owner_name": name,
                "site": site,
                "boat_type": "motorised" if propulsion.lower().startswith("motor") else "canoe",
                "vessel_type": "" if "#REF" in vessel else vessel,
                "propulsion": propulsion,
                "fishing_gear": gear,
                "main_species": clean(get(row, "FISH SPIECES")),
                "bariars": to_int(get(row, "BARIARS"), None),
            }

        owner_objs = {}
        for key, o in owners.items():
            obj = BoatOwner.objects.filter(name__iexact=o["name"], landing_site=o["site"]).first()
            if obj is None:
                obj = BoatOwner.objects.create(
                    name=o["name"], sex=o["sex"], phone=o["phone"], landing_site=o["site"],
                    sub_county=o["site"].sub_county, parish=o["site"].parish,
                    registered_by=self.user,
                )
                self.count("boat owners created")
            else:
                self.count("boat owners already in the system")
            owner_objs[key] = obj

        for plate, b in boats.items():
            if Boat.objects.filter(registration_number=plate).exists():
                self.count("boats already in the system (skipped)")
                continue
            Boat.objects.create(
                registration_number=plate, boat_type=b["boat_type"], engine_hp=0,
                owner=owner_objs[b["owner_key"]], landing_site=b["site"], status="active",
                vessel_type=b["vessel_type"], propulsion=b["propulsion"],
                fishing_gear=b["fishing_gear"], main_species=b["main_species"],
                bariars=b["bariars"], registered_by=self.user,
            )
            self.count("boats created")

    # ------------------------------------------------------------ farmers

    def import_farmers(self, path):
        from docx import Document

        document = Document(str(path))
        raw = []
        for table in document.tables:
            for row in table.rows:
                cells = [clean(c.text) for c in row.cells]
                if len(cells) >= 12 and re.fullmatch(r"\d+\.?", cells[0]):
                    raw.append(cells)
        if not raw:
            self.issue("No farmer rows were found in the Word file.")
            return

        groups = {}
        for cells in raw:
            sno, name, farm, county, subcounty, parish, village, total, yes, no, category, contact = cells[:12]
            name, farm = clean_farm_text(name), clean_farm_text(farm)
            parish, village = clean_farm_text(parish), clean_farm_text(village)
            if "city" in county.lower() or "city" in subcounty.lower():
                self.city.append("S/No %s: %s (%s, %s)" % (sno.rstrip("."), name, subcounty, parish))
                continue
            sub_name = SUBCOUNTY_ALIASES.get(clean(subcounty).lower(), clean(subcounty))
            sub = SubCounty.objects.filter(name__iexact=sub_name).first()
            if sub is None or not parish or not name:
                self.issue("S/No %s (%s): sub-county %r or parish not usable, not imported." % (sno.rstrip("."), name, subcounty))
                continue
            parish_obj = Parish.objects.filter(sub_county=sub, name__iexact=parish).first()
            if parish_obj is None:
                parish_obj = Parish.objects.create(sub_county=sub, name=parish)
                self.count("parishes created")
            total_n, stocked_n, unstocked_n = to_int(total), to_int(yes), to_int(no)
            if stocked_n + unstocked_n != total_n:
                self.issue(
                    "S/No %s (%s): %d ponds in total but %d stocked and %d not stocked."
                    % (sno.rstrip("."), farm, total_n, stocked_n, unstocked_n)
                )
            stocked_n = min(stocked_n, total_n)
            key = (name.lower(), sub.id, parish_obj.id)
            g = groups.setdefault(
                key,
                {"name": name, "sub": sub, "parish": parish_obj, "village": village,
                 "farms": [], "phones": [], "category": ""},
            )
            g["farms"].append({"name": farm, "village": village, "total": total_n, "stocked": stocked_n})
            phone = clean_phone(contact)
            if phone and phone not in g["phones"]:
                g["phones"].append(phone)
            cat = clean(category).lower().replace(" ", "")
            if not g["category"]:
                g["category"] = "non_household" if cat.startswith("non") else ("household" if "household" in cat else "")

        for g in groups.values():
            if len(g["phones"]) > 1:
                self.issue("%s has different phone numbers in the list: %s (the first was kept)." % (g["name"], ", ".join(g["phones"])))
            farm_names = "; ".join(dict.fromkeys(f["name"] for f in g["farms"] if f["name"]))[:250]
            farmer = Farmer.objects.filter(name__iexact=g["name"], parish=g["parish"]).exclude(status="merged").first()
            if farmer is None:
                farmer = Farmer.objects.create(
                    name=g["name"], sex="", phone=(g["phones"][0] if g["phones"] else "")[:40],
                    sub_county=g["sub"], parish=g["parish"], village=g["village"],
                    fish_farming=True, farm_name=farm_names, farm_category=g["category"],
                    status="active", registered_by=self.user,
                )
                self.count("fish farmers created")
            else:
                changed = False
                if not farmer.fish_farming:
                    farmer.fish_farming, changed = True, True
                if not farmer.farm_name and farm_names:
                    farmer.farm_name, changed = farm_names, True
                if changed:
                    farmer.save()
                self.count("farmers already in the system (updated if needed)")
            for farm in g["farms"]:
                for n in range(1, farm["total"] + 1):
                    pond_name = ("%s - Pond %d" % (farm["name"] or "Farm", n))[:100]
                    if FishPond.objects.filter(owner=farmer, pond_name=pond_name).exists():
                        self.count("ponds already in the system (skipped)")
                        continue
                    FishPond.objects.create(
                        owner=farmer, pond_name=pond_name, pond_type="earthen", size_sqm=0,
                        sub_county=g["sub"], parish=g["parish"], village=farm["village"],
                        status="active" if n <= farm["stocked"] else "inactive",
                        registered_by=self.user,
                    )
                    self.count("ponds created")

    # ------------------------------------------------------------- report

    def report(self):
        self.stdout.write("")
        for label, n in self.counts.items():
            self.stdout.write("%6d  %s" % (n, label))
        if self.city:
            self.stdout.write("%6d  Soroti City farmers NOT imported" % len(self.city))
        self.stdout.write("%6d  things to check (see the report file)" % len(self.issues))
        path = Path("imports") / "import_report.txt"
        path.parent.mkdir(exist_ok=True)
        lines = ["IMPORT REPORT", "", "Things to check:"] + ["- " + i for i in self.issues]
        lines += ["", "Soroti City farmers not imported:"] + ["- " + c for c in self.city]
        path.write_text("\n".join(lines), encoding="utf-8")
        self.stdout.write("Report written to %s" % path)