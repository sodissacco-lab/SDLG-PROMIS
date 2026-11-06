from django import forms
from django.utils import timezone

from .pdm_models import PDMBeneficiary, PDMGroup, PDMVisit


def _check_location(form, cleaned):
    sub_county = cleaned.get("sub_county")
    parish = cleaned.get("parish")
    if sub_county and parish and parish.sub_county_id != sub_county.id:
        form.add_error(
            "parish", "This parish does not belong to the selected sub-county."
        )


class BeneficiaryForm(forms.ModelForm):
    class Meta:
        model = PDMBeneficiary
        fields = [
            "name",
            "sex",
            "phone",
            "group",
            "sub_county",
            "parish",
            "village",
            "enterprise",
            "youth",
            "pwd",
            "amount_received",
            "date_received",
            "loan_status",
            "notes",
        ]
        widgets = {
            "date_received": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound and self.data.get("confirm_distinct"):
            self._add_confirm()

    def _add_confirm(self):
        self.fields["confirm_distinct"] = forms.BooleanField(
            required=False,
            label="This is a different person from the existing record (tick to save anyway)",
        )

    def clean(self):
        cleaned = super().clean()
        _check_location(self, cleaned)
        name = (cleaned.get("name") or "").strip()
        parish = cleaned.get("parish")
        if name and parish:
            same = PDMBeneficiary.objects.filter(name__iexact=name, parish=parish)
            if self.instance.pk:
                same = same.exclude(pk=self.instance.pk)
            phone = (cleaned.get("phone") or "").strip()
            if phone:
                same = same.filter(phone=phone)
            if same.exists() and not self.data.get("confirm_distinct"):
                self._add_confirm()
                self.add_error(
                    "name",
                    "A beneficiary with this name is already registered in this parish. "
                    "If this is a different person, tick the box at the bottom and save again.",
                )
        return cleaned

    def clean_date_received(self):
        d = self.cleaned_data.get("date_received")
        if d and d > timezone.localdate():
            raise forms.ValidationError("The date cannot be in the future.")
        return d


class GroupForm(forms.ModelForm):
    class Meta:
        model = PDMGroup
        fields = [
            "name",
            "sub_county",
            "parish",
            "village",
            "enterprise",
            "contact_person",
            "phone",
        ]

    def clean(self):
        cleaned = super().clean()
        _check_location(self, cleaned)
        return cleaned


class VisitForm(forms.ModelForm):
    class Meta:
        model = PDMVisit
        fields = [
            "date",
            "enterprise_status",
            "revenue",
            "expenditure",
            "production",
            "challenges",
            "action_taken",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "production": forms.Textarea(attrs={"rows": 2}),
            "challenges": forms.Textarea(attrs={"rows": 3}),
            "action_taken": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_date(self):
        d = self.cleaned_data["date"]
        if d > timezone.localdate():
            raise forms.ValidationError("The date cannot be in the future.")
        return d