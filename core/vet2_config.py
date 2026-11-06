from . import registers
from . import vet2_models as v
from .crop_vet_models import (
    AIService, AnimalHealthCase, DiseaseReport, LivestockCount,
    LivestockMarket, LivestockMortality, Outbreak, SlaughterRecord, TreatmentRecord,
)
from .reg_config import CONFIGS, SHARED_PLACE, Register

PLACE = SHARED_PLACE


def cfg(model):
    for c in CONFIGS.values():
        if getattr(c, "model", None) is model:
            return c
    raise RuntimeError("No register found for %s" % model.__name__)


def extend(model, fields, columns):
    c = cfg(model)
    c.fields = list(c.fields) + [f for f in fields if f not in c.fields]
    c.columns = list(c.columns) + columns


# ---- the one combined disease register ----
Register(
    "disease-surveillance", v.DiseaseSurveillance, "Disease surveillance", "disease record", "Veterinary",
    ["date", "record_type", "species", "disease", "diagnosis_status", "farmer",
     "animals_at_risk", "animals_sick", "animals_dead", "sample_taken", "lab_result",
     "action_taken", "outbreak_status", "reported_upward"] + PLACE + ["notes"],
    [("Date", "date"), ("Type", "get_record_type_display"), ("Species", "get_species_display"),
     ("Disease", "disease"), ("Diagnosis", "get_diagnosis_status_display"),
     ("Sick", "animals_sick"), ("Dead", "animals_dead"),
     ("Sub-county", "sub_county"), ("Outbreak", "get_outbreak_status_display")],
    search=("disease__icontains", "farmer__name__icontains", "lab_result__icontains"),
    status_field=None, kind="record", date_field="date",
    sum=("animals_dead", "Animals dead"),
)
registers._add(
    "disease-surveillance", "Disease surveillance", "record",
    "Sick animals, outbreaks, deaths and surveillance reports in one register.",
    "Cases and deaths by disease, species and area; outbreaks ongoing.",
)

# ---- hide the four old registers from the menu (data is kept) ----
_old = {AnimalHealthCase, Outbreak, LivestockMortality, DiseaseReport}
_old_slugs = {s for s, c in CONFIGS.items() if getattr(c, "model", None) in _old}


def _clean(items):
    out = []
    for it in items:
        if isinstance(it, str):
            if it not in _old_slugs:
                out.append(it)
        else:
            label, slugs = it
            slugs = [s for s in slugs if s not in _old_slugs]
            if slugs:
                out.append((label, slugs))
    return out


registers.MENUS["Veterinary"] = _clean(registers.MENUS["Veterinary"]) + ["disease-surveillance"]

# ---- the expanded registers ----
extend(AIService, ["service_time", "heat_type", "semen_breed", "bull_name", "calves_produced"],
       [("Time", "service_time"), ("Heat", "get_heat_type_display"),
        ("Semen breed", "semen_breed"), ("Bull", "bull_name"), ("Calves", "calves_produced")])
extend(TreatmentRecord, ["animal_sex", "age_value", "age_unit"],
       [("Sex", "get_animal_sex_display")])
extend(LivestockCount, ["dogs", "cats", "chicken"],
       [("Dogs", "dogs"), ("Cats", "cats"), ("Chicken", "chicken")])
extend(LivestockMarket, ["animal_category", "number_sold", "price_per_animal", "destination"],
       [("Category", "get_animal_category_display"), ("Sold", "number_sold"),
        ("Price each", "price_per_animal"), ("Destination", "destination")])
extend(SlaughterRecord, ["judgement", "organ_affected", "number_affected"],
       [("Judgement", "get_judgement_display"), ("Organ", "organ_affected")])