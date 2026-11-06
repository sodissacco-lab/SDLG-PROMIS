import importlib.util

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("manage/", include("core.admin_urls")),
]

# Optional page groups: only added when their file is present.
for _module in ("core.pwa_urls", "core.permit_urls", "core.api_urls"):
    if importlib.util.find_spec(_module):
        urlpatterns.append(path("", include(_module)))

urlpatterns.append(path("", include("core.urls")))