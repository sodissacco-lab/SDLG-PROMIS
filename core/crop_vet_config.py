from . import crop_vet_models as c
from . import reg_models as m
from .reg_config import CONFIGS, SHARED_PLACE, Register

PLACE = SHARED_PLACE
FARMER_STATUS = [("active", "Active"), ("inactive", "Inactive")]
FARMER_SEARCH = ("name__icontains", "phone__icontains", "code__icontains")
FARMER_COLS = [
    ("ID", "code"), ("Name", "name"), ("Sex", "get_sex_display"), ("Phone", "phone"),
    ("Sub-county", "sub_county"), ("Parish", "parish.name"),
]

# ------------------------------------------------------------------ Crops

Register(
    "crop-farmers", m.Farmer, "Crop farmers", "crop farmer", "Crops",
    ["name", "sex", "phone", "household"] + PLACE + ["youth", "pwd", "keeps_livestock", "fish_farming", "status"],
    FARMER_COLS + [("Crops recorded", "crops.count"), ("Status", "get_status_display")],
    search=FARMER_SEARCH, base={"grows_crops": True}, preset={"grows_crops": True},
    exclude={"status": "merged"}, status_choices=FARMER_STATUS, dup=True,
    children=[
        {"title": "Crops grown", "key": "crops-grown", "fk": "farmer"},
        {"title": "Group memberships", "key": "group-members", "fk": "farmer"},
    ],
)

Register(
    "farmer-groups", c.FarmerGroup, "Farmer groups & cooperatives", "farmer group", None,
    ["name", "group_type", "chairperson", "phone", "members_count", "focus"] + PLACE + ["status"],
    [("Name", "name"), ("Type", "get_group_type_display"), ("Chairperson", "chairperson"),
     ("Members (declared)", "members_count"), ("Members (listed)", "members.count"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name"), ("Status", "get_status_display")],
    search=("name__icontains", "chairperson__icontains", "focus__icontains"),
    dup=True, sum=("members_count", "Members (declared)"),
    children=[{"title": "Members", "key": "group-members", "fk": "group"}],
)

Register(
    "group-members", c.GroupMember, "Group members", "group member", None,
    ["group", "farmer", "role"],
    [("Group", "group.name"), ("Farmer", "farmer.name"), ("Role", "role")],
    search=("group__name__icontains", "farmer__name__icontains"),
    sub_county="group__sub_county", status_field=None, kind="record",
)

Register(
    "crop-varieties", c.CropVariety, "Crop varieties", "crop variety", "Crops",
    ["crop", "name", "characteristics"],
    [("Crop", "crop"), ("Variety", "name"), ("Characteristics", "characteristics")],
    search=("crop__icontains", "name__icontains"), sub_county=None, kind="reference",
)

_crop_fields = ["farmer", "crop", "variety", "season", "acreage", "planting_date", "status"]
Register(
    "crops-grown", c.CropGrown, "Crops grown", "crop record", "Crops",
    _crop_fields,
    [("Farmer", "farmer.name"), ("Crop", "crop"), ("Variety", "variety.name"), ("Season", "season"),
     ("Acreage", "acreage"), ("Planted", "planting_date"), ("Status", "get_status_display")],
    search=("farmer__name__icontains", "crop__icontains"),
    sub_county="farmer__sub_county", kind="record",
    sum=("acreage", "Total acreage"),
    children=[
        {"title": "Planting records", "key": "planting-records", "fk": "crop_grown"},
        {"title": "Harvests", "key": "harvest-records", "fk": "crop_grown"},
        {"title": "PDM links", "key": "pdm-enterprise-linkage", "fk": "crop_grown"},
    ],
)
CONFIGS["crops-grown"].active_label = "Growing"

Register(
    "crop-acreage", c.CropGrown, "Acreage", "acreage record", "Crops",
    _crop_fields,
    [("Crop", "crop"), ("Season", "season"), ("Farmer", "farmer.name"),
     ("Acreage", "acreage"), ("Sub-county", "farmer.sub_county"), ("Status", "get_status_display")],
    search=("farmer__name__icontains", "crop__icontains"),
    sub_county="farmer__sub_county", kind="record",
    sum=("acreage", "Total acreage"),
)
CONFIGS["crop-acreage"].active_label = "Growing"

Register(
    "planting-records", c.PlantingRecord, "Planting records", "planting record", "Crops",
    ["crop_grown", "date", "seed_kg", "notes"],
    [("Date", "date"), ("Farmer", "crop_grown.farmer.name"), ("Crop", "crop_grown.crop"), ("Seed (kg)", "seed_kg")],
    search=("crop_grown__farmer__name__icontains", "crop_grown__crop__icontains"),
    sub_county="crop_grown__farmer__sub_county", status_field=None,
    kind="record", date_field="date", sum=("seed_kg", "Seed used (kg)"),
)

Register(
    "harvest-records", c.CropHarvest, "Harvest records", "harvest record", "Crops",
    ["crop_grown", "date", "quantity_kg"],
    [("Date", "date"), ("Farmer", "crop_grown.farmer.name"), ("Crop", "crop_grown.crop"), ("Quantity (kg)", "quantity_kg")],
    search=("crop_grown__farmer__name__icontains", "crop_grown__crop__icontains"),
    sub_county="crop_grown__farmer__sub_county", status_field=None,
    kind="record", date_field="date", sum=("quantity_kg", "Total harvest (kg)"),
)

Register(
    "crop-production-estimates", c.CropProductionEstimate, "Production estimates", "production estimate", "Crops",
    ["sub_county", "crop", "season", "estimated_tonnes", "basis"],
    [("Sub-county", "sub_county"), ("Crop", "crop"), ("Season", "season"),
     ("Estimated (tonnes)", "estimated_tonnes"), ("Basis", "basis")],
    search=("crop__icontains", "season__icontains"),
    status_field=None, kind="record", sum=("estimated_tonnes", "Estimated production (tonnes)"),
)

Register(
    "agricultural-inputs", c.AgriInput, "Agricultural inputs", "input record", "Crops",
    ["date", "input_type", "item", "quantity", "unit", "farmer", "group", "sub_county"],
    [("Date", "date"), ("Type", "get_input_type_display"), ("Item", "item"), ("Quantity", "quantity"),
     ("Unit", "unit"), ("Farmer", "farmer.name"), ("Group", "group.name"), ("Sub-county", "sub_county")],
    search=("item__icontains", "farmer__name__icontains", "group__name__icontains"),
    status_field=None, kind="record", date_field="date",
)

Register(
    "demonstration-farms", c.DemonstrationFarm, "Demonstration farms", "demonstration farm", "Crops",
    ["host", "crop", "technology", "established"] + PLACE + ["status"],
    [("Host farmer", "host.name"), ("Crop", "crop"), ("Technology", "technology"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name"), ("Status", "get_status_display")],
    search=("host__name__icontains", "crop__icontains", "technology__icontains"),
)

Register(
    "pest-disease-surveillance", c.PestDiseaseReport, "Pest & disease surveillance", "pest or disease report", "Crops",
    ["date", "crop", "pest_or_disease", "severity", "area_affected_acres", "sub_county", "parish", "action_taken"],
    [("Date", "date"), ("Crop", "crop"), ("Pest or disease", "pest_or_disease"),
     ("Severity", "get_severity_display"), ("Area (acres)", "area_affected_acres"), ("Sub-county", "sub_county")],
    search=("crop__icontains", "pest_or_disease__icontains"),
    status_field=None, kind="record", date_field="date",
    sum=("area_affected_acres", "Area affected (acres)"),
)

Register(
    "post-harvest-handling", c.PostHarvestRecord, "Post-harvest handling", "post-harvest record", "Crops",
    ["date", "farmer", "crop", "storage_method", "loss_kg", "sub_county", "notes"],
    [("Date", "date"), ("Farmer", "farmer.name"), ("Crop", "crop"), ("Storage", "storage_method"),
     ("Loss (kg)", "loss_kg"), ("Sub-county", "sub_county")],
    search=("crop__icontains", "farmer__name__icontains"),
    status_field=None, kind="record", date_field="date", sum=("loss_kg", "Post-harvest loss (kg)"),
)

Register(
    "market-prices", c.MarketPrice, "Market prices", "market price", "Crops",
    ["date", "market", "sub_county", "category", "commodity", "unit", "price_ugx"],
    [("Date", "date"), ("Market", "market"), ("Category", "get_category_display"), ("Commodity", "commodity"),
     ("Unit", "unit"), ("Price (UGX)", "price_ugx", "money"), ("Sub-county", "sub_county")],
    search=("market__icontains", "commodity__icontains"),
    status_field=None, kind="record", date_field="date",
)

Register(
    "agricultural-interventions", c.AgriIntervention, "Agricultural interventions", "intervention", "Crops",
    ["date", "description", "farmer", "group", "sub_county", "cost_ugx", "notes"],
    [("Date", "date"), ("Intervention", "description"), ("Farmer", "farmer.name"), ("Group", "group.name"),
     ("Sub-county", "sub_county"), ("Cost (UGX)", "cost_ugx", "money")],
    search=("description__icontains", "farmer__name__icontains", "group__name__icontains"),
    status_field=None, kind="record", date_field="date",
    sum=("cost_ugx", "Total cost (UGX)", "money"),
)

Register(
    "pdm-enterprise-linkage", c.PDMEnterpriseLink, "PDM enterprise linkage", "PDM link", "Crops",
    ["beneficiary", "crop_grown", "notes"],
    [("PDM beneficiary", "beneficiary.name"), ("Crop enterprise", "crop_grown"), ("Notes", "notes")],
    search=("beneficiary__name__icontains",),
    sub_county="beneficiary__sub_county", status_field=None, kind="record",
)

# ------------------------------------------------------------ Veterinary

Register(
    "livestock-farmers", m.Farmer, "Livestock farmers", "livestock farmer", "Veterinary",
    ["name", "sex", "phone", "household"] + PLACE + ["youth", "pwd", "grows_crops", "fish_farming", "status"],
    FARMER_COLS + [("Livestock counts", "livestock_counts.count"), ("Status", "get_status_display")],
    search=FARMER_SEARCH, base={"keeps_livestock": True}, preset={"keeps_livestock": True},
    exclude={"status": "merged"}, status_choices=FARMER_STATUS, dup=True,
    children=[
        {"title": "Livestock counted", "key": "livestock-inventory", "fk": "farmer"},
        {"title": "Health cases", "key": "animal-health-cases", "fk": "farmer"},
        {"title": "AI services", "key": "artificial-insemination", "fk": "farmer"},
    ],
)

_count_cols = [("Date", "date"), ("Farmer", "farmer.name"), ("Species", "get_species_display"),
               ("Number", "count"), ("Breed", "breed")]
Register(
    "livestock-inventory", c.LivestockCount, "Livestock inventory", "livestock count", "Veterinary",
    ["farmer", "species", "date", "count", "breed"], _count_cols,
    search=("farmer__name__icontains", "breed__icontains"),
    sub_county="farmer__sub_county", status_field=None, kind="record",
    date_field="date", sum=("count", "Animals counted"),
)
for _slug, _code, _label in [
    ("cattle", "cattle", "Cattle"), ("goats", "goats", "Goats"), ("sheep", "sheep", "Sheep"),
    ("pigs", "pigs", "Pigs"), ("poultry", "poultry", "Poultry"),
]:
    Register(
        _slug, c.LivestockCount, _label, _label.lower() + " count", "Veterinary",
        ["farmer", "date", "count", "breed"], _count_cols,
        search=("farmer__name__icontains", "breed__icontains"),
        base={"species": _code}, preset={"species": _code},
        sub_county="farmer__sub_county", status_field=None, kind="record",
        date_field="date", sum=("count", "%s counted" % _label),
    )

Register(
    "animal-health-cases", c.AnimalHealthCase, "Animal health cases", "health case", "Veterinary",
    ["date", "farmer", "species", "animals_affected", "signs", "diagnosis", "treatment"] + PLACE,
    [("Date", "date"), ("Farmer", "farmer.name"), ("Species", "get_species_display"),
     ("Affected", "animals_affected"), ("Diagnosis", "diagnosis"), ("Sub-county", "sub_county")],
    search=("diagnosis__icontains", "farmer__name__icontains"),
    status_field=None, kind="record", date_field="date", sum=("animals_affected", "Animals affected"),
)

Register(
    "vaccination-campaigns", c.VaccinationCampaign, "Vaccination campaigns", "vaccination record", "Veterinary",
    ["date", "disease", "species", "animals_eligible", "animals_vaccinated", "vaccine_batch"] + PLACE,
    [("Date", "date"), ("Disease", "disease"), ("Species", "get_species_display"),
     ("Eligible", "animals_eligible"), ("Vaccinated", "animals_vaccinated"), ("Coverage", "coverage"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name")],
    search=("disease__icontains", "vaccine_batch__icontains"),
    status_field=None, kind="record", date_field="date",
    sum=("animals_vaccinated", "Animals vaccinated"),
)

Register(
    "disease-surveillance", c.DiseaseReport, "Disease surveillance", "disease report", "Veterinary",
    ["date", "disease", "species", "status", "animals_affected", "animals_dead", "farmer"] + PLACE + ["notes"],
    [("Date", "date"), ("Disease", "disease"), ("Species", "get_species_display"),
     ("Status", "get_status_display"), ("Affected", "animals_affected"), ("Dead", "animals_dead"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name")],
    search=("disease__icontains", "farmer__name__icontains"),
    kind="record", date_field="date",
)
CONFIGS["disease-surveillance"].active_label = "Confirmed"
CONFIGS["disease-surveillance"].active_value = "confirmed"

Register(
    "outbreak-management", c.Outbreak, "Outbreaks (FMD and other priority diseases)", "outbreak", "Veterinary",
    ["disease", "start_date", "end_date", "status", "confirmed_cases", "animals_dead"] + PLACE + ["response_actions"],
    [("Disease", "disease"), ("Started", "start_date"), ("Status", "get_status_display"),
     ("Confirmed cases", "confirmed_cases"), ("Dead", "animals_dead"), ("Sub-county", "sub_county"),
     ("Parish", "parish.name")],
    search=("disease__icontains",), kind="record", date_field="start_date",
    future_ok=("end_date",),
)

Register(
    "treatment-records", c.TreatmentRecord, "Treatment records", "treatment record", "Veterinary",
    ["date", "farmer", "species", "drug", "animals_treated"] + PLACE + ["notes"],
    [("Date", "date"), ("Farmer", "farmer.name"), ("Species", "get_species_display"),
     ("Drug", "drug"), ("Treated", "animals_treated"), ("Sub-county", "sub_county")],
    search=("drug__icontains", "farmer__name__icontains"),
    status_field=None, kind="record", date_field="date", sum=("animals_treated", "Animals treated"),
)

Register(
    "artificial-insemination", c.AIService, "Artificial insemination", "AI service", "Veterinary",
    ["date", "farmer", "animal_tag", "semen_used"] + PLACE + ["notes"],
    [("Date", "date"), ("Farmer", "farmer.name"), ("Animal", "animal_tag"),
     ("Semen", "semen_used"), ("Sub-county", "sub_county")],
    search=("farmer__name__icontains", "animal_tag__icontains"),
    status_field=None, kind="record", date_field="date",
)

Register(
    "livestock-markets", c.LivestockMarket, "Livestock markets", "livestock market", "Veterinary",
    ["name", "market_day"] + PLACE + ["status"],
    [("Name", "name"), ("Market day", "market_day"), ("Sub-county", "sub_county"),
     ("Parish", "parish.name"), ("Status", "get_status_display")],
    search=("name__icontains",), dup=True,
)

Register(
    "slaughter-records", c.SlaughterRecord, "Slaughter information", "slaughter record", "Veterinary",
    ["date", "slaughter_place", "species", "number_slaughtered", "number_inspected"] + PLACE,
    [("Date", "date"), ("Place", "slaughter_place"), ("Species", "get_species_display"),
     ("Slaughtered", "number_slaughtered"), ("Inspected", "number_inspected"), ("Sub-county", "sub_county")],
    search=("slaughter_place__icontains",), status_field=None, kind="record",
    date_field="date", sum=("number_slaughtered", "Animals slaughtered"),
)

Register(
    "livestock-mortality", c.LivestockMortality, "Mortality", "mortality record", "Veterinary",
    ["date", "farmer", "species", "number_dead", "suspected_cause"] + PLACE,
    [("Date", "date"), ("Farmer", "farmer.name"), ("Species", "get_species_display"),
     ("Dead", "number_dead"), ("Suspected cause", "suspected_cause"), ("Sub-county", "sub_county")],
    search=("suspected_cause__icontains", "farmer__name__icontains"),
    status_field=None, kind="record", date_field="date", sum=("number_dead", "Animals dead"),
)

Register(
    "drug-vaccine-inventory", c.DrugVaccineStock, "Drug & vaccine inventory", "stock entry", "Veterinary",
    ["date", "item", "item_type", "transaction", "quantity", "batch_number", "expiry_date"],
    [("Date", "date"), ("Item", "item"), ("Type", "get_item_type_display"),
     ("Transaction", "get_transaction_display"), ("Quantity", "quantity"),
     ("Batch", "batch_number"), ("Expires", "expiry_date")],
    search=("item__icontains", "batch_number__icontains"),
    sub_county=None, status_field=None, kind="record", date_field="date",
    future_ok=("expiry_date",),
)