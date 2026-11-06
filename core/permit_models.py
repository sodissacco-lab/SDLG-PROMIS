from datetime import timedelta

from django.db import models
from django.utils import timezone

from .reg_models import Coded, Farmer, Stamped

ANIMAL_SUB = "animal_sub"
ANIMAL_SLAUGHTER = "animal_slaughter"
ANIMAL_OTHER = "animal_other"
FISH = "fish"
ANIMAL_TYPES = (ANIMAL_SUB, ANIMAL_SLAUGHTER, ANIMAL_OTHER)

TYPES = [
    (ANIMAL_SUB, "Animals: sub-county to sub-county"),
    (ANIMAL_SLAUGHTER, "Animals: district to district, for slaughter only"),
    (ANIMAL_OTHER, "Animals: district to district, other than slaughter"),
    (FISH, "Fish and fish products"),
]

ANIMAL_COMMODITIES = [
    ("cattle", "Cattle"),
    ("goats", "Goats"),
    ("sheep", "Sheep"),
    ("pigs", "Pigs"),
    ("chicken", "Chicken"),
    ("dogs", "Dogs"),
    ("other_animal", "Other animals"),
]
FISH_FORMS = [
    ("fresh", "Fresh"),
    ("smoked", "Smoked"),
    ("salted", "Salted"),
    ("sun_dried", "Sun dried"),
]
UNITS = [
    ("head", "head"),
    ("kg", "kg"),
]
STATUS = [
    ("issued", "Issued"),
    ("used", "Completed (arrived)"),
    ("cancelled", "Cancelled"),
]


class MovementPermit(Coded, Stamped):
    CODE_PREFIX = "MP"

    permit_type = models.CharField("Permit type", max_length=16, choices=TYPES)
    book_number = models.CharField(
        "Serial number in the permit book", max_length=40, blank=True,
        help_text="The number printed on the paper permit, if you use a permit book.",
    )
    issue_date = models.DateField("Date of issue")
    valid_days = models.PositiveIntegerField("Valid for (days from the date of issue)")
    valid_until = models.DateField(null=True, blank=True, editable=False)

    # who
    holder_name = models.CharField("Name", max_length=150)
    address = models.CharField("Address", max_length=200, blank=True)
    holder_phone = models.CharField("Phone", max_length=40, blank=True)
    farmer_code = models.CharField("Farmer ID, if registered (e.g. FM-00012)", max_length=20, blank=True)
    farmer = models.ForeignKey(
        Farmer, null=True, blank=True, editable=False, on_delete=models.SET_NULL, related_name="+"
    )
    county = models.CharField("County of", max_length=100, blank=True)

    # what: animals
    commodity = models.CharField("Animals", max_length=20, choices=ANIMAL_COMMODITIES, blank=True)
    description = models.CharField(
        "Description (sex, age, colour, markings)", max_length=250, blank=True
    )
    brand = models.CharField("Brand", max_length=150, blank=True)
    # what: fish
    fish_species = models.CharField("Fish species (local name)", max_length=150, blank=True)
    fish_form = models.CharField("Form of the fish", max_length=10, choices=FISH_FORMS, blank=True)
    # both
    quantity = models.DecimalField("Quantity", max_digits=10, decimal_places=1)
    unit = models.CharField(max_length=5, choices=UNITS, default="head")

    # journey
    origin_sub_county = models.ForeignKey(
        "core.SubCounty", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="Sub-county of origin",
    )
    from_place = models.CharField("From (place)", max_length=250, blank=True)
    origin_lake = models.CharField("Lake", max_length=100, blank=True)
    origin_landing_site = models.ForeignKey(
        "core.LandingSite", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="Landing site",
    )
    origin_market = models.CharField("Fish market", max_length=120, blank=True)
    origin_district = models.CharField("District of origin", max_length=100, blank=True)
    to_place = models.CharField("To (place)", max_length=200)
    dest_district = models.CharField("Destination district", max_length=100, blank=True)
    via = models.CharField("Via (route)", max_length=200, blank=True)
    purpose = models.CharField("For the purpose of", max_length=200, blank=True)
    slaughter_within_days = models.PositiveIntegerField("To be slaughtered within (days)", null=True, blank=True)
    transport_mode = models.CharField("Mode of transport", max_length=80, blank=True)
    vehicle_reg = models.CharField("Registration number of the vehicle", max_length=30, blank=True)

    # issue and checks
    officer_post = models.CharField("Title of the issuing officer", max_length=80, blank=True)
    fee = models.PositiveBigIntegerField("Fees paid (UGX)", default=0)
    receipt_number = models.CharField("Receipt number", max_length=40, blank=True)
    inspection_notes = models.TextField("Inspection notes", blank=True)
    inspected = models.BooleanField(
        "I certify that the fish has been inspected and conforms to the provisions of the Fish Act "
        "and the statutory instruments made under it",
        default=False,
    )
    outbreak_confirmed = models.BooleanField(
        "There is an ongoing outbreak in the area of origin. I have checked with the District "
        "Veterinary Officer that this movement is allowed",
        default=False,
    )

    status = models.CharField(max_length=10, choices=STATUS, default="issued")
    status_note = models.CharField("Reason or note", max_length=250, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issue_date", "-id"]
        verbose_name = "movement permit"

    def save(self, *args, **kwargs):
        if self.issue_date and self.valid_days is not None:
            self.valid_until = self.issue_date + timedelta(days=self.valid_days)
        if self.permit_type == FISH:
            self.unit = "kg"
            parts = [
                self.origin_landing_site.name if self.origin_landing_site_id else "",
                self.origin_market,
                self.origin_lake,
                self.origin_district,
            ]
            self.from_place = ", ".join(p for p in parts if p)[:250]
        elif self.permit_type == ANIMAL_SLAUGHTER:
            self.purpose = "Slaughter"
            self.unit = "head"
        elif self.permit_type in ANIMAL_TYPES:
            self.unit = "head"
        if self.farmer_code:
            self.farmer = Farmer.objects.filter(code__iexact=self.farmer_code.strip()).first()
        else:
            self.farmer = None
        super().save(*args, **kwargs)

    # ---------------------------------------------------------------- helpers
    @property
    def is_animal(self):
        return self.permit_type in ANIMAL_TYPES

    @property
    def is_expired(self):
        return bool(self.valid_until and self.valid_until < timezone.localdate())

    @property
    def state(self):
        if self.status == "cancelled":
            return "Cancelled"
        if self.status == "used":
            return "Completed"
        return "Expired" if self.is_expired else "Valid"

    @property
    def officer_caption(self):
        return {
            ANIMAL_SUB: "Inspecting Officer",
            ANIMAL_SLAUGHTER: "Veterinary Officer",
            ANIMAL_OTHER: "Veterinary Officer",
            FISH: "Issuing Officer",
        }.get(self.permit_type, "Officer")

    @property
    def quantity_text(self):
        if self.quantity is None:
            return ""
        return format(self.quantity.normalize(), "f")

    @property
    def what(self):
        """Short description of what is moving, for lists."""
        if self.permit_type == FISH:
            label = self.fish_species or "fish"
            return "%s kg %s%s" % (
                self.quantity_text, label.lower(),
                " (%s)" % self.get_fish_form_display().lower() if self.fish_form else "",
            )
        return "%s head of %s" % (self.quantity_text, (self.get_commodity_display() or "animals").lower())

    @property
    def movement_text(self):
        """The wording that goes on the permit after 'is allowed to move'."""
        text = self.what
        if self.description and self.is_animal:
            text += " (%s)" % self.description
        return text

    @property
    def destination(self):
        if self.dest_district:
            return "%s, %s" % (self.to_place, self.dest_district)
        return self.to_place

    @property
    def issued_by(self):
        user = self.registered_by
        return (user.get_full_name() or user.get_username()) if user else ""

    def __str__(self):
        return "%s - %s" % (self.code or "new", self.holder_name)
