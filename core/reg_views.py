from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import SubCounty
from .reg_config import CONFIGS, build_form, cell
from .reg_models import CageFarm, Farmer, FishPond
from .registers import KIND_LABELS


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _config(key):
    cfg = CONFIGS.get(key)
    if cfg is None:
        raise Http404
    return cfg


def _list_url(key):
    return reverse("r_" + key.replace("-", "_"))


def has_field(model, name):
    return any(f.name == name for f in model._meta.fields)


def can_view(user, cfg):
    if user.is_superuser or user.role in ("admin", "dpo", "viewer"):
        return True
    if cfg.sector is None:
        return True
    return user.department_id is not None and user.department.name == cfg.sector


def can_add(user):
    return user.is_superuser or user.role != "viewer"


def can_edit(user, obj):
    return (
        user.is_superuser
        or user.role in ("admin", "dpo")
        or getattr(obj, "registered_by_id", None) == user.id
    )


def _guard(request, cfg):
    if not can_view(request.user, cfg):
        messages.error(request, "You do not have access to this register.")
        return redirect("dashboard")
    return None


def _stats(cfg, qs):
    today = timezone.localdate()
    names = {f.name for f in cfg.model._meta.fields}
    first = {
        "register": "Registered",
        "record": "Records",
        "authorisation": "Issued",
        "reference": "Entries",
    }.get(cfg.kind, "Total")
    stats = [(first, qs.count())]
    if cfg.has_created:
        stats.append(
            (
                "New this month",
                qs.filter(
                    created_at__year=today.year, created_at__month=today.month
                ).count(),
            )
        )
    if cfg.status_field:
        stats.append((getattr(cfg, "active_label", "Active"), qs.filter(**{cfg.status_field: getattr(cfg, "active_value", "active")}).count()))
    if "expiry_date" in names:
        stats.append(("Valid now", qs.filter(expiry_date__gte=today).count()))
    if cfg.date_field:
        stats.append(
            (
                "Dated this month",
                qs.filter(
                    **{
                        cfg.date_field + "__year": today.year,
                        cfg.date_field + "__month": today.month,
                    }
                ).count(),
            )
        )
    if cfg.sum:
        total = qs.aggregate(t=Sum(cfg.sum[0]))["t"] or 0
        if len(cfg.sum) > 2 and cfg.sum[2] == "money":
            total = "{:,}".format(total)
        stats.append((cfg.sum[1], total))
    return stats


def _cells(obj, columns):
    return [cell(obj, c[1], c[2] if len(c) > 2 else None) for c in columns]


@login_required
def reg_list(request, key):
    cfg = _config(key)
    user = request.user
    blocked = _guard(request, cfg)
    if blocked:
        return blocked

    qs = cfg.queryset()
    q = request.GET.get("q", "").strip()
    if q and cfg.search:
        cond = Q()
        for lookup in cfg.search:
            cond |= Q(**{lookup: q})
        qs = qs.filter(cond)
    sub = _int(request.GET.get("sub_county"))
    if sub and cfg.sub_county_path:
        qs = qs.filter(**{cfg.sub_county_path: sub})
    status = request.GET.get("status", "")
    if status and cfg.status_field:
        qs = qs.filter(**{cfg.status_field: status})

    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    status_choices = []
    if cfg.status_field:
        status_choices = cfg.status_choices or cfg.model._meta.get_field(
            cfg.status_field
        ).choices
    rows = [
        {"url": reverse("reg_detail", args=[key, o.pk]), "cells": _cells(o, cfg.columns)}
        for o in page
    ]
    return render(
        request,
        "core/reg_list.html",
        {
            "cfg": cfg,
            "headers": [c[0] for c in cfg.columns],
            "rows": rows,
            "page": page,
            "stats": _stats(cfg, qs),
            "q": q,
            "sub_county_id": sub,
            "status": status,
            "status_choices": status_choices,
            "sub_counties": SubCounty.objects.order_by("name"),
            "params": params.urlencode(),
            "can_add": can_add(user),
            "kind_label": KIND_LABELS.get(cfg.kind, ""),
        },
    )


@login_required
def reg_new(request, key):
    cfg = _config(key)
    user = request.user
    blocked = _guard(request, cfg)
    if blocked:
        return blocked
    if not can_add(user):
        return redirect(_list_url(key))

    initial = {k: v for k, v in cfg.preset.items() if k in cfg.fields}
    field, parent = request.GET.get("f", ""), request.GET.get("p", "")
    if field in cfg.fields and parent.isdigit():
        initial[field] = int(parent)
    form = build_form(cfg)(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if has_field(cfg.model, "registered_by"):
            obj.registered_by = user
        for k, v in cfg.preset.items():
            setattr(obj, k, v)
        obj.save()
        return redirect("reg_detail", key=key, pk=obj.pk)
    return render(
        request,
        "core/reg_form.html",
        {
            "cfg": cfg,
            "form": form,
            "title": "New " + cfg.singular,
            "cancel": _list_url(key),
        },
    )


@login_required
def reg_edit(request, key, pk):
    cfg = _config(key)
    user = request.user
    blocked = _guard(request, cfg)
    if blocked:
        return blocked
    obj = get_object_or_404(cfg.queryset(), pk=pk)
    if not can_edit(user, obj):
        return redirect("reg_detail", key=key, pk=pk)
    form = build_form(cfg)(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("reg_detail", key=key, pk=pk)
    return render(
        request,
        "core/reg_form.html",
        {
            "cfg": cfg,
            "form": form,
            "title": "Edit %s" % cfg.singular,
            "cancel": reverse("reg_detail", args=[key, pk]),
        },
    )


def _detail_rows(cfg, obj):
    rows = []
    if getattr(obj, "code", None):
        rows.append(("ID", obj.code))
    for name in cfg.fields:
        field = cfg.model._meta.get_field(name)
        label = str(field.verbose_name)
        label = label[:1].upper() + label[1:]
        if field.choices:
            value = getattr(obj, "get_%s_display" % name)()
        else:
            value = getattr(obj, name)
        if isinstance(value, bool):
            value = "Yes" if value else "No"
        elif value in (None, ""):
            value = "-"
        rows.append((label, value))
    if has_field(cfg.model, "registered_by"):
        user = obj.registered_by
        rows.append(("Registered by", user.get_full_name() or user.username))
    if has_field(cfg.model, "created_at"):
        rows.append(("Registered on", obj.created_at.date()))
    return rows


@login_required
def reg_detail(request, key, pk):
    cfg = _config(key)
    user = request.user
    blocked = _guard(request, cfg)
    if blocked:
        return blocked
    obj = get_object_or_404(cfg.queryset(), pk=pk)

    sections = []
    for ch in cfg.children:
        child = CONFIGS[ch["key"]]
        if not can_view(user, child):
            continue
        base = child.queryset().filter(**{ch["fk"]: obj})
        rows = [
            {
                "url": reverse("reg_detail", args=[child.key, o.pk]),
                "cells": _cells(o, child.columns),
            }
            for o in base[:20]
        ]
        add = None
        if can_add(user):
            add = reverse("reg_new", args=[child.key]) + "?f=%s&p=%s" % (ch["fk"], obj.pk)
        sections.append(
            {
                "title": ch["title"],
                "headers": [c[0] for c in child.columns],
                "rows": rows,
                "total": base.count(),
                "add": add,
            }
        )

    dups = []
    can_merge = user.is_superuser or user.role in ("admin", "dpo")
    if cfg.model is Farmer:
        cond = Q(name__iexact=obj.name, parish=obj.parish)
        if obj.phone:
            cond |= Q(phone=obj.phone)
        dups = list(
            Farmer.objects.exclude(pk=obj.pk)
            .exclude(status="merged")
            .filter(cond)
            .select_related("parish")[:10]
        )

    return render(
        request,
        "core/reg_detail.html",
        {
            "cfg": cfg,
            "obj": obj,
            "title": "%s: %s" % (cfg.singular.capitalize(), obj),
            "rows": _detail_rows(cfg, obj),
            "sections": sections,
            "editable": can_edit(user, obj),
            "dups": dups,
            "can_merge": can_merge,
            "back": _list_url(key),
        },
    )


@login_required
@require_POST
def reg_merge(request, key, pk, dup):
    cfg = _config(key)
    user = request.user
    if cfg.model is not Farmer:
        raise Http404
    if not (user.is_superuser or user.role in ("admin", "dpo")):
        messages.error(request, "Only the administrator or DPO can merge records.")
        return redirect("reg_detail", key=key, pk=pk)
    keeper = get_object_or_404(Farmer, pk=pk)
    dupe = get_object_or_404(Farmer, pk=dup)
    if keeper.pk == dupe.pk:
        return redirect("reg_detail", key=key, pk=pk)
    with transaction.atomic():
        FishPond.objects.filter(owner=dupe).update(owner=keeper)
        CageFarm.objects.filter(owner=dupe).update(owner=keeper); dupe.activities.update(farmer=keeper)
        for flag in ("grows_crops", "keeps_livestock", "fish_farming", "youth", "pwd"):
            if getattr(dupe, flag) and not getattr(keeper, flag):
                setattr(keeper, flag, True)
        if not keeper.phone and dupe.phone:
            keeper.phone = dupe.phone
        if not keeper.household_id and dupe.household_id:
            keeper.household = dupe.household
        keeper.save()
        dupe.status = "merged"
        dupe.merged_into = keeper
        dupe.save()
    messages.info(request, "%s was merged into this record." % dupe.name)
    return redirect("reg_detail", key=key, pk=keeper.pk)