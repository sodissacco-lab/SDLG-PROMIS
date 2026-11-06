from . import reg_extra_models as x
from .reg_config import CONFIGS, Register

Register(
    "pond-measurements", x.PondMeasurement, "Pond measurements", "pond measurement", "Fisheries",
    ["pond", "date", "length_m", "width_m", "depth_m"],
    [("Date", "date"), ("Pond", "pond"), ("Length (m)", "length_m"), ("Width (m)", "width_m"),
     ("Depth (m)", "depth_m"), ("Area (sqm)", "area_sqm")],
    search=("pond__owner__name__icontains",),
    sub_county="pond__sub_county", status_field=None,
    kind="record", date_field="date",
)

Register(
    "feeding-records", x.FeedingRecord, "Feeding records", "feeding record", "Fisheries",
    ["pond", "date", "feed_type", "quantity_kg"],
    [("Date", "date"), ("Pond", "pond"), ("Feed type", "feed_type"), ("Quantity (kg)", "quantity_kg")],
    search=("pond__owner__name__icontains", "feed_type__icontains"),
    sub_county="pond__sub_county", status_field=None,
    kind="record", date_field="date", sum=("quantity_kg", "Feed given (kg)"),
)

Register(
    "water-quality", x.WaterQualityRecord, "Water quality", "water quality reading", "Fisheries",
    ["pond", "date", "temperature_c", "ph", "dissolved_oxygen", "notes"],
    [("Date", "date"), ("Pond", "pond"), ("Temp (C)", "temperature_c"), ("pH", "ph"),
     ("Oxygen (mg/L)", "dissolved_oxygen")],
    search=("pond__owner__name__icontains",),
    sub_county="pond__sub_county", status_field=None,
    kind="record", date_field="date",
)

Register(
    "production-estimates", x.FishProductionEstimate, "Production estimates", "production estimate", "Fisheries",
    ["pond", "period_label", "estimated_kg", "basis"],
    [("Pond", "pond"), ("Period", "period_label"), ("Estimated (kg)", "estimated_kg"), ("Basis", "basis")],
    search=("pond__owner__name__icontains", "period_label__icontains"),
    sub_county="pond__sub_county", status_field=None,
    kind="record", sum=("estimated_kg", "Estimated production (kg)"),
)

Register(
    "fishing-gears", x.FishingGear, "Fishing gears", "fishing gear record", "Fisheries",
    ["landing_site", "date", "gear_type", "quantity", "mesh_size_mm", "legal_status"],
    [("Date", "date"), ("Landing site", "landing_site.name"), ("Gear", "get_gear_type_display"),
     ("Quantity", "quantity"), ("Mesh (mm)", "mesh_size_mm"), ("Legal status", "get_legal_status_display")],
    search=("landing_site__name__icontains",),
    sub_county="landing_site__sub_county", status_field=None,
    kind="record", date_field="date", sum=("quantity", "Gears recorded"),
)

CONFIGS["fish-ponds"].children += [
    {"title": "Measurements", "key": "pond-measurements", "fk": "pond"},
    {"title": "Feeding", "key": "feeding-records", "fk": "pond"},
    {"title": "Water quality", "key": "water-quality", "fk": "pond"},
    {"title": "Production estimates", "key": "production-estimates", "fk": "pond"},
]
CONFIGS["landing-sites"].children.append(
    {"title": "Fishing gears", "key": "fishing-gears", "fk": "landing_site"}
)