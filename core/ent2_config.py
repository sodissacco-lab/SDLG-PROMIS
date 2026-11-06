from . import ent2_models as e
from .reg_config import SHARED_PLACE, Register

PLACE = SHARED_PLACE

Register(
    "apiaries", e.Apiary, "Apiaries & hives", "apiary", "Entomology",
    ["name", "owner", "group", "hive_type", "hives", "colonised_hives", "started_date"] + PLACE + ["status"],
    [("Apiary", "name"), ("Owner", "owner.name"), ("Group", "group.name"),
     ("Hive type", "get_hive_type_display"), ("Hives", "hives"), ("With bees", "colonised_hives"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name"), ("Status", "get_status_display")],
    search=("name__icontains", "owner__name__icontains", "group__name__icontains"),
    sum=("hives", "Hives"),
)

Register(
    "bsf-units", e.BSFUnit, "Black soldier fly units", "black soldier fly unit", "Entomology",
    ["owner", "group", "unit_type", "waste_kg_per_week", "larvae_use", "started_date"] + PLACE + ["status"],
    [("Owner", "owner.name"), ("Group", "group.name"), ("Type", "get_unit_type_display"),
     ("Waste (kg/week)", "waste_kg_per_week"), ("Larvae used for", "larvae_use"),
     ("Sub-county", "sub_county"), ("Status", "get_status_display")],
    search=("owner__name__icontains", "group__name__icontains", "larvae_use__icontains"),
)

Register(
    "vermin-reports", e.VerminReport, "Vermin surveillance & control", "vermin report", "Entomology",
    ["date", "vermin", "where_found", "severity", "farmer", "control_action", "controlled"] + PLACE + ["notes"],
    [("Date", "date"), ("Vermin", "get_vermin_display"), ("Where", "get_where_found_display"),
     ("Severity", "get_severity_display"), ("Control done", "controlled"),
     ("Action", "control_action"), ("Sub-county", "sub_county")],
    search=("control_action__icontains", "farmer__name__icontains"),
    status_field=None, kind="record", date_field="date",
)

Register(
    "collaborations", e.Collaboration, "Collaboration", "collaboration record", "Entomology",
    ["date", "partner", "partner_type", "topic", "outcome", "sub_county"],
    [("Date", "date"), ("Partner", "partner"), ("Type", "get_partner_type_display"),
     ("Topic", "topic"), ("Sub-county", "sub_county")],
    search=("partner__icontains", "topic__icontains"),
    status_field=None, kind="record", date_field="date",
)