from django.urls import path

from . import pwa_views as v

urlpatterns = [
    path("sw.js", v.service_worker, name="pwa_sw"),
    path("manifest.webmanifest", v.manifest, name="pwa_manifest"),
    path("offline-app/", v.offline_app, name="offline_app"),
    path("offline-app/data/", v.offline_data, name="offline_data"),
    path("offline-app/sync/", v.offline_sync, name="offline_sync"),
]
