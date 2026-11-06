from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .notifications import collect


@login_required
def notifications(request):
    items = collect(request.user)
    groups, seen = [], {}
    for item in items:
        if item["group"] not in seen:
            seen[item["group"]] = []
            groups.append((item["group"], seen[item["group"]]))
        seen[item["group"]].append(item)
    return render(
        request,
        "core/notifications.html",
        {"groups": groups, "total": len(items)},
    )