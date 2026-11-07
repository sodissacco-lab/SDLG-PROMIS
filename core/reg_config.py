from django import forms
from django.db import models
from django.utils import timezone

from . import reg_models as m

CONFIGS = {}


class Register:
    def __init__(self, key, model, label, singular, sector, fields, columns, **kw):
        self.key = key
        self.model = model
        self.label = label
        self.singular = singular
        self.sector = sector
        self.fields = fields
        self.columns = columns
        self.search = kw.get("search", ())
        self.base = kw.get("base", {})
        self.exclude = kw.get("exclude", {})
        self.preset = kw.get("preset", {})
        self.sub_county_path = kw.get("sub_county", "sub_county")
        self.sum = kw.get("sum")
        self.date_field = kw.get("date_field")
        self.kind = kw.get("kind", "register")
        names = {f.name for f in model._meta.fields}
        self.status_field = kw.get("status_field", "status" if "status" in names else None)
        self.status_choices = kw.get("status_choices")
        self.dup = kw.get("dup", False)
        self.children = kw.get("children", [])
        self.future_ok = kw.get("future_ok", ())
        self.has_created = "created_at" in names
        CONFIGS[key] = self

    def queryset(self):
        qs = self.model.objects.all()
        if self.base:
            qs = qs.filter(**self.base)
        if self.exclude:
            qs = qs.exclude(**self.exclude)
        related = [
            f.name for f in self.model._meta.fields if f.is_relation and f.many_to_one
        ]
        return qs.select_related(*related)


def cell(obj, path, fmt=None):
    cur = obj
    parts = path.split(".")
    for index, part in enumerate(parts):
        cur = getattr(cur, part, None)
        if callable(cur) and index == len(parts) - 1:
            cur = cur()
        if cur is None:
            return "-"
    if cur == "":
        return "-"
    if isinstance(cur, bool):
        return "Yes" if cur else "No"
    if fmt == "money":
        try:
            return "{:,}".format(int(cur))
        except (TypeError, ValueError):
            return cur
    return cur


def build_form(cfg):
    model = cfg.model
    widgets = {}
    for name in cfg.fields:
        field = model._meta.get_field(name)
        if isinstance(field, models.DateField):
            widgets[name] = forms.DateInput(attrs={"type": "date"})
        elif isinstance(field, models.TextField):
            widgets[name] = forms.Textarea(attrs={"rows": 3})
    base = forms.modelform_factory(model, fields=list(cfg.fields), widgets=widgets)

    class RegisterForm(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if cfg.status_choices and "status" in self.fields:
                self.fields["status"].choices = cfg.status_choices
            for fld in self.fields.values():
                qs = getattr(fld, "queryset", None)
                if qs is not None and qs.model is m.Farmer:
                    fld.queryset = m.Farmer.objects.exclude(status="merged").order_by("name")
            if self.is_bound and self.data.get("confirm_distinct"):
                self._add_confirm()

        def _add_confirm(self):
            self.fields["confirm_distinct"] = forms.BooleanField(
                required=False,
                label="This is a different record from the one that already exists (tick to save anyway)",
            )

        def clean(self):
            cleaned = super().clean()
            sub_county = cleaned.get("sub_county")
            parish = cleaned.get("parish")
            if sub_county and parish and parish.sub_county_id != sub_county.id:
                self.add_error(
                    "parish", "This parish does not belong to the selected sub-county."
                )
            today = timezone.localdate()
            for name in cfg.fields:
                field = model._meta.get_field(name)
                value = cleaned.get(name)
                if (
                    isinstance(field, models.DateField)
                    and value
                    and name not in cfg.future_ok
                    and value > today
                ):
                    self.add_error(name, "The date cannot be in the future.")
            if cfg.dup:
                name = (cleaned.get("name") or "").strip()
                if name and parish:
                    same = model.objects.filter(name__iexact=name, parish=parish)
                    if cfg.exclude:
                        same = same.exclude(**cfg.exclude)
                    if self.instance.pk:
                        same = same.exclude(pk=self.instance.pk)
                    phone = (cleaned.get("phone") or "").strip()
                    if phone:
                        same = same.filter(phone=phone)
                    if same.exists() and not self.data.get("confirm_distinct"):
                        self._add_confirm()
                        self.add_error(
                            "name",
                            "A record with this name already exists in this parish. "
                            "If it is a different one, tick the box at the bottom and save again.",
                        )
            return cleaned

    return RegisterForm


SHARED_PLACE = ["sub_county", "parish", "village"]

Register(
    "farmer-registry", m.Farmer, "Farmers", "farmer", None,
    ["name", "sex", "age_group", "phone", "national_id", "household"] + SHARED_PLACE
    + ["youth", "pwd", "grows_crops", "keeps_livestock", "fish_farming",
       "does_entomology", "is_fisher",
       "farm_size", "farm_size_unit", "years_farming", "production_notes",
       "group_name", "pdm_beneficiary", "support_received", "trainings",
       "latitude", "longitude", "status"],
    [("ID", "code"), ("Name", "name"), ("Sex", "get_sex_display"), ("Phone", "phone"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name"), ("Crops", "grows_crops"),
     ("Livestock", "keeps_livestock"), ("Fish", "fish_farming"),
     ("Bees/silk", "does_entomology"), ("Fisher", "is_fisher"),
     ("Status", "get_status_display")],
    search=("name__icontains", "phone__icontains", "code__icontains"),
    exclude={"status": "merged"},
    status_choices=[("active", "Active"), ("inactive", "Inactive")],
    dup=True,
    children=[
        {"title": "Fish ponds", "key": "fish-ponds", "fk": "owner"},
        {"title": "Cage farms", "key": "cage-farms", "fk": "owner"},
    ],
)

Register(
    "households", m.Household, "Households", "household", None,
    ["head_name", "members"] + SHARED_PLACE + ["notes"],
    [("ID", "code"), ("Head", "head_name"), ("Members", "members"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name"), ("Village", "village")],
    search=("head_name__icontains", "code__icontains"),
    status_field=None,
    children=[{"title": "Farmers in this household", "key": "farmer-registry", "fk": "household"}],
)

Register(
    "fish-farmers", m.Farmer, "Fish farmers", "fish farmer", "Fisheries",
    ["name", "sex", "phone", "household"] + SHARED_PLACE
    + ["youth", "pwd", "grows_crops", "keeps_livestock", "status"],
    [("ID", "code"), ("Name", "name"), ("Sex", "get_sex_display"), ("Phone", "phone"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name"), ("Ponds", "ponds.count"),
     ("Status", "get_status_display")],
    search=("name__icontains", "phone__icontains", "code__icontains"),
    base={"fish_farming": True}, preset={"fish_farming": True},
    exclude={"status": "merged"},
    status_choices=[("active", "Active"), ("inactive", "Inactive")],
    dup=True,
    children=[
        {"title": "Fish ponds", "key": "fish-ponds", "fk": "owner"},
        {"title": "Cage farms", "key": "cage-farms", "fk": "owner"},
    ],
)

Register(
    "landing-sites", m.LandingSite, "Landing sites", "landing site", "Fisheries",
    ["name"] + SHARED_PLACE + ["water_body", "gazetted", "facilities", "latitude", "longitude", "status"],
    [("Name", "name"), ("Sub-county", "sub_county"), ("Parish", "parish.name"),
     ("Water body", "water_body"), ("Gazetted", "gazetted"), ("Boats", "boats.count"),
     ("Status", "get_status_display")],
    search=("name__icontains", "water_body__icontains"),
    dup=True,
    children=[
        {"title": "Boats", "key": "boats", "fk": "landing_site"},
        {"title": "Fishers", "key": "fishers", "fk": "landing_site"},
        {"title": "Daily catches", "key": "daily-catches", "fk": "landing_site"},
        {"title": "Revenue", "key": "landing-site-revenue", "fk": "landing_site"},
        {"title": "Illegal fishing incidents", "key": "illegal-fishing-incidents", "fk": "landing_site"},
    ],
)

Register(
    "boat-owners", m.BoatOwner, "Boat owners", "boat owner", "Fisheries",
    ["name", "sex", "phone", "landing_site"] + SHARED_PLACE,
    [("Name", "name"), ("Sex", "get_sex_display"), ("Phone", "phone"),
     ("Landing site", "landing_site.name"), ("Boats", "boats.count"), ("Sub-county", "sub_county")],
    search=("name__icontains", "phone__icontains"),
    status_field=None, dup=True,
    children=[{"title": "Boats", "key": "boats", "fk": "owner"}],
)

Register(
    "boats", m.Boat, "Boats", "boat", "Fisheries",
    ["registration_number", "boat_name", "boat_type", "engine_hp", "owner", "landing_site", "status"],
    [("Registration no.", "registration_number"), ("Name", "boat_name"),
     ("Type", "get_boat_type_display"), ("Engine (HP)", "engine_hp"), ("Owner", "owner.name"),
     ("Landing site", "landing_site.name"), ("Status", "get_status_display")],
    search=("registration_number__icontains", "boat_name__icontains", "owner__name__icontains"),
    sub_county="landing_site__sub_county",
    children=[{"title": "Licences", "key": "fishing-licences", "fk": "boat"}],
)

Register(
    "fishers", m.Fisher, "Fishers", "fisher", "Fisheries",
    ["name", "sex", "phone", "landing_site", "role"] + SHARED_PLACE + ["youth", "pwd", "status"],
    [("Name", "name"), ("Sex", "get_sex_display"), ("Role", "get_role_display"),
     ("Landing site", "landing_site.name"), ("Sub-county", "sub_county"),
     ("Parish", "parish.name"), ("Status", "get_status_display")],
    search=("name__icontains", "phone__icontains"),
    dup=True,
)

Register(
    "fishing-licences", m.FishingLicence, "Licences", "licence", "Fisheries",
    ["boat", "licence_type", "licence_number", "issue_date", "expiry_date", "fee", "receipt_number"],
    [("Licence no.", "licence_number"), ("Type", "get_licence_type_display"),
     ("Boat", "boat.registration_number"), ("Issued", "issue_date"),
     ("Expires", "expiry_date"), ("Fee (UGX)", "fee", "money"), ("Status", "validity")],
    search=("licence_number__icontains", "boat__registration_number__icontains"),
    sub_county="boat__landing_site__sub_county",
    kind="authorisation", date_field="issue_date",
    sum=("fee", "Fees recorded (UGX)", "money"),
    future_ok=("expiry_date",),
)

Register(
    "daily-catches", m.DailyCatch, "Daily catches", "daily catch record", "Fisheries",
    ["landing_site", "date", "species", "quantity_kg", "boats_count", "notes"],
    [("Date", "date"), ("Landing site", "landing_site.name"), ("Species", "species.name"),
     ("Quantity (kg)", "quantity_kg"), ("Boats", "boats_count")],
    search=("landing_site__name__icontains",),
    sub_county="landing_site__sub_county",
    kind="record", date_field="date", sum=("quantity_kg", "Total catch (kg)"),
)

Register(
    "fish-species", m.FishSpecies, "Fish species", "fish species", "Fisheries",
    ["name", "local_name"],
    [("Name", "name"), ("Local name", "local_name")],
    search=("name__icontains", "local_name__icontains"),
    sub_county=None, kind="reference",
)

Register(
    "landing-site-revenue", m.LandingSiteRevenue, "Landing-site revenue", "revenue record", "Fisheries",
    ["landing_site", "date", "revenue_type", "amount", "receipt_number"],
    [("Date", "date"), ("Landing site", "landing_site.name"),
     ("Type", "get_revenue_type_display"), ("Amount (UGX)", "amount", "money"),
     ("Receipt no.", "receipt_number")],
    search=("landing_site__name__icontains", "receipt_number__icontains"),
    sub_county="landing_site__sub_county",
    kind="record", date_field="date", sum=("amount", "Total collected (UGX)", "money"),
)

Register(
    "fish-ponds", m.FishPond, "Fish ponds", "fish pond", "Fisheries",
    ["owner", "pond_name", "pond_type", "size_sqm", "species"] + SHARED_PLACE + ["status", "latitude", "longitude"],
    [("Owner", "owner.name"), ("Pond", "pond_name"), ("Type", "get_pond_type_display"),
     ("Size (sqm)", "size_sqm"), ("Species", "species"), ("Sub-county", "sub_county"),
     ("Parish", "parish.name"), ("Status", "get_status_display")],
    search=("owner__name__icontains", "pond_name__icontains"),
    sum=("size_sqm", "Total pond area (sqm)"),
    children=[
        {"title": "Stocking", "key": "stocking-records", "fk": "pond"},
        {"title": "Harvests", "key": "fish-harvest", "fk": "pond"},
        {"title": "Mortality", "key": "fish-mortality", "fk": "pond"},
    ],
)

Register(
    "cage-farms", m.CageFarm, "Cage farms", "cage farm", "Fisheries",
    ["owner", "number_of_cages", "species"] + SHARED_PLACE + ["status"],
    [("Owner", "owner.name"), ("Cages", "number_of_cages"), ("Species", "species"),
     ("Sub-county", "sub_county"), ("Parish", "parish.name"), ("Status", "get_status_display")],
    search=("owner__name__icontains",),
    sum=("number_of_cages", "Total cages"),
)

Register(
    "stocking-records", m.StockingRecord, "Stocking records", "stocking record", "Fisheries",
    ["pond", "date", "species", "fingerlings", "source"],
    [("Date", "date"), ("Pond", "pond"), ("Species", "species"),
     ("Fingerlings", "fingerlings"), ("Source", "source")],
    search=("pond__owner__name__icontains", "species__icontains"),
    sub_county="pond__sub_county",
    kind="record", date_field="date", sum=("fingerlings", "Fingerlings stocked"),
)

Register(
    "fish-harvest", m.HarvestRecord, "Harvest records", "harvest record", "Fisheries",
    ["pond", "date", "species", "quantity_kg"],
    [("Date", "date"), ("Pond", "pond"), ("Species", "species"), ("Quantity (kg)", "quantity_kg")],
    search=("pond__owner__name__icontains", "species__icontains"),
    sub_county="pond__sub_county",
    kind="record", date_field="date", sum=("quantity_kg", "Total harvest (kg)"),
)

Register(
    "fish-mortality", m.MortalityRecord, "Mortality records", "mortality record", "Fisheries",
    ["pond", "date", "number_dead", "suspected_cause"],
    [("Date", "date"), ("Pond", "pond"), ("Number dead", "number_dead"), ("Suspected cause", "suspected_cause")],
    search=("pond__owner__name__icontains", "suspected_cause__icontains"),
    sub_county="pond__sub_county",
    kind="record", date_field="date", sum=("number_dead", "Total fish deaths"),
)

Register(
    "fish-mongers", m.FishTrader, "Fish mongers", "fish monger", "Fisheries",
    ["name", "sex", "phone", "landing_site", "market"] + SHARED_PLACE + ["status"],
    [("Name", "name"), ("Sex", "get_sex_display"), ("Phone", "phone"),
     ("Landing site", "landing_site.name"), ("Market", "market"), ("Sub-county", "sub_county")],
    search=("name__icontains", "phone__icontains"),
    base={"trader_type": "monger"}, preset={"trader_type": "monger"}, dup=True,
)

Register(
    "fish-buyers", m.FishTrader, "Fish buyers", "fish buyer", "Fisheries",
    ["name", "sex", "phone", "landing_site", "market"] + SHARED_PLACE + ["status"],
    [("Name", "name"), ("Sex", "get_sex_display"), ("Phone", "phone"),
     ("Landing site", "landing_site.name"), ("Market", "market"), ("Sub-county", "sub_county")],
    search=("name__icontains", "phone__icontains"),
    base={"trader_type": "buyer"}, preset={"trader_type": "buyer"}, dup=True,
)

Register(
    "illegal-fishing-incidents", m.IllegalFishingIncident, "Illegal fishing incidents", "incident", "Fisheries",
    ["date", "landing_site", "sub_county", "parish", "offence", "gear_seized", "action_taken"],
    [("Date", "date"), ("Landing site", "landing_site.name"), ("Sub-county", "sub_county"),
     ("Offence", "offence"), ("Gear seized", "gear_seized"), ("Action taken", "action_taken")],
    search=("offence__icontains", "landing_site__name__icontains"),
    kind="record", date_field="date",)
from . import reg_extra_config  # noqa: E402,F401
from . import crop_vet_config  # noqa: E402,F401
from . import ent_com_config  # noqa: E402,F401
from . import ent2_config  # noqa: E402,F401
from . import import_config  # noqa: E402,F401
from . import vet2_config  # noqa: E402,F401
from . import permit_registry  # noqa: E402,F401