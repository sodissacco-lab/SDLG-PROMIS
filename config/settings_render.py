
# ======================= Render hosting (add at the very bottom of config/settings.py) =======================
import os as _os
from pathlib import Path as _Path

import dj_database_url as _dj

_ON_RENDER = bool(_os.environ.get("RENDER"))

if _ON_RENDER:
    DEBUG = _os.environ.get("DEBUG", "False") == "True"
    SECRET_KEY = _os.environ["SECRET_KEY"]

    _host = _os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    _domains = ["sorotidlg-prodn.com", "www.sorotidlg-prodn.com"]
    ALLOWED_HOSTS = _domains + ([_host] if _host else [])
    CSRF_TRUSTED_ORIGINS = [f"https://{d}" for d in ALLOWED_HOSTS]

    DATABASES = {"default": _dj.config(conn_max_age=600, ssl_require=True)}

    # static files served by WhiteNoise
    if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
        MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    STATIC_ROOT = _Path(BASE_DIR) / "staticfiles"
    STATIC_URL = "/static/"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

    # uploaded photos live on the persistent disk
    MEDIA_ROOT = _os.environ.get("MEDIA_ROOT", "/var/data/media")
    MEDIA_URL = "/media/"

    # HTTPS
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
