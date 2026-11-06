from django.urls import reverse

KIND_LABELS = {
    "register": "Register: something that exists. Counted as registered, new this period and active.",
    "record": "Records over time: observations and transactions. Counted by date, with quantities.",
    "authorisation": "Authorisation: a time-bound permission. Counted as issued and currently valid.",
    "activity": "Activity: recorded in the Daily Activity Register and counted once approved.",
    "reference": "Reference list: names and categories used by other records.",
    "platform": "System page.",
}

CATALOG = {}
LIVE = {"pdm-register": "pdm_list"}


def _add(slug, label, kind, what, counted=""):
    CATALOG[slug] = {
        "slug": slug,
        "label": label,
        "kind": kind,
        "what": what,
        "counted": counted,
    }


# Shared services
_add("farmer-registry", "Farmer & Household Registry", "register", "One profile per household and farmer, with crop, livestock and fish enterprises, groups, PDM record, training attendance, extension visits and intervention history. Shared by every sector so nobody is registered twice.", "Households and farmers: registered, new this period, active.")
_add("farmer-groups", "Farmer Groups & Cooperatives", "register", "Groups, SACCOs and cooperatives with their members, leaders and enterprises.", "Groups registered, new and active. Members are counted from the farmer registry.")
_add("pdm-register", "PDM Management", "register", "PDM groups, beneficiaries and monitoring visits.", "Beneficiaries registered; amounts received; monitoring visits.")
_add("inputs-equipment", "Inputs & Equipment", "register", "Inputs distributed and equipment issued, with recipients and dates.", "Items issued and recipients reached.")
_add("partners-projects", "Partners & Projects", "register", "Partners, NGOs and projects, where they work and what they support.", "Partners and projects by sub-county and sector.")
_add("document-centre", "Document Centre", "platform", "Work plans, guidelines, circulars, minutes and attendance sheets in one searchable place.")

# Fisheries: capture fisheries
_add("landing-sites", "Landing sites", "register", "Gazetted and ungazetted landing sites with location, facilities, boats and fishers based there.", "Landing sites registered and active. Each inspection links to its site.")
_add("boats", "Boats", "register", "Registered boats with registration number, type, engine and landing site. One boat is one asset.", "Boats registered and active.")
_add("boat-owners", "Boat owners", "register", "Owners of boats, linked to their boats and licences.", "Owners registered.")
_add("fishers", "Fishers", "register", "Registered fishers with landing site, role and gear used.", "Fishers registered and active.")
_add("fishing-gears", "Fishing gears", "reference", "Gear types, and the gear in use by boat or fisher.", "Gear by type.")
_add("daily-catches", "Daily catches", "record", "Catch recorded on a date at a landing site: species, quantity and number of boats.", "Catch quantity and number of records in the period.")
_add("fish-species", "Fish species", "reference", "Fish species names and categories used in catch, stocking and harvest records.")
_add("fish-mongers", "Fish mongers", "register", "Fish traders registered at landing sites and markets.", "Fish mongers registered.")
_add("fish-buyers", "Fish buyers", "register", "Buyers and processors, with the markets they serve.", "Buyers registered.")
_add("fishing-licences", "Licensing", "authorisation", "Boat and fishing licences: issue date, expiry date, fee and status.", "Licences issued and licences currently valid.")
_add("enforcement-operations", "Enforcement", "activity", "Patrols and enforcement operations. Record them in the Daily Activity Register.", "Approved operations.")
_add("illegal-fishing-incidents", "Illegal fishing incidents", "record", "Incidents with location, offence, gear seized and action taken.", "Incidents reported and actions taken.")
_add("landing-site-revenue", "Landing-site revenue", "record", "Fees collected and receipted at landing sites.", "Amount collected and receipts issued.")

# Fisheries: aquaculture
_add("fish-farmers", "Fish farmers", "register", "Fish farmers, linked to the shared Farmer & Household Registry.", "Fish farmers registered and active.")
_add("fish-ponds", "Fish ponds", "register", "Ponds with owner, size, species and status.", "Ponds registered and active; total pond area.")
_add("cage-farms", "Cage farms", "register", "Cage farms with owner, number of cages and species.", "Cage farms registered and active.")
_add("pond-measurements", "Pond measurements", "record", "Pond dimensions and water depth over time.")
_add("stocking-records", "Species and stocking", "record", "Fingerlings stocked per pond: species, number and date.", "Fingerlings stocked.")
_add("feeding-records", "Feeding records", "record", "Feed type and quantity given to a pond or cage.")
_add("water-quality", "Water quality", "record", "Water quality readings per pond.")
_add("fish-mortality", "Mortality records", "record", "Fish deaths per pond with the suspected cause.", "Mortalities recorded.")
_add("fish-harvest", "Harvest records", "record", "Harvest per pond: species, quantity and date.", "Harvest quantity.")
_add("production-estimates", "Production estimates", "record", "Estimated production per farm or sub-county.")
_add("fisheries-equipment", "Fisheries equipment & inputs", "register", "Fisheries equipment and inputs issued.")

# Crops
_add("crops-grown", "Crops grown", "record", "Crops grown by each farmer or group per season.", "Farmers and acreage by crop.")
_add("crop-acreage", "Acreage", "record", "Acreage planted per crop, farmer and season.", "Total acreage.")
_add("crop-varieties", "Crop varieties", "reference", "Crop varieties and their characteristics.")
_add("planting-records", "Planting records", "record", "Planting dates and quantities.")
_add("harvest-records", "Harvest records", "record", "Harvest quantities and dates.")
_add("crop-production-estimates", "Production estimates", "record", "Estimated production per crop and area.")
_add("agricultural-inputs", "Agricultural inputs", "record", "Seed, fertiliser and chemicals distributed.", "Quantities distributed and recipients.")
_add("demonstration-farms", "Demonstration farms", "register", "Demonstration plots with host farmer, crop and technology shown.", "Demonstration farms registered and active.")
_add("pest-disease-surveillance", "Pest & disease surveillance", "record", "Pest and disease reports per location and crop.", "Reports and severity by area.")
_add("post-harvest-handling", "Post-harvest handling", "record", "Storage and post-harvest practices and losses.")
_add("market-prices", "Market prices", "record", "Prices by commodity, market and date.", "Average price per commodity, market and week.")
_add("agricultural-interventions", "Agricultural interventions", "record", "Interventions delivered to farmers or groups.")
_add("pdm-enterprise-linkage", "PDM enterprise linkage", "record", "Links between enterprises and PDM beneficiaries.")

# Veterinary
for _slug, _label in [("cattle", "Cattle"), ("goats", "Goats"), ("sheep", "Sheep"), ("pigs", "Pigs"), ("poultry", "Poultry")]:
    _add(_slug, _label, "record", "%s counted per household or farm, with breed and age groups." % _label, "Animals by species and location.")
_add("animal-health-cases", "Animal health cases", "record", "Sick animals seen: species, signs, diagnosis and treatment.", "Cases by disease and location.")
_add("vaccination-campaigns", "Vaccination campaigns", "record", "Vaccination rounds: disease, animals eligible, animals vaccinated and vaccine batch.", "Animals vaccinated and coverage.")
_add("disease-surveillance", "Disease surveillance", "record", "Suspected disease reports. A suspected case stays separate from a confirmed one.", "Suspected and confirmed cases, kept apart.")
_add("outbreak-management", "Outbreaks (FMD and other priority diseases)", "record", "Confirmed outbreaks with locations, response and follow-up.", "Outbreaks and affected locations.")
_add("treatment-records", "Treatment records", "record", "Treatments given: animal, drug and date.")
_add("artificial-insemination", "Artificial insemination", "record", "AI services: farmer, animal, semen used and date.", "Services provided.")
_add("livestock-markets", "Livestock markets", "register", "Livestock markets and market-day numbers.", "Markets registered; animals traded.")
_add("slaughter-records", "Slaughter information", "record", "Slaughter and meat inspection records.")
_add("livestock-mortality", "Mortality", "record", "Animal deaths with the suspected cause.")
_add("drug-vaccine-inventory", "Drug & vaccine inventory", "record", "Stock received, used, expired and remaining.")

# Entomology
_add("vector-surveillance", "Tsetse / vector surveillance", "record", "Surveillance rounds for tsetse and other vectors.")
_add("trap-register", "Trap register & locations", "register", "Each trap with a unique number, installation date, coordinates, target vector and status.", "Traps installed, operational and inspected.")
_add("trap-inspections", "Trap inspections", "record", "One inspection per trap per date.", "Inspections done.")
_add("vector-counts", "Vector counts", "record", "Counts captured at each inspection, so trends can be compared.", "Vectors captured per trap, place and period.")
_add("vector-control-activities", "Vector control activities", "activity", "Control work such as spraying or target deployment. Record it in the Daily Activity Register.", "Approved activities.")
_add("pest-surveillance", "Pest surveillance", "record", "Pest reports by place and date.")
_add("vector-incidents", "Disease / vector incidents", "record", "Incidents linked to vectors, with location and response.")
_add("entomology-equipment", "Control equipment & inputs", "register", "Equipment and inputs used for control.")

# Commercial
_add("enterprises", "Enterprises", "register", "Enterprises and their profiles, with production, sales and expenditure updated over time.", "Enterprises registered, new and active.")
_add("business-activities", "Business activities", "activity", "Business visits and follow-up. Record them in the Daily Activity Register.", "Approved activities.")
_add("markets", "Markets", "register", "Markets, their days and facilities.", "Markets registered.")
_add("value-addition", "Value addition", "register", "Value-addition ventures and what they process.")
_add("msmes", "MSMEs", "register", "Micro, small and medium enterprises.", "MSMEs registered and active.")
_add("enterprise-training", "Training", "activity", "Business training. Record it in the Daily Activity Register.", "Approved trainings and people reached.")
_add("business-support", "Business support", "activity", "Business support visits. Record them in the Daily Activity Register.")
_add("loans-interventions", "Loans & interventions", "record", "Loans and support given to enterprises, with status.", "Amounts given and repaid.")
_add("enterprise-performance", "Enterprise performance", "record", "Periodic updates of production, sales and expenditure for each enterprise.", "Performance by enterprise over time.")
_add("market-linkages", "Market linkages", "record", "Links between producers and buyers or markets.")

# System pages
_add("work-plans", "Work Plans & Targets", "platform", "Annual work plans and targets compared with approved achievements. For now, targets are managed under Administration, Targets.")
_add("gis-maps", "GIS & Maps", "platform", "Maps of activities, landing sites, farms and incidents from GPS coordinates.")
_add("notifications", "Notifications", "platform", "Alerts: pending approvals, returned records, licence expiry, disease reports and data quality issues.")
_add("audit-trail", "Audit Trail", "platform", "Who created or changed what, and when.")
_add("system-settings", "System Settings", "platform", "Indicator definitions, financial-year settings and lists.")
_add("backup-sync", "Backup & Synchronization", "platform", "Backups of the database and photos. For now, run backup.bat. Synchronisation for offline work comes with the mobile app.")

SHARED = [
    "farmer-registry",
    "farmer-groups",
    "pdm-register",
    "inputs-equipment",
    "partners-projects",
    "document-centre",
]

MENUS = {
    "Crops": [
        "farmer-registry",
        "farmer-groups",
        ("Crop production", ["crops-grown", "crop-acreage", "crop-varieties", "planting-records", "harvest-records", "crop-production-estimates"]),
        "agricultural-inputs",
        "demonstration-farms",
        "pest-disease-surveillance",
        "post-harvest-handling",
        "market-prices",
        "agricultural-interventions",
        "pdm-enterprise-linkage",
    ],
    "Fisheries": [
        ("Capture fisheries", ["landing-sites", "boats", "boat-owners", "fishers", "fishing-gears", "daily-catches", "fish-species", "fish-mongers", "fish-buyers", "fishing-licences", "enforcement-operations", "illegal-fishing-incidents", "landing-site-revenue"]),
        ("Aquaculture", ["fish-farmers", "fish-ponds", "cage-farms", "pond-measurements", "stocking-records", "feeding-records", "water-quality", "fish-mortality", "fish-harvest", "production-estimates"]),
        "fisheries-equipment",
    ],
    "Veterinary": [
        "farmer-registry",
        ("Livestock inventory", ["cattle", "goats", "sheep", "pigs", "poultry"]),
        "animal-health-cases",
        "vaccination-campaigns",
        "disease-surveillance",
        "outbreak-management",
        "treatment-records",
        "artificial-insemination",
        "livestock-markets",
        "slaughter-records",
        "livestock-mortality",
        "drug-vaccine-inventory",
    ],
    "Entomology": [
        "vector-surveillance",
        "trap-register",
        "trap-inspections",
        "vector-counts",
        "vector-control-activities",
        "pest-surveillance",
        "vector-incidents",
        "entomology-equipment",
    ],
    "Commercial": [
        "enterprises",
        "farmer-groups",
        "business-activities",
        "markets",
        "market-prices",
        "value-addition",
        "msmes",
        "enterprise-training",
        "business-support",
        "loans-interventions",
        "enterprise-performance",
        "market-linkages",
    ],
}


def register_href(slug, sector_pk=None):
    if slug in LIVE:
        return reverse(LIVE[slug])
    href = reverse("register", kwargs={"slug": slug})
    if sector_pk:
        href += "?s=%s" % sector_pk
    return href


def _leaf(slug, sector_pk, current_slug):
    return {
        "label": CATALOG[slug]["label"],
        "href": register_href(slug, sector_pk),
        "active": slug == current_slug,
        "children": None,
    }


def build_menu(sector_name, sector_pk, current_slug=None):
    entries = []
    for item in MENUS.get(sector_name, []):
        if isinstance(item, tuple):
            label, slugs = item
            children = [_leaf(s, sector_pk, current_slug) for s in slugs if s in CATALOG]
            entries.append(
                {
                    "label": label,
                    "children": children,
                    "open": any(c["active"] for c in children),
                }
            )
        elif item in CATALOG:
            entries.append(_leaf(item, sector_pk, current_slug))
    return entries


def shared_menu(current_slug=None):
    return [_leaf(s, None, current_slug) for s in SHARED]


def siblings(slug):
    for items in MENUS.values():
        for item in items:
            if isinstance(item, tuple) and slug in item[1]:
                return [s for s in item[1] if s != slug and s in CATALOG]
    return []
from .reg_config import CONFIGS  # noqa: E402

for _key in CONFIGS:
    LIVE[_key] = "r_" + _key.replace("-", "_")

_add(
    "households",
    "Households",
    "register",
    "Household profiles: head, members and location, linked to the farmers living in them.",
    "Households registered, new and active.",
)
SHARED.insert(1, "households")
_add("crop-farmers", "Crop farmers", "register", "Farmers who grow crops. A view of the shared Farmer & Household Registry.", "Crop farmers registered, new and active.")
_add("livestock-farmers", "Livestock farmers", "register", "Farmers who keep livestock. A view of the shared Farmer & Household Registry.", "Livestock farmers registered, new and active.")
MENUS["Crops"][0] = "crop-farmers"
MENUS["Veterinary"][0] = "livestock-farmers"
_add("apiaries", "Apiaries & hives", "register", "Apiaries with owner or group, hive type, number of hives and how many have bees.", "Apiaries registered and active; total hives.")
_add("bsf-units", "Black soldier fly units", "register", "Black soldier fly units with owner, type, organic waste processed and what the larvae are used for.", "Units registered and active.")
_add("vermin-reports", "Vermin surveillance & control", "record", "Vermin reports with location, severity and the control action taken.", "Reports by vermin and area; how many were controlled.")
_add("collaborations", "Collaboration", "record", "Work done with partners and other departments: who, on what, and the result.", "Collaborations recorded by partner and period.")
MENUS["Entomology"] += [
    ("Bee keeping", ["apiaries"]),
    ("Black soldier fly", ["bsf-units"]),
    "vermin-reports",
    "collaborations",
]