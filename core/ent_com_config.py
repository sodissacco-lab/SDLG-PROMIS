from . import ent_com_models as x
from .reg_config import CONFIGS, SHARED_PLACE, Register

PLACE = SHARED_PLACE

# ------------------------------------------------------------ Entomology

Register(
    "trap-register", x.Trap, "Trap register & locations", "trap", "Entomology",
    ["trap_name", "trap_type", "target_vector", "installed_date"] + PLACE + ["latitude", "longitude", "status"],
    [("Trap no.", "code"), ("Name", "trap_name"), ("Type", "get_trap_type_display"),
     ("Target vector", "target_vector"), ("Sub-county", "sub_county"), ("Parish", "parish.name"),
     ("Installed", "installed_date"), ("Status", "get_status_display")],
    search=("code__icontains", "trap_name__icontains", "village__icontains"),
    children=[{"title": "Inspections", "key": "trap-inspections", "fk": "trap"}],
)
CONFIGS["trap-register"].active_label = "Operational"

Register(
    "trap-inspections", x.TrapInspection, "Trap inspections", "trap inspection", "Entomology",
    ["trap", "date", "condition", "notes"],
    [("Date", "date"), ("Trap", "trap.code"), ("Condition", "get_condition_display"), ("Notes", "notes")],
    search=("trap__code__icontains", "trap__trap_name__icontains"),
    sub_county="trap__sub_county", status_field=None, kind="record", date_field="date",
    children=[{"title": "Vector counts", "key": "vector-counts", "fk": "inspection"}],
)

Register(
    "vector-counts", x.VectorCount, "Vector counts", "vector count", "Entomology",
    ["inspection", "species", "number_caught", "notes"],
    [("Date", "inspection.date"), ("Trap", "inspection.trap.code"), ("Species", "species"),
     ("Caught", "number_caught")],
    search=("inspection__trap__code__icontains", "species__icontains"),
    sub_county="inspection__trap__sub_county", status_field=None, kind="record",
    sum=("number_caught", "Vectors caught"),
)

Register(
    "vector-surveillance", x.SurveillanceRound, "Tsetse / vector surveillance", "surveillance round", "Entomology",
    ["date", "vector", "method", "traps_set", "traps_recovered"] + PLACE + ["notes"],
    [("Date", "date"), ("Vector", "vector"), ("Method", "method"), ("Traps set", "traps_set"),
     ("Recovered", "traps_recovered"), ("Sub-county", "sub_county"), ("Parish", "parish.name")],
    search=("vector__icontains", "method__icontains"),
    status_field=None, kind="record", date_field="date", sum=("traps_set", "Traps set"),
)

Register(
    "vector-incidents", x.VectorIncident, "Disease / vector incidents", "incident", "Entomology",
    ["date", "vector", "incident_type", "cases", "status"] + PLACE + ["response_actions"],
    [("Date", "date"), ("Vector", "vector"), ("Type", "get_incident_type_display"),
     ("Cases", "cases"), ("Sub-county", "sub_county"), ("Status", "get_status_display")],
    search=("vector__icontains",), kind="record", date_field="date",
)
CONFIGS["vector-incidents"].active_label = "Open"

_equip_fields = ["item", "category", "quantity", "date_received", "holder", "sub_county", "status"]
_equip_cols = [("Item", "item"), ("Category", "category"), ("Quantity", "quantity"),
               ("Received", "date_received"), ("Held by", "holder"), ("Sub-county", "sub_county"),
               ("Status", "get_status_display")]
for _key, _label, _sector in [
    ("entomology-equipment", "Control equipment & inputs", "Entomology"),
    ("fisheries-equipment", "Fisheries equipment & inputs", "Fisheries"),
]:
    Register(
        _key, x.Equipment, _label, "equipment item", _sector,
        _equip_fields, _equip_cols,
        search=("item__icontains", "category__icontains", "holder__icontains"),
        base={"sector": _sector}, preset={"sector": _sector},
        kind="register", sum=("quantity", "Items held"),
    )
    CONFIGS[_key].active_label = "In use"

Register(
    "inputs-equipment", x.Equipment, "Inputs & Equipment", "equipment item", None,
    ["sector"] + _equip_fields,
    [("Sector", "sector")] + _equip_cols,
    search=("item__icontains", "category__icontains", "holder__icontains"),
    kind="register", sum=("quantity", "Items held"),
)
CONFIGS["inputs-equipment"].active_label = "In use"

# ------------------------------------------------------------ Commercial

Register(
    "enterprises", x.Enterprise, "Enterprises", "enterprise", "Commercial",
    ["name", "enterprise_type", "description", "owner", "owner_name", "group", "pdm_beneficiary",
     "started_date", "capital_ugx", "employees"] + PLACE + ["status"],
    [("ID", "code"), ("Name", "name"), ("Type", "get_enterprise_type_display"), ("Owner", "owner.name"),
     ("Group", "group.name"), ("Sub-county", "sub_county"), ("Capital (UGX)", "capital_ugx", "money"),
     ("Employees", "employees"), ("Status", "get_status_display")],
    search=("name__icontains", "code__icontains", "owner__name__icontains", "owner_name__icontains"),
    dup=True, sum=("capital_ugx", "Capital invested (UGX)", "money"),
    children=[
        {"title": "Performance records", "key": "enterprise-performance", "fk": "enterprise"},
        {"title": "Loans and support", "key": "loans-interventions", "fk": "enterprise"},
        {"title": "Market linkages", "key": "market-linkages", "fk": "enterprise"},
    ],
)

Register(
    "markets", x.Market, "Markets", "market", "Commercial",
    ["name", "market_type", "market_day"] + PLACE + ["status"],
    [("Name", "name"), ("Type", "get_market_type_display"), ("Market day", "market_day"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name"), ("Status", "get_status_display")],
    search=("name__icontains",), dup=True,
)

Register(
    "value-addition", x.ValueAdditionVenture, "Value addition", "value-addition venture", "Commercial",
    ["name", "product", "raw_material", "capacity", "owner", "group"] + PLACE + ["status"],
    [("Name", "name"), ("Product", "product"), ("Raw material", "raw_material"),
     ("Capacity", "capacity"), ("Sub-county", "sub_county"), ("Status", "get_status_display")],
    search=("name__icontains", "product__icontains"), dup=True,
)

Register(
    "msmes", x.MSME, "MSMEs", "MSME", "Commercial",
    ["name", "owner_name", "owner", "business_type", "registered", "employees"] + PLACE + ["status"],
    [("Business", "name"), ("Owner", "owner_name"), ("Type", "business_type"),
     ("Registered", "registered"), ("Employees", "employees"), ("Sub-county", "sub_county"),
     ("Status", "get_status_display")],
    search=("name__icontains", "owner_name__icontains", "business_type__icontains"),
    dup=True, sum=("employees", "Employees"),
)

Register(
    "loans-interventions", x.LoanIntervention, "Loans & interventions", "loan or intervention", "Commercial",
    ["date", "description", "source", "enterprise", "farmer", "group", "amount_ugx", "repaid_ugx", "status"],
    [("Date", "date"), ("Description", "description"), ("Enterprise", "enterprise.name"),
     ("Farmer", "farmer.name"), ("Group", "group.name"), ("Amount (UGX)", "amount_ugx", "money"),
     ("Repaid (UGX)", "repaid_ugx", "money"), ("Status", "get_status_display")],
    search=("description__icontains", "enterprise__name__icontains", "farmer__name__icontains",
            "group__name__icontains", "source__icontains"),
    sub_county=None, kind="record", date_field="date",
    sum=("amount_ugx", "Amounts given (UGX)", "money"),
)
CONFIGS["loans-interventions"].active_label = "Ongoing"

Register(
    "enterprise-performance", x.EnterprisePerformance, "Enterprise performance", "performance record", "Commercial",
    ["enterprise", "date", "period_label", "revenue_ugx", "expenditure_ugx", "production_note", "employees"],
    [("Date", "date"), ("Enterprise", "enterprise.name"), ("Period", "period_label"),
     ("Revenue (UGX)", "revenue_ugx", "money"), ("Expenditure (UGX)", "expenditure_ugx", "money"),
     ("Profit (UGX)", "profit", "money")],
    search=("enterprise__name__icontains", "period_label__icontains"),
    sub_county="enterprise__sub_county", status_field=None, kind="record", date_field="date",
    sum=("revenue_ugx", "Revenue reported (UGX)", "money"),
)

Register(
    "market-linkages", x.MarketLinkage, "Market linkages", "market linkage", "Commercial",
    ["date", "description", "enterprise", "group", "buyer", "commodity", "quantity", "notes"],
    [("Date", "date"), ("Description", "description"), ("Enterprise", "enterprise.name"),
     ("Group", "group.name"), ("Buyer or market", "buyer"), ("Commodity", "commodity"),
     ("Quantity", "quantity")],
    search=("description__icontains", "buyer__icontains", "commodity__icontains"),
    sub_county=None, status_field=None, kind="record", date_field="date",
)

# Pest surveillance is the same report table the Crops sector uses.
from . import crop_vet_models as _cv  # noqa: E402

Register(
    "pest-surveillance", _cv.PestDiseaseReport, "Pest surveillance", "pest report", "Entomology",
    ["date", "crop", "pest_or_disease", "severity", "area_affected_acres", "sub_county", "parish", "action_taken"],
    [("Date", "date"), ("Crop or host", "crop"), ("Pest", "pest_or_disease"),
     ("Severity", "get_severity_display"), ("Area (acres)", "area_affected_acres"),
     ("Sub-county", "sub_county")],
    search=("crop__icontains", "pest_or_disease__icontains"),
    status_field=None, kind="record", date_field="date",
    sum=("area_affected_acres", "Area affected (acres)"),
)

# Market prices are used by Crops and Commercial: open to both.
CONFIGS["market-prices"].sector = None