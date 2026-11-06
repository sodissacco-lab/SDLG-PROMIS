import os
from datetime import datetime
from functools import wraps
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db import models
from django.db.models import ProtectedError, Q
from django.forms import modelform_factory
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .admin2_models import AuditLog, Document, Partner, Project, SystemSetting
from .models import Parish, SubCounty, Target

User = get_user_model()


# ------------------------------------------------------------------ access
def is_manager(u):
    return u.is_superuser or getattr(u, "role", "") in ("admin", "dpo")


def is_staff_user(u):
    return u.is_superuser or getattr(u, "role", "") != "viewer"


def manager_only(view):
    @wraps(view)
    def wrapper(request, *a, **k):
        if not is_manager(request.user):
            raise PermissionDenied
        return view(request, *a, **k)

    return login_required(wrapper)


# ------------------------------------------------------------------- forms
def _date_widgets(field, **kwargs):
    if isinstance(field, models.DateField) and not isinstance(field, models.DateTimeField):
        kwargs["widget"] = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    return field.formfield(**kwargs)


_names = {f.name for f in User._meta.get_fields()}
USER_FIELDS = [f for f in ["username", "first_name", "last_name", "email", "role",
                           "department", "sub_county", "phone", "is_active"] if f in _names]


class UserForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Password", required=False, widget=forms.PasswordInput(render_value=False),
        help_text="Required for a new user. For an existing user, leave blank to keep the current password.",
    )

    class Meta:
        model = User
        fields = USER_FIELDS

    def clean_new_password(self):
        pw = self.cleaned_data.get("new_password")
        if not self.instance.pk and not pw:
            raise forms.ValidationError("Set a password for the new user.")
        if pw:
            password_validation.validate_password(pw, self.instance)
        return pw

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get("new_password")
        if pw:
            user.set_password(pw)
        if commit:
            user.save()
            self.save_m2m()
        return user


class SettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        exclude = []


# ------------------------------------------------------- generic page setup
def _cols(model, candidates):
    have = {f.name for f in model._meta.get_fields()}
    return [(label, path) for label, path in candidates if path.split(".")[0] in have or hasattr(model, path)]


PAGES = {
    "sub-counties": dict(
        model=SubCounty, title="Sub-counties", single="sub-county", access="manager", delete=False,
        cols=_cols(SubCounty, [("Name", "name"), ("Code", "code")]), search=["name"], filters=[],
    ),
    "parishes": dict(
        model=Parish, title="Parishes", single="parish", access="manager", delete=True, bulk=True,
        cols=[("Parish", "name"), ("Sub-county", "sub_county")],
        search=["name", "sub_county__name"], filters=["sub_county"],
    ),
    "users": dict(
        model=User, title="Users & accounts", single="user", access="manager", delete=False, form=UserForm,
        cols=_cols(User, [("Username", "username"), ("Name", "get_full_name"), ("Role", "role"),
                          ("Department", "department"), ("Sub-county", "sub_county"),
                          ("Phone", "phone"), ("Active", "is_active")]),
        search=["username", "first_name", "last_name"],
        filters=[f for f in ["role", "department", "sub_county"] if f in _names],
    ),
    "targets": dict(
        model=Target, title="Work plan targets", single="target", access="manager", delete=True,
        cols=_cols(Target, [("Department", "department"), ("Activity type", "activity_type"),
                            ("Measure", "measure"), ("Financial year", "fiscal_year"),
                            ("Q1", "q1"), ("Q2", "q2"), ("Q3", "q3"), ("Q4", "q4")]),
        search=[f for f in ["activity_type", "measure"] if f in {x.name for x in Target._meta.get_fields()}],
        filters=[f for f in ["department", "fiscal_year"] if f in {x.name for x in Target._meta.get_fields()}],
    ),
    "partners": dict(
        model=Partner, title="Partners", single="partner", access="staff", delete=True,
        cols=[("Partner", "name"), ("Type", "partner_type"), ("Focus", "focus_area"),
              ("Contact", "contact_person"), ("Phone", "phone"), ("Active", "active")],
        search=["name", "focus_area", "contact_person"], filters=["partner_type"],
    ),
    "projects": dict(
        model=Project, title="Projects", single="project", access="staff", delete=True,
        cols=[("Project", "name"), ("Partner", "partner"), ("Department", "department"),
              ("Budget (UGX)", "budget"), ("Start", "start_date"), ("End", "end_date"), ("Status", "status")],
        search=["name", "funder", "partner__name"], filters=["status", "department", "partner"],
    ),
    "documents": dict(
        model=Document, title="Document Centre", single="document", access="staff", delete=True,
        download=True, owner_field="uploaded_by", exclude=["uploaded_by", "created_at"],
        cols=[("Title", "title"), ("Category", "category"), ("Department", "department"),
              ("Year", "year"), ("Uploaded by", "uploaded_by"), ("Added", "created_at")],
        search=["title", "description"], filters=["category", "department"],
    ),
}


def _cfg(slug):
    cfg = PAGES.get(slug)
    if cfg is None:
        raise Http404
    return cfg


def _check(user, cfg, action):
    if cfg["access"] == "manager":
        ok = is_manager(user)
    elif action == "view":
        ok = True
    elif action == "delete":
        ok = is_manager(user)
    else:
        ok = is_staff_user(user)
    if not ok:
        raise PermissionDenied


def cell(obj, path):
    val = obj
    for part in path.split("."):
        if val is None:
            return ""
        field = None
        try:
            field = val._meta.get_field(part)
        except Exception:
            pass
        if field is not None and getattr(field, "choices", None):
            val = getattr(val, "get_%s_display" % part)()
        else:
            val = getattr(val, part, "")
            if callable(val):
                val = val()
    if val is True:
        return "Yes"
    if val is False:
        return "No"
    return "" if val is None else val


# --------------------------------------------------------------------- home
@manager_only
def home(request):
    backups = _backups()
    tiles = [
        ("Users & accounts", User.objects.filter(is_active=True).count(), "adm_list", "users", "green"),
        ("Sub-counties", SubCounty.objects.count(), "adm_list", "sub-counties", "blue"),
        ("Parishes", Parish.objects.count(), "adm_list", "parishes", "orange"),
        ("Targets", Target.objects.count(), "adm_list", "targets", "purple"),
        ("Documents", Document.objects.count(), "adm_list", "documents", "pink"),
        ("Partners", Partner.objects.count(), "adm_list", "partners", "green"),
        ("Projects", Project.objects.count(), "adm_list", "projects", "orange"),
    ]
    tiles = [{"label": a, "value": b, "url": reverse(c, args=[d]) if d else reverse(c), "color": e}
             for a, b, c, d, e in tiles]
    return render(request, "core/adm_home.html", {
        "tiles": tiles,
        "last_backup": backups[0] if backups else None,
        "audit_count": AuditLog.objects.count(),
    })


# ------------------------------------------------------------- generic CRUD
@login_required
def page_list(request, slug):
    cfg = _cfg(slug)
    _check(request.user, cfg, "view")
    model = cfg["model"]
    qs = model.objects.all()
    related = [f.name for f in model._meta.get_fields() if f.is_relation and f.many_to_one]
    if related:
        qs = qs.select_related(*related)
    q = request.GET.get("q", "").strip()
    if q and cfg["search"]:
        cond = Q()
        for s in cfg["search"]:
            cond |= Q(**{s + "__icontains": q})
        qs = qs.filter(cond)
    filters = []
    for name in cfg["filters"]:
        field = model._meta.get_field(name)
        value = request.GET.get(name, "")
        if field.is_relation:
            options = [(str(o.pk), str(o)) for o in field.related_model.objects.all()]
        elif field.choices:
            options = [(str(k), str(v)) for k, v in field.choices]
        else:
            vals = model.objects.order_by().values_list(name, flat=True).distinct()
            options = [(str(v), str(v)) for v in vals if v not in (None, "")]
        if value:
            qs = qs.filter(**{name: value})
        filters.append({"name": name, "label": str(field.verbose_name).capitalize(),
                        "options": options, "value": value})
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    rows = [(o, [cell(o, p) for _, p in cfg["cols"]]) for o in page]
    keep = request.GET.copy()
    keep.pop("page", None)
    return render(request, "core/adm_list.html", {
        "slug": slug, "title": cfg["title"], "single": cfg["single"], "columns": [c for c, _ in cfg["cols"]],
        "rows": rows, "page": page, "filters": filters, "q": q, "keep": keep.urlencode(),
        "can_add": cfg["access"] != "manager" and is_staff_user(request.user) or is_manager(request.user),
        "can_delete": cfg["delete"] and is_manager(request.user),
        "bulk": cfg.get("bulk"), "download": cfg.get("download"),
        "owner_field": cfg.get("owner_field"), "me": request.user.pk,
    })


@login_required
def page_edit(request, slug, pk=None):
    cfg = _cfg(slug)
    _check(request.user, cfg, "edit")
    obj = get_object_or_404(cfg["model"], pk=pk) if pk else None
    Form = cfg.get("form") or modelform_factory(
        cfg["model"], exclude=cfg.get("exclude", ()), formfield_callback=_date_widgets)
    form = Form(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if obj is None and cfg.get("owner_field"):
            setattr(saved, cfg["owner_field"], request.user)
        saved.save()
        form.save_m2m()
        messages.success(request, "%s saved." % cfg["single"].capitalize())
        return redirect("adm_list", slug=slug)
    return render(request, "core/adm_form.html", {
        "form": form, "title": ("Edit " if obj else "Add ") + cfg["single"],
        "back_url": reverse("adm_list", args=[slug]),
    })


@login_required
def page_delete(request, slug, pk):
    cfg = _cfg(slug)
    obj = get_object_or_404(cfg["model"], pk=pk)
    owner = cfg.get("owner_field")
    if not (owner and getattr(obj, owner + "_id", None) == request.user.pk):
        _check(request.user, cfg, "delete")
    if not cfg["delete"] and not owner:
        raise PermissionDenied
    if request.method == "POST":
        try:
            obj.delete()
            messages.success(request, "Deleted.")
        except ProtectedError:
            messages.error(request, "This record cannot be deleted because other records depend on it.")
        return redirect("adm_list", slug=slug)
    return render(request, "core/adm_confirm.html", {
        "obj": obj, "title": "Delete " + cfg["single"], "back_url": reverse("adm_list", args=[slug]),
    })


@manager_only
def parish_bulk(request):
    subs = SubCounty.objects.all()
    if request.method == "POST":
        sub = get_object_or_404(SubCounty, pk=request.POST.get("sub_county"))
        added = skipped = 0
        for line in request.POST.get("names", "").splitlines():
            name = " ".join(line.split())
            if not name:
                continue
            if Parish.objects.filter(sub_county=sub, name__iexact=name).exists():
                skipped += 1
            else:
                Parish.objects.create(sub_county=sub, name=name.title() if name.isupper() else name)
                added += 1
        messages.success(request, "%d parishes added to %s; %d already existed." % (added, sub, skipped))
        return redirect("adm_list", slug="parishes")
    return render(request, "core/adm_bulk.html", {"subs": subs})


@login_required
def doc_download(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if not doc.file:
        raise Http404
    return FileResponse(doc.file.open("rb"), as_attachment=True, filename=os.path.basename(doc.file.name))


# ----------------------------------------------------------------- settings
@manager_only
def settings_page(request):
    form = SettingForm(request.POST or None, instance=SystemSetting.get())
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Settings saved.")
        return redirect("adm_settings")
    return render(request, "core/adm_form.html", {
        "form": form, "title": "System settings", "back_url": reverse("adm_home"),
    })


# -------------------------------------------------------------------- audit
@manager_only
def audit(request):
    qs = AuditLog.objects.select_related("user")
    q = request.GET.get("q", "").strip()
    action = request.GET.get("action", "")
    user = request.GET.get("user", "")
    if q:
        qs = qs.filter(Q(summary__icontains=q) | Q(model_name__icontains=q))
    if action:
        qs = qs.filter(action=action)
    if user:
        qs = qs.filter(user_id=user)
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    keep = request.GET.copy()
    keep.pop("page", None)
    return render(request, "core/adm_audit.html", {
        "page": page, "q": q, "action": action, "user_id": user, "keep": keep.urlencode(),
        "users": User.objects.order_by("username"),
        "actions": ["created", "updated", "deleted", "login", "logout"],
    })


# ------------------------------------------------------------------- backup
def _backup_dir():
    return Path(settings.BASE_DIR) / "backups"


def _backups():
    folder = _backup_dir()
    if not folder.exists():
        return []
    out = []
    for p in sorted(folder.iterdir(), reverse=True):
        if p.is_file() and p.suffix in (".sqlite3", ".json"):
            st = p.stat()
            out.append({"name": p.name, "size": round(st.st_size / 1048576, 2),
                        "when": datetime.fromtimestamp(st.st_mtime)})
    return out


@manager_only
def backup(request):
    if request.method == "POST":
        try:
            call_command("backup_db")
            messages.success(request, "Backup completed.")
        except Exception as exc:
            messages.error(request, "Backup failed: %s" % exc)
        return redirect("adm_backup")
    return render(request, "core/adm_backup.html", {"files": _backups()[:40]})


@manager_only
def backup_download(request, name):
    if name not in {b["name"] for b in _backups()}:
        raise Http404
    return FileResponse(open(_backup_dir() / name, "rb"), as_attachment=True, filename=name)