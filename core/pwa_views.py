import json
import re
from datetime import date as date_cls

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import Activity, Department, Parish, SubCounty
from .pwa_models import OfflineSync


def user_obj(u, attr, model):
    """The user's department / sub-county as a model object, whether the user
    record stores it as a link or as plain text (matched by name)."""
    val = getattr(u, attr, None)
    if not val:
        return None
    if hasattr(val, "pk"):
        return val
    return model.objects.filter(name__iexact=str(val).strip()).first()


try:
    from .photo_models import ActivityPhoto
except Exception:  # photos not installed
    ActivityPhoto = None

try:
    from .activity_types import BY_DEPARTMENT
except Exception:
    BY_DEPARTMENT = {}

MAX_PHOTOS = 6


# ------------------------------------------------------------ small helpers
def field_names(model):
    return {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}


def pick(model, *candidates):
    """First field name that really exists on the model."""
    have = field_names(model)
    for name in candidates:
        if name in have:
            return name
    return None


# ------------------------------------------------------- manifest + worker
def manifest(request):
    data = {
        "name": "SDLG-Production MIS",
        "short_name": "SD-PROMIS",
        "description": "Field activity recording for Soroti District Production Department",
        "start_url": "/offline-app/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#ffffff",
        "theme_color": "#1b6b3a",
        "icons": [
            {"src": static("core/pwa/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("core/pwa/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
        ],
    }
    return HttpResponse(json.dumps(data), content_type="application/manifest+json")


SERVICE_WORKER = """
const VERSION = 'promis-v2';
const SHELL = ['/offline-app/', '/offline-app/data/', '/manifest.webmanifest',
               '%(i192)s', '%(i512)s', '%(logo)s'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(VERSION).then(function (c) {
    return Promise.all(SHELL.map(function (u) {
      return fetch(u, {credentials: 'same-origin'}).then(function (r) {
        if (r.ok) return c.put(u, r);
      }).catch(function () {});
    }));
  }));
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== VERSION; })
      .map(function (k) { return caches.delete(k); }));
  }));
  self.clients.claim();
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;
  var cacheable = SHELL.indexOf(url.pathname) !== -1;
  if (!cacheable) return;
  // network first, fall back to the saved copy
  e.respondWith(
    fetch(req).then(function (r) {
      if (r.ok) {
        var copy = r.clone();
        caches.open(VERSION).then(function (c) { c.put(url.pathname, copy); });
      }
      return r;
    }).catch(function () {
      return caches.match(url.pathname).then(function (hit) {
        return hit || new Response('Offline and not saved yet. Open this page once with internet.',
                                   {status: 503});
      });
    })
  );
});
"""


@never_cache
def service_worker(request):
    body = SERVICE_WORKER % {
        "i192": static("core/pwa/icon-192.png"),
        "i512": static("core/pwa/icon-512.png"),
        "logo": static("core/logo.jpg"),
    }
    resp = HttpResponse(body, content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    return resp


# -------------------------------------------------------------- the page
@login_required
@ensure_csrf_cookie
def offline_app(request):
    return render(request, "core/offline_app.html")


def lookup_data(u):
    """Lists the phone needs to fill the form with no signal."""
    depts = list(Department.objects.order_by("name").values("id", "name"))
    subs = list(SubCounty.objects.order_by("name").values("id", "name"))
    parishes = list(Parish.objects.order_by("name").values("id", "name", "sub_county_id"))
    types = {name: list(items) for name, items in BY_DEPARTMENT.items()}
    my_dept = getattr(user_obj(u, "department", Department), "id", None)
    my_sub = getattr(user_obj(u, "sub_county", SubCounty), "id", None)
    return {
        "user": u.get_full_name() or u.get_username(),
        "my_department": my_dept,
        "my_sub_county": my_sub,
        "departments": depts,
        "sub_counties": subs,
        "parishes": parishes,
        "activity_types": types,
    }


@login_required
@never_cache
def offline_data(request):
    """Everything the phone needs to fill the form with no signal."""
    return JsonResponse(lookup_data(request.user))


# ------------------------------------------------------------------ sync
def _int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def sync_record(request):
    """Saves one phone-made record. The caller must have set request.user."""
    try:
        data = json.loads(request.POST.get("payload", ""))
    except ValueError:
        return JsonResponse({"ok": False, "error": "Unreadable record."}, status=400)

    client_id = str(data.get("client_id", ""))[:64]
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", client_id):
        return JsonResponse({"ok": False, "error": "Record has no valid id."}, status=400)

    done = OfflineSync.objects.filter(client_id=client_id).select_related("activity").first()
    if done:
        return JsonResponse({"ok": True, "id": done.activity_id, "duplicate": True})

    # ---- required fields and honest validation
    try:
        when = date_cls.fromisoformat(str(data.get("date", "")))
    except ValueError:
        return JsonResponse({"ok": False, "error": "Date is missing or wrong."}, status=422)
    if when > date_cls.today():
        return JsonResponse({"ok": False, "error": "Date is in the future."}, status=422)

    dept = Department.objects.filter(pk=_int(data.get("department"))).first()
    sub = SubCounty.objects.filter(pk=_int(data.get("sub_county"))).first()
    parish = Parish.objects.filter(pk=_int(data.get("parish"))).first()
    atype = str(data.get("activity_type") or "").strip()
    if not (dept and sub and parish and atype):
        return JsonResponse({"ok": False, "error": "Department, activity type, sub-county and parish are required."}, status=422)
    if parish.sub_county_id != sub.id:
        return JsonResponse({"ok": False, "error": "Parish does not belong to that sub-county."}, status=422)

    male, female = _int(data.get("male")), _int(data.get("female"))
    youth, pwd = _int(data.get("youth")), _int(data.get("pwd"))
    total = male + female
    if youth > total or pwd > total:
        return JsonResponse({"ok": False, "error": "Youth or PWD cannot be more than male plus female."}, status=422)

    # ---- map the phone's answers onto whatever fields Activity really has
    values, stored = {}, []

    def put(label, candidates, value, required_value=True):
        name = pick(Activity, *candidates)
        if name and (value or value == 0 or not required_value):
            values[name] = value
            stored.append(label)

    put("date", ("date", "activity_date"), when)
    put("department", ("department",), dept)
    put("activity type", ("activity_type",), atype)
    put("sub-county", ("sub_county",), sub)
    put("parish", ("parish",), parish)
    put("village", ("village",), str(data.get("village") or "")[:100], required_value=False)
    put("description", ("description", "details"), str(data.get("description") or ""))
    put("findings", ("findings",), str(data.get("findings") or ""))
    put("action taken", ("action_taken", "actions_taken", "action"), str(data.get("action_taken") or ""))
    put("male", ("male", "males"), male)
    put("female", ("female", "females"), female)
    put("youth", ("youth",), youth)
    put("pwd", ("pwd",), pwd)
    for name in ("beneficiaries", "total_beneficiaries", "people_reached", "participants"):
        if name in field_names(Activity):
            values[name] = total
            stored.append("total")
            break

    lat, lng = data.get("latitude"), data.get("longitude")
    try:
        lat, lng = round(float(lat), 6), round(float(lng), 6)
    except (TypeError, ValueError):
        lat = lng = None
    if lat is not None:
        put("GPS", ("latitude", "gps_lat", "lat"), lat)
        put("GPS", ("longitude", "gps_lng", "gps_lon", "lng", "lon"), lng)

    officer_field = pick(Activity, "officer", "user", "created_by", "owner")
    if officer_field:
        values[officer_field] = request.user

    status_field = pick(Activity, "status")
    if status_field:
        values[status_field] = "submitted" if data.get("submit") else "draft"

    with transaction.atomic():
        activity = Activity.objects.create(**values)
        OfflineSync.objects.create(client_id=client_id, activity=activity)

        saved_photos = 0
        if ActivityPhoto is not None:
            img_field = next((f.name for f in ActivityPhoto._meta.fields
                              if f.get_internal_type() in ("ImageField", "FileField")), None)
            fk_field = next((f.name for f in ActivityPhoto._meta.fields
                             if f.is_relation and f.related_model is Activity), None)
            extra = {}
            by = pick(ActivityPhoto, "uploaded_by", "taken_by", "officer", "user")
            if by:
                extra[by] = request.user
            if img_field and fk_field:
                for f in request.FILES.getlist("photos")[:MAX_PHOTOS]:
                    ActivityPhoto.objects.create(**{fk_field: activity, img_field: f}, **extra)
                    saved_photos += 1

    return JsonResponse({"ok": True, "id": activity.pk, "photos": saved_photos, "stored": sorted(set(stored))})


offline_sync = login_required(require_POST(sync_record))
