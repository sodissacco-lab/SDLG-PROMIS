from django.conf import settings
from django.db import models
from django.utils import timezone

SEX = [("F", "Female"), ("M", "Male")]
ACTIVE = [("active", "Active"), ("inactive", "Inactive")]
FARM_CATEGORIES = [("household", "Household"), ("non_household", "Non-household")]
AGE_GROUPS = [
    ("youth", "Youth (18 to 30)"),
    ("adult", "Adult (31 to 59)"),
    ("elder", "Elder (60 and above)"),
]
SIZE_UNITS = [
    ("ponds", "Ponds"),
    ("boats", "Boats"),
    ("acres", "Acres"),
    ("animals", "Animals"),
    ("hives", "Beehives"),
]


class Stamped(models.Model):
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Place(Stamped):
    sub_county = models.ForeignKey(
        "core.SubCounty", on_delete=models.PROTECT, related_name="+"
    )
    parish = models.ForeignKey("core.Parish", on_delete=models.PROTECT, related_name="+")
    village = models.CharField(max_length=100, blank=True)

    class Meta:
        abstract = True


class Coded(models.Model):
    CODE_PREFIX = "ID"
    code = models.CharField(
        max_length=20, unique=True, null=True, blank=True, editable=False
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = "%s-%05d" % (self.CODE_PREFIX, self.pk)
            super().save(update_fields=["code"])


class Household(Coded, Place):
    CODE_PREFIX = "HH"
    head_name = models.CharField("Head of household", max_length=150)
    members = models.PositiveIntegerField("Household members", default=1)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["head_name"]

    def __str__(self):
        return "%s (%s)" % (self.head_name, self.code or "new")


class Farmer(Coded, Place):
    CODE_PREFIX = "FM"
    STATUS = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("merged", "Merged into another record"),
    ]
    name = models.CharField(max_length=150)
    sex = models.CharField(max_length=1, choices=SEX, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    household = models.ForeignKey(
        Household,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="farmers",
    )
    youth = models.BooleanField(default=False)
    pwd = models.BooleanField("Person with disability", default=False)
    grows_crops = models.BooleanField("Grows crops", default=False)
    keeps_livestock = models.BooleanField("Keeps livestock", default=False)
    fish_farming = models.BooleanField("Fish farming", default=False)
    does_entomology = models.BooleanField("Bee-keeping or sericulture", default=False)
    is_fisher = models.BooleanField("Fisher or boat owner", default=False)
    national_id = models.CharField("National ID (NIN)", max_length=20, blank=True)
    age_group = models.CharField(max_length=10, choices=AGE_GROUPS, blank=True)
    farm_size = models.DecimalField(
        "Farm size", max_digits=10, decimal_places=2, null=True, blank=True
    )
    farm_size_unit = models.CharField(
        "Unit of farm size", max_length=10, choices=SIZE_UNITS, blank=True
    )
    years_farming = models.PositiveSmallIntegerField(
        "Years farming", null=True, blank=True
    )
    production_notes = models.TextField("Production and inputs used", blank=True)
    group_name = models.CharField("Farmer group", max_length=150, blank=True)
    pdm_beneficiary = models.BooleanField("PDM beneficiary", default=False)
    support_received = models.TextField("Support received", blank=True)
    trainings = models.TextField("Trainings attended", blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    client_id = models.CharField(
        max_length=64, null=True, blank=True, unique=True, editable=False
    )
    farm_name = models.CharField("Farm or group name", max_length=250, blank=True)
    farm_category = models.CharField(
        "Farm category", max_length=14, choices=FARM_CATEGORIES, blank=True
    )
    status = models.CharField(max_length=10, choices=STATUS, default="active")
    merged_into = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="merged_from",
        editable=False,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return "%s (%s)" % (self.name, self.code or "new")


class FishSpecies(models.Model):
    name = models.CharField(max_length=100, unique=True)
    local_name = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "fish species"
        verbose_name_plural = "fish species"

    def __str__(self):
        return self.name


class LandingSite(Place):
    name = models.CharField(max_length=150)
    water_body = models.CharField("Water body", max_length=100, blank=True)
    gazetted = models.BooleanField(default=True)
    facilities = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BoatOwner(Place):
    name = models.CharField(max_length=150)
    sex = models.CharField(max_length=1, choices=SEX, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    landing_site = models.ForeignKey(
        LandingSite,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="boat_owners",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Boat(Stamped):
    TYPES = [
        ("canoe", "Wooden canoe"),
        ("planked", "Planked boat"),
        ("motorised", "Motorised boat"),
        ("other", "Other"),
    ]
    registration_number = models.CharField(max_length=40, unique=True)
    boat_name = models.CharField("Boat name", max_length=100, blank=True)
    boat_type = models.CharField("Boat type", max_length=12, choices=TYPES, default="canoe")
    engine_hp = models.PositiveIntegerField("Engine (HP)", default=0)
    vessel_type = models.CharField("Vessel type", max_length=80, blank=True)
    propulsion = models.CharField(max_length=40, blank=True)
    fishing_gear = models.CharField("Fishing gear", max_length=100, blank=True)
    main_species = models.CharField("Main fish species", max_length=80, blank=True)
    bariars = models.PositiveIntegerField(
        "Bariars (as in the registry)", null=True, blank=True
    )
    owner = models.ForeignKey(BoatOwner, on_delete=models.PROTECT, related_name="boats")
    landing_site = models.ForeignKey(
        LandingSite, on_delete=models.PROTECT, related_name="boats"
    )
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["registration_number"]

    def __str__(self):
        return self.registration_number


class Fisher(Place):
    ROLES = [
        ("owner", "Boat owner"),
        ("crew", "Crew"),
        ("net_maker", "Net maker"),
        ("other", "Other"),
    ]
    name = models.CharField(max_length=150)
    sex = models.CharField(max_length=1, choices=SEX)
    phone = models.CharField(max_length=40, blank=True)
    landing_site = models.ForeignKey(
        LandingSite,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fishers",
    )
    role = models.CharField(max_length=12, choices=ROLES, default="crew")
    youth = models.BooleanField(default=False)
    pwd = models.BooleanField("Person with disability", default=False)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FishingLicence(Stamped):
    TYPES = [("boat", "Boat licence"), ("fishing", "Fishing licence")]
    boat = models.ForeignKey(Boat, on_delete=models.PROTECT, related_name="licences")
    licence_type = models.CharField("Licence type", max_length=10, choices=TYPES, default="boat")
    licence_number = models.CharField("Licence number", max_length=40, unique=True)
    issue_date = models.DateField("Issue date")
    expiry_date = models.DateField("Expiry date")
    fee = models.PositiveBigIntegerField("Fee (UGX)", default=0)
    receipt_number = models.CharField("Receipt number", max_length=40, blank=True)

    class Meta:
        ordering = ["-expiry_date"]

    @property
    def is_valid(self):
        return self.expiry_date >= timezone.localdate()

    @property
    def validity(self):
        return "Valid" if self.is_valid else "Expired"

    def __str__(self):
        return self.licence_number


class DailyCatch(Stamped):
    landing_site = models.ForeignKey(
        LandingSite, on_delete=models.PROTECT, related_name="catches"
    )
    date = models.DateField()
    species = models.ForeignKey(
        FishSpecies, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    quantity_kg = models.DecimalField("Quantity (kg)", max_digits=10, decimal_places=1)
    boats_count = models.PositiveIntegerField("Boats that fished", default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return "%s %s" % (self.landing_site, self.date)


class LandingSiteRevenue(Stamped):
    TYPES = [
        ("landing_fee", "Landing fee"),
        ("licence_fee", "Licence fee"),
        ("levy", "Fish trade levy"),
        ("other", "Other"),
    ]
    landing_site = models.ForeignKey(
        LandingSite, on_delete=models.PROTECT, related_name="revenues"
    )
    date = models.DateField()
    revenue_type = models.CharField("Type", max_length=12, choices=TYPES, default="landing_fee")
    amount = models.PositiveBigIntegerField("Amount (UGX)")
    receipt_number = models.CharField("Receipt number", max_length=40, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return "%s %s" % (self.landing_site, self.date)


class FishPond(Place):
    TYPES = [("earthen", "Earthen"), ("lined", "Lined"), ("tank", "Tank")]
    STATUS = [
        ("active", "Active"),
        ("under_construction", "Under construction"),
        ("inactive", "Inactive"),
    ]
    owner = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="ponds")
    pond_name = models.CharField("Pond name or number", max_length=100, blank=True)
    pond_type = models.CharField("Pond type", max_length=10, choices=TYPES, default="earthen")
    size_sqm = models.DecimalField("Size (sqm)", max_digits=10, decimal_places=1, default=0)
    species = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="active")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["owner__name", "pond_name"]

    def __str__(self):
        return "%s - %s" % (self.owner.name, self.pond_name or "pond %s" % self.pk)


class CageFarm(Place):
    owner = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="cage_farms")
    number_of_cages = models.PositiveIntegerField("Number of cages", default=1)
    species = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["owner__name"]

    def __str__(self):
        return "%s - %s cages" % (self.owner.name, self.number_of_cages)


class StockingRecord(Stamped):
    pond = models.ForeignKey(FishPond, on_delete=models.PROTECT, related_name="stockings")
    date = models.DateField()
    species = models.CharField(max_length=100, blank=True)
    fingerlings = models.PositiveIntegerField("Fingerlings stocked", default=0)
    source = models.CharField("Source of fingerlings", max_length=150, blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class HarvestRecord(Stamped):
    pond = models.ForeignKey(FishPond, on_delete=models.PROTECT, related_name="harvests")
    date = models.DateField()
    species = models.CharField(max_length=100, blank=True)
    quantity_kg = models.DecimalField("Quantity (kg)", max_digits=10, decimal_places=1)

    class Meta:
        ordering = ["-date", "-id"]


class MortalityRecord(Stamped):
    pond = models.ForeignKey(FishPond, on_delete=models.PROTECT, related_name="mortalities")
    date = models.DateField()
    number_dead = models.PositiveIntegerField("Number dead", default=0)
    suspected_cause = models.CharField("Suspected cause", max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class FishTrader(Place):
    TYPES = [("monger", "Fish monger"), ("buyer", "Fish buyer")]
    name = models.CharField(max_length=150)
    sex = models.CharField(max_length=1, choices=SEX)
    phone = models.CharField(max_length=40, blank=True)
    landing_site = models.ForeignKey(
        LandingSite,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="traders",
    )
    trader_type = models.CharField(max_length=10, choices=TYPES, default="monger")
    market = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=ACTIVE, default="active")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class IllegalFishingIncident(Stamped):
    date = models.DateField()
    landing_site = models.ForeignKey(
        LandingSite,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incidents",
    )
    sub_county = models.ForeignKey(
        "core.SubCounty", on_delete=models.PROTECT, related_name="+"
    )
    parish = models.ForeignKey(
        "core.Parish", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    offence = models.CharField(max_length=200)
    gear_seized = models.TextField("Gear seized", blank=True)
    action_taken = models.TextField("Action taken", blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return "%s %s" % (self.date, self.offence)


ALL_MODELS = [
    Household,
    Farmer,
    LandingSite,
    BoatOwner,
    Boat,
    Fisher,
    FishingLicence,
    FishSpecies,
    DailyCatch,
    LandingSiteRevenue,
    FishPond,
    CageFarm,
    StockingRecord,
    HarvestRecord,
    MortalityRecord,
    FishTrader,
    IllegalFishingIncident,
]