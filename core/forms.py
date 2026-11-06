from django import forms
from django.utils import timezone

from .activity_types import all_types, allowed_types
from .models import Activity


class ActivityForm(forms.ModelForm):
    activity_type = forms.ChoiceField(
        choices=[("", "---------")] + [(t, t) for t in all_types()]
    )

    class Meta:
        model = Activity
        fields = [
            "department",
            "activity_type",
            "date",
            "start_time",
            "end_time",
            "sub_county",
            "parish",
            "village", "landing_site", "farmer", "pond",
            "latitude",
            "longitude",
            "male",
            "female",
            "youth",
            "pwd",
            "description",
            "findings",
            "action_taken",
            "follow_up",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "description": forms.Textarea(attrs={"rows": 3}),
            "findings": forms.Textarea(attrs={"rows": 3}),
            "action_taken": forms.Textarea(attrs={"rows": 3}),
            "follow_up": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sub_county"].required = True
        self.fields["parish"].required = True
        self.fields["male"].label = "Men reached"
        self.fields["female"].label = "Women reached"
        self.fields["youth"].label = "Of these, youth"
        self.fields["pwd"].label = "Of these, persons with disability"
        self.fields["findings"].label = "Findings"
        self.fields["follow_up"].label = "Follow-up required"

    def clean_date(self):
        d = self.cleaned_data["date"]
        if d > timezone.localdate():
            raise forms.ValidationError("The date cannot be in the future.")
        return d

    def clean(self):
        cleaned = super().clean()

        dept = cleaned.get("department")
        atype = cleaned.get("activity_type")
        if dept and atype and atype not in allowed_types(dept.name):
            self.add_error(
                "activity_type",
                "This activity type is not available for the selected department.",
            )

        sub_county = cleaned.get("sub_county")
        parish = cleaned.get("parish")
        if parish and sub_county and parish.sub_county_id != sub_county.id:
            self.add_error(
                "parish", "This parish does not belong to the selected sub-county."
            )

        male = cleaned.get("male") or 0
        female = cleaned.get("female") or 0
        total = male + female
        if (cleaned.get("youth") or 0) > total:
            self.add_error("youth", "Youth cannot be more than the total reached.")
        if (cleaned.get("pwd") or 0) > total:
            self.add_error(
                "pwd", "Persons with disability cannot be more than the total reached."
            )

        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", "End time must be after the start time.")

        return cleaned