from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .activity_types import all_types
from .models import Activity, Department, Parish, SubCounty, Target, User
from .pdm_models import PDMBeneficiary, PDMGroup, PDMVisit
from .photo_models import ActivityPhoto

admin.site.site_header = "SDLG-Production MIS"
admin.site.site_title = "SDLG-Production MIS admin"
admin.site.index_title = "Administration"

admin.site.register(Department)
admin.site.register(SubCounty)
admin.site.register(Parish)

MIS_FIELDS = ("Production MIS", {"fields": ("role", "department", "sub_county", "phone")})


@admin.register(User)
class SystemUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (MIS_FIELDS,)
    add_fieldsets = UserAdmin.add_fieldsets + (MIS_FIELDS,)
    list_display = ("username", "first_name", "last_name", "role", "department", "is_active")
    list_filter = ("role", "department", "is_active")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("date", "activity_type", "department", "officer", "sub_county", "status")
    list_filter = ("department", "status", "sub_county", "date")
    search_fields = ("activity_type", "description", "officer__username")


class TargetForm(forms.ModelForm):
    activity_type = forms.ChoiceField(
        required=False,
        choices=[("", "All activity types")] + [(t, t) for t in all_types()],
    )

    class Meta:
        model = Target
        fields = "__all__"


@admin.register(Target)
class TargetAdmin(admin.ModelAdmin):
    form = TargetForm
    list_display = ("fiscal_year", "department", "activity_type", "measure", "q1", "q2", "q3", "q4")
    list_filter = ("fiscal_year", "department")


@admin.register(PDMGroup)
class PDMGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "parish", "sub_county", "enterprise", "registered_by")
    list_filter = ("sub_county",)
    search_fields = ("name", "contact_person")


@admin.register(PDMBeneficiary)
class PDMBeneficiaryAdmin(admin.ModelAdmin):
    list_display = ("name", "sex", "group", "parish", "sub_county", "amount_received", "loan_status")
    list_filter = ("sub_county", "loan_status", "sex", "youth", "pwd")
    search_fields = ("name", "phone")


@admin.register(PDMVisit)
class PDMVisitAdmin(admin.ModelAdmin):
    list_display = ("beneficiary", "date", "enterprise_status", "revenue", "expenditure", "officer")
    list_filter = ("enterprise_status", "date")


@admin.register(ActivityPhoto)
class ActivityPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "activity", "uploaded_by", "uploaded_at")
from . import reg_admin  # noqa: E402,F401 