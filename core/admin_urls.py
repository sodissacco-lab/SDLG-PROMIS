from django.urls import path

from . import admin_views as v

urlpatterns = [
    path("", v.home, name="adm_home"),
    path("settings/", v.settings_page, name="adm_settings"),
    path("audit/", v.audit, name="adm_audit"),
    path("backup/", v.backup, name="adm_backup"),
    path("backup/download/<str:name>/", v.backup_download, name="adm_backup_download"),
    path("parishes/bulk/", v.parish_bulk, name="adm_parish_bulk"),
    path("documents/<int:pk>/download/", v.doc_download, name="adm_doc_download"),
    path("<slug:slug>/", v.page_list, name="adm_list"),
    path("<slug:slug>/new/", v.page_edit, name="adm_new"),
    path("<slug:slug>/<int:pk>/edit/", v.page_edit, name="adm_edit"),
    path("<slug:slug>/<int:pk>/delete/", v.page_delete, name="adm_delete"),
]