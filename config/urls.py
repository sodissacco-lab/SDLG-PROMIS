import importlib

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("manage/", include("core.admin_urls")),
]

# Optional page groups: added only if they load without errors.
for _module in ("core.pwa_urls", "core.permit_urls", "core.api_urls"):
    try:
        importlib.import_module(_module)
    except Exception:
        continue
    urlpatterns.append(path("", include(_module)))

urlpatterns.append(path("", include("core.urls")))