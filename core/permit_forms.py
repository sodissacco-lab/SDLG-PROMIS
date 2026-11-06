from django import forms
from django.utils import timezone

from .permit_models import (
    ANIMAL_OTHER,
    ANIMAL_SLAUGHTER,
    ANIMAL_SUB,
    ANIMAL_COMMODITIES,
    FISH,
    MovementPermit,
)

_ANIMAL = [
    "issue_date", "valid_days", "book_number",
    "holder_name", "holder_phone", "farmer_code",
    "commodity", "quantity", "description",
    "origin_sub_county", "from_place", "to_place", "via", "purpose",
    "vehicle_reg", "fee", "receipt_number", "inspection_notes", "outbreak_confirmed",
]

KEEP = {
    ANIMAL_SUB: _ANIMAL + ["county"],
    ANIMAL_SLAUGHTER: [f for f in _ANIMAL if f != "purpose"] + ["brand", "slaughter_within_days"],
    ANIMAL_OTHER: list(_ANIMAL),
    FISH: [
        "issue_date", "valid_days", "book_number",
        "holder_name", "address", "holder_phone", "farmer_code",
        "fish_species", "quantity", "fish_form",
        "origin_lake", "origin_landing_site", "origin_market", "origin_district",
        "to_place", "dest_district", "transport_mode", "vehicle_reg",
        "inspected", "inspection_notes", "officer_post", "fee", "receipt_number",
    ],
}

ALL_FIELDS = sorted({f for names in KEEP.values() for f in names})

SECTIONS = {
    FISH: [
        ("The permit", ["issue_date", "valid_days", "book_number"]),
        ("Section A: the bearer", ["holder_name", "address", "holder_phone", "farmer_code"]),
        ("The fish", ["fish_species", "quantity", "fish_form"]),
        ("Details of origin", ["origin_lake", "origin_landing_site", "origin_market", "origin_district"]),
        ("Destination and transport", ["to_place", "dest_district", "transport_mode", "vehicle_reg"]),
        ("Section B: attestation, fees and officer",
         ["inspected", "inspection_notes", "officer_post", "fee", "receipt_number"]),
    ],
}
_ANIMAL_SECTIONS = [
    ("The permit", ["issue_date", "valid_days", "book_number"]),
    ("Who is moving the animals", ["holder_name", "county", "holder_phone", "farmer_code"]),
    ("The animals", ["commodity", "quantity", "description", "brand"]),
    ("The journey", ["origin_sub_county", "from_place", "to_place", "via", "purpose",
                     "slaughter_within_days", "vehicle_reg"]),
    ("Checks and fees", ["inspection_notes", "outbreak_confirmed", "fee", "receipt_number"]),
]
for _t in (ANIMAL_SUB, ANIMAL_SLAUGHTER, ANIMAL_OTHER):
    SECTIONS[_t] = _ANIMAL_SECTIONS

SPECIES_TO_RECORD = {
    "cattle": "cattle", "goats": "goat", "sheep": "sheep",
    "pigs": "pig", "chicken": "chicken", "dogs": "dog",
}


def ongoing_outbreaks(sub_county, commodity):
    """Ongoing outbreaks recorded in the Disease surveillance register for the area of origin."""
    if sub_county is None:
        return []
    try:
        from .vet2_models import DiseaseSurveillance
    except Exception:
        return []
    qs = DiseaseSurveillance.objects.filter(
        record_type="outbreak", outbreak_status="ongoing", sub_county=sub_county
    )
    species = SPECIES_TO_RECORD.get(commodity)
    if species:
        qs = qs.filter(species=species)
    return list(qs[:3])


class PermitForm(forms.ModelForm):
    class Meta:
        model = MovementPermit
        fields = ALL_FIELDS
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.TextInput(),
            "inspection_notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, kind=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = kind
        keep = KEEP[kind]
        for name in list(self.fields):
            if name not in keep:
                del self.fields[name]
        if "commodity" in self.fields:
            self.fields["commodity"].required = True
            self.fields["commodity"].choices = [("", "Choose")] + ANIMAL_COMMODITIES
            self.fields["quantity"].label = "Number of animals"
        if kind == FISH:
            self.fields["quantity"].label = "Quantity (kg)"
            self.fields["fish_species"].required = True
            self.fields["fish_form"].required = True
            self.fields["to_place"].label = "Destination"
            self.fields["origin_district"].required = True
            self.fields["fee"].label = "Fees paid (Ug. Shs.)"
            self.fields["inspected"].required = False
        if kind == ANIMAL_SLAUGHTER:
            self.fields["slaughter_within_days"].required = True
            self.fields["brand"].help_text = "Brand or markings the animals carry."
        if kind == ANIMAL_SUB:
            self.fields["county"].required = True
        if "purpose" in self.fields:
            self.fields["purpose"].required = True
        if "origin_sub_county" in self.fields:
            self.fields["origin_sub_county"].required = True
            self.fields["from_place"].required = True
        if "outbreak_confirmed" in self.fields:
            self.fields["outbreak_confirmed"].required = False

    def sections(self):
        out = []
        for title, names in SECTIONS[self.kind]:
            fields = [self[n] for n in names if n in self.fields]
            if fields:
                out.append((title, fields))
        return out

    # ------------------------------------------------------------- checks
    def clean_issue_date(self):
        value = self.cleaned_data["issue_date"]
        if value > timezone.localdate():
            raise forms.ValidationError("The date of issue cannot be in the future.")
        return value

    def clean_valid_days(self):
        value = self.cleaned_data["valid_days"]
        if value < 1 or value > 60:
            raise forms.ValidationError("Enter a number of days from 1 to 60.")
        return value

    def clean_quantity(self):
        value = self.cleaned_data["quantity"]
        if value is None or value <= 0:
            raise forms.ValidationError("Enter a quantity above zero.")
        return value

    def clean_book_number(self):
        value = (self.cleaned_data.get("book_number") or "").strip()
        if value:
            clash = MovementPermit.objects.filter(book_number__iexact=value, permit_type=self.kind)
            if self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise forms.ValidationError(
                    "A permit with this book number is already recorded (%s)." % clash.first().code
                )
        return value

    def clean(self):
        data = super().clean()
        if self.kind == FISH:
            if not data.get("inspected"):
                self.add_error("inspected", "The attestation must be ticked before a fish permit is issued.")
        else:
            frm, to = (data.get("from_place") or "").strip().lower(), (data.get("to_place") or "").strip().lower()
            if frm and frm == to:
                self.add_error("to_place", "The destination is the same as the place of origin.")
            found = ongoing_outbreaks(data.get("origin_sub_county"), data.get("commodity"))
            if found and not data.get("outbreak_confirmed"):
                names = ", ".join(sorted({o.disease for o in found}))
                self.add_error(
                    "outbreak_confirmed",
                    "The Disease surveillance register shows an ongoing outbreak (%s) in %s. "
                    "Check with the District Veterinary Officer, then tick this box to continue."
                    % (names, data["origin_sub_county"]),
                )
        return data
