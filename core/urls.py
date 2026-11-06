from django.urls import include, path

from . import (
    api,
    district_views,
    narrative_views,
    pack_views,
    pdm_views,
    personal_views,
    photo_views,
    reg_views,
    register_views,
    report_views,
    sector_views,
    sub_views,
    views,
)
from .reg_config import CONFIGS

urlpatterns = [
    path("", personal_views.my_dashboard, name="dashboard"),
    path("activity/new/", views.activity_new, name="activity_new"),
    path("activity/", views.activity_list, name="activity_list"),
    path("activity/<int:pk>/", views.activity_detail, name="activity_detail"),
    path("activity/<int:pk>/edit/", views.activity_edit, name="activity_edit"),
    path("activity/<int:pk>/review/", views.activity_review, name="activity_review"),
    path("review/", views.review_queue, name="review_queue"),
    path("photos/<int:pk>/", photo_views.photo_file, name="photo_file"),
    path("photos/<int:pk>/delete/", photo_views.photo_delete, name="photo_delete"),
    path("district/", district_views.district, name="district"),
    path("sector/<int:pk>/", sector_views.sector, name="sector"),
    path("subcounties/", sub_views.subcounty_list, name="subcounty_list"),
    path("subcounties/<int:pk>/", sub_views.subcounty, name="subcounty"),
    path("reports/", report_views.report, name="report"),
    path("reports/docx/", report_views.report_docx, name="report_docx"),
    path("reports/pdf/", report_views.report_pdf, name="report_pdf"),
    path("reports/narrative/", narrative_views.narrative, name="narrative"),
    path("reports/narrative/docx/", narrative_views.narrative_docx, name="narrative_docx"),
    path("reports/narrative/pdf/", narrative_views.narrative_pdf, name="narrative_pdf"),
    path("reports/pack/pdf/", pack_views.pack_pdf, name="pack_pdf"),
    path("reports/pack/docx/", pack_views.pack_docx, name="pack_docx"),
    path("pdm/", pdm_views.pdm_list, name="pdm_list"),
    path("pdm/new/", pdm_views.pdm_new, name="pdm_new"),
    path("pdm/groups/", pdm_views.pdm_groups, name="pdm_groups"),
    path("pdm/groups/new/", pdm_views.pdm_group_new, name="pdm_group_new"),
    path("pdm/summary/", pdm_views.pdm_summary, name="pdm_summary"),
    path("pdm/summary/pdf/", pdm_views.pdm_summary_pdf, name="pdm_summary_pdf"),
    path("pdm/summary/docx/", pdm_views.pdm_summary_docx, name="pdm_summary_docx"),
    path("pdm/<int:pk>/", pdm_views.pdm_detail, name="pdm_detail"),
    path("pdm/<int:pk>/edit/", pdm_views.pdm_edit, name="pdm_edit"),
    path("pdm/<int:pk>/visit/", pdm_views.pdm_visit_new, name="pdm_visit_new"),
    path("registers/<slug:slug>/", register_views.register_page, name="register"),
    path("api/parishes/", api.parishes, name="api_parishes"),
]

for _key in CONFIGS:
    urlpatterns.append(
        path(
            "r/%s/" % _key,
            reg_views.reg_list,
            {"key": _key},
            name="r_" + _key.replace("-", "_"),
        )
    )

urlpatterns += [
    path("r/<slug:key>/new/", reg_views.reg_new, name="reg_new"),
    path("r/<slug:key>/<int:pk>/", reg_views.reg_detail, name="reg_detail"),
    path("r/<slug:key>/<int:pk>/edit/", reg_views.reg_edit, name="reg_edit"),
    path("r/<slug:key>/<int:pk>/merge/<int:dup>/", reg_views.reg_merge, name="reg_merge"),
]
from . import notification_views  # noqa: E402

urlpatterns += [path("notifications/", notification_views.notifications, name="notifications")]
from . import map_views, workplan_views  # noqa: E402

urlpatterns += [
    path("map/", map_views.map_view, name="map"),
    path("workplan/", workplan_views.workplan, name="workplan"),
    path("", include("core.permit_urls")),
]