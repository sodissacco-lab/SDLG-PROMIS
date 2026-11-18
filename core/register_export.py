import csv
import io
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .reg_config import CONFIGS, cell
from .reg_views import _config, _int, can_view


def _filtered(request, cfg):
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
    return qs


def _plain(value):
    if value is None:
        return ""
    if isinstance(value, (int, float, date)):
        return value
    text = str(value)
    return "" if text == "-" else text


@login_required
def register_export(request, key):
    cfg = _config(key)
    if not can_view(request.user, cfg):
        messages.error(request, "You do not have access to this register.")
        return redirect("dashboard")

    headers = [c[0] for c in cfg.columns]
    rows = [
        [_plain(cell(o, c[1], c[2] if len(c) > 2 else None)) for c in cfg.columns]
        for o in _filtered(request, cfg).iterator()
    ]
    stamp = timezone.localdate().isoformat()
    name = "%s-%s" % (key, stamp)

    if request.GET.get("format") == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(rows)
        resp = HttpResponse("﻿" + buf.getvalue(), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="%s.csv"' % name
        return resp

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = cfg.label[:31].replace("/", "-").replace("\\", "-") or "Register"
    ws.append(["Soroti District Local Government, Production Department"])
    ws.append([cfg.label + " (downloaded " + stamp + ", " + str(len(rows)) + " records)"])
    ws.append([])
    ws.append(headers)
    head_row = 4
    for cl in ws[head_row]:
        cl.font = Font(bold=True, color="FFFFFF")
        cl.fill = PatternFill("solid", fgColor="1F5C3A")
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"].font = Font(italic=True)
    for r in rows:
        ws.append(r)
    for i, h in enumerate(headers, 1):
        width = max([len(str(h))] + [len(str(r[i - 1])) for r in rows[:300]]) + 2
        ws.column_dimensions[get_column_letter(i)].width = min(max(width, 10), 45)
    ws.freeze_panes = ws.cell(row=head_row + 1, column=1)
    out = io.BytesIO()
    wb.save(out)
    resp = HttpResponse(
        out.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = 'attachment; filename="%s.xlsx"' % name
    return resp


@login_required
def downloads(request):
    groups = {}
    for key, cfg in CONFIGS.items():
        if not can_view(request.user, cfg):
            continue
        groups.setdefault(cfg.sector or "Shared registers", []).append(
            {"key": key, "label": cfg.label, "kind": cfg.kind}
        )
    ordered = sorted(groups.items(), key=lambda g: (g[0] != "Shared registers", g[0]))
    for _name, items in ordered:
        items.sort(key=lambda i: i["label"])
    return render(
        request,
        "core/downloads.html",
        {"groups": ordered, "reviewer": getattr(request.user, "role", "") in ("admin", "dpo", "head") or request.user.is_superuser},
    )
