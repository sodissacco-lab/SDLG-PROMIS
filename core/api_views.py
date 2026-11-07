"""JSON API used by the Flutter app. Sign in once, then send the token in the
Authorization header ("Bearer <token>"). No extra packages or migrations needed."""
import json
from datetime import date, datetime
from functools import wraps

from django.contrib.auth import authenticate, get_user_model
from django.core import signing
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import pwa_views as pv
from .models import Activity, Department, SubCounty

SALT = "sdlg-promis-api"
MAX_AGE = 60 * 60 * 24 * 30  # a token lasts 30 days
SUPERVISOR_ROLES = {"admin", "dpo", "head"}

User = get_user_model()


def _err(message, status=400):
    return JsonResponse({"ok": False, "error": message}, status=status)


def is_supervisor(user):
    return bool(user.is_superuser or getattr(user, "role", "") in SUPERVISOR_ROLES)


def _user(u):
    dept = pv.user_obj(u, "department", Department)
    sub = pv.user_obj(u, "sub_county", SubCounty)
    return {
        "id": u.pk,
        "username": u.get_username(),
        "name": u.get_full_name() or u.get_username(),
        "role": getattr(u, "role", ""),
        "is_supervisor": is_supervisor(u),
        "department": {"id": dept.pk, "name": str(dept)} if dept else (
            {"id": None, "name": str(getattr(u, "department", ""))} if getattr(u, "department", "") else None),
        "sub_county": {"id": sub.pk, "name": str(sub)} if sub else (
            {"id": None, "name": str(getattr(u, "sub_county", ""))} if getattr(u, "sub_county", "") else None),
    }


def token_required(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return _err("Please sign in.", 401)
        try:
            data = signing.loads(header[7:].strip(), salt=SALT, max_age=MAX_AGE)
        except signing.SignatureExpired:
            return _err("Your session has expired. Please sign in again.", 401)
        except signing.BadSignature:
            return _err("Please sign in.", 401)
        user = User.objects.filter(pk=data.get("uid"), is_active=True).first()
        if not user:
            return _err("This account is not active.", 401)
        request.user = user
        return view(request, *args, **kwargs)

    return csrf_exempt(inner)


# ------------------------------------------------------------------ sign in
@csrf_exempt
@require_POST
def login(request):
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        data = {}
    user = authenticate(
        request,
        username=str(data.get("username", "")).strip(),
        password=str(data.get("password", "")),
    )
    if not user or not user.is_active:
        return _err("Wrong username or password.", 401)
    token = signing.dumps({"uid": user.pk}, salt=SALT)
    return JsonResponse({"ok": True, "token": token, "user": _user(user)})


@token_required
@require_GET
def me(request):
    return JsonResponse({"ok": True, "user": _user(request.user)})


@token_required
@require_GET
def bootstrap(request):
    """Lists for the offline form: departments, sub-counties, parishes, activity types."""
    data = pv.lookup_data(request.user)
    data["ok"] = True
    data["user_info"] = _user(request.user)
    return JsonResponse(data)


# ------------------------------------------------------------------- sync
@token_required
@require_POST
def sync(request):
    """Same record format as the browser offline app: form field "payload"
    (JSON text) plus optional files named "photos"."""
    return pv.sync_record(request)


# --------------------------------------------------------- activity rows
def _get(a, *names):
    for n in names:
        if hasattr(a, n):
            v = getattr(a, n)
            if v not in (None, ""):
                return v
    return None


def _text(v):
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return str(v)


def _num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _row(a, detail=False):
    officer = _get(a, "officer", "user", "created_by", "owner")
    row = {
        "id": a.pk,
        "date": _text(_get(a, "date", "activity_date")),
        "activity_type": _text(getattr(a, "activity_label", None) or _get(a, "activity_type")),
        "department": _text(_get(a, "department")),
        "sub_county": "District HQ" if getattr(a, "at_district_hq", False) else _text(_get(a, "sub_county")),
        "parish": _text(_get(a, "parish")),
        "village": _text(_get(a, "village")),
        "start_time": _text(_get(a, "start_time"))[:5],
        "end_time": _text(_get(a, "end_time"))[:5],
        "status": _text(_get(a, "status")),
        "officer": (officer.get_full_name() or str(officer)) if officer else "",
        "reviewer_comment": _text(_get(a, "review_comment", "supervisor_comment",
                                       "returned_comment", "approval_comment", "comment", "remarks")),
    }
    male, female = _num(_get(a, "male", "males")), _num(_get(a, "female", "females"))
    row["male"], row["female"] = male, female
    row["total"] = male + female
    if detail:
        row.update({
            "description": _text(_get(a, "description", "details")),
            "findings": _text(_get(a, "findings")),
            "action_taken": _text(_get(a, "action_taken", "actions_taken", "action")),
            "youth": _num(_get(a, "youth")),
            "pwd": _num(_get(a, "pwd")),
            "latitude": _get(a, "latitude", "gps_lat", "lat"),
            "longitude": _get(a, "longitude", "gps_lng", "gps_lon", "lng", "lon"),
        })
    return row


def _officer_field():
    return pv.pick(Activity, "officer", "user", "created_by", "owner")


def _date_field():
    return pv.pick(Activity, "date", "activity_date")


def _status_field():
    return pv.pick(Activity, "status")


@token_required
@require_GET
def mine(request):
    f = _officer_field()
    qs = Activity.objects.filter(**{f: request.user}) if f else Activity.objects.none()
    d = _date_field()
    qs = qs.order_by("-" + d, "-pk") if d else qs.order_by("-pk")
    return JsonResponse({"ok": True, "activities": [_row(a, detail=True) for a in qs[:150]]})


@token_required
@require_GET
def summary(request):
    today = timezone.localdate()
    f, d, s = _officer_field(), _date_field(), _status_field()
    mine_qs = Activity.objects.filter(**{f: request.user}) if f else Activity.objects.none()
    out = {"ok": True, "month": today.strftime("%B %Y")}
    month_qs = mine_qs.filter(**{d + "__year": today.year, d + "__month": today.month}) if d else mine_qs
    out["this_month"] = month_qs.count()
    if s:
        for key in ("draft", "submitted", "approved", "returned"):
            out[key] = month_qs.filter(**{s: key}).count()  # this month only
    out["pending_approval"] = _pending_qs(request.user).count() if is_supervisor(request.user) else 0
    return JsonResponse(out)


# --------------------------------------------------------------- approvals
def _pending_qs(user):
    s = _status_field()
    if not s:
        return Activity.objects.none()
    qs = Activity.objects.filter(**{s: "submitted"})
    if not (user.is_superuser or getattr(user, "role", "") in ("admin", "dpo")):
        dept = pv.user_obj(user, "department", Department)
        if dept and pv.pick(Activity, "department"):
            qs = qs.filter(department=dept)
    of = _officer_field()
    if of:
        qs = qs.exclude(**{of: user})  # nobody approves their own work
    return qs


@token_required
@require_GET
def approvals(request):
    if not is_supervisor(request.user):
        return _err("Only supervisors can approve.", 403)
    qs = _pending_qs(request.user)
    d = _date_field()
    qs = qs.order_by(d, "pk") if d else qs.order_by("pk")
    return JsonResponse({"ok": True, "activities": [_row(a, detail=True) for a in qs[:100]]})


def _allowed_status(name, fallbacks):
    """Pick the status value this project really uses."""
    status_field = _status_field()
    choices = [c[0] for c in Activity._meta.get_field(status_field).choices] if status_field else []
    for candidate in (name,) + tuple(fallbacks):
        if not choices or candidate in choices:
            return candidate
    return name


@token_required
@require_POST
def decide(request, pk):
    if not is_supervisor(request.user):
        return _err("Only supervisors can approve.", 403)
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        data = {}
    action = data.get("action")
    comment = str(data.get("comment", "")).strip()
    if action not in ("approve", "return"):
        return _err("Choose approve or return.", 422)
    if action == "return" and not comment:
        return _err("Please write why it is being returned.", 422)

    activity = _pending_qs(request.user).filter(pk=pk).first()
    if not activity:
        return _err("This record is not waiting for your approval.", 404)

    status = _allowed_status("approved", ()) if action == "approve" else _allowed_status(
        "returned", ("rejected", "returned_for_correction", "revision"))
    setattr(activity, _status_field(), status)
    note = pv.pick(Activity, "review_comment", "supervisor_comment", "returned_comment",
                   "approval_comment", "comment", "remarks")
    if note and comment:
        setattr(activity, note, comment)
    who = pv.pick(Activity, "approved_by", "reviewed_by", "approver", "supervisor")
    if who:
        setattr(activity, who, request.user)
    when = pv.pick(Activity, "approved_at", "reviewed_at", "reviewed_on")
    if when:
        setattr(activity, when, timezone.now())
    activity.save()
    return JsonResponse({"ok": True, "status": status})
