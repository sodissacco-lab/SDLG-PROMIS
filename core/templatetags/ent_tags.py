from django import template
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from core.ent2_models import Apiary, BSFUnit, Collaboration, VerminReport

register = template.Library()


def _row(label, url_name, qs, active=None):
    today = timezone.localdate()
    return {
        "label": label,
        "url": reverse(url_name),
        "total": qs.count(),
        "new": qs.filter(created_at__year=today.year, created_at__month=today.month).count(),
        "active": qs.filter(**active).count() if active else None,
    }


def _month(qs):
    today = timezone.localdate()
    return qs.filter(date__year=today.year, date__month=today.month)


@register.inclusion_tag("core/_ent_extras.html")
def ent_extras(department):
    if department.name != "Entomology":
        return {"rows": [], "measures": []}
    active = {"status": "active"}
    vermin = _month(VerminReport.objects.all())
    rows = [
        _row("Apiaries", "r_apiaries", Apiary.objects.all(), active),
        _row("Black soldier fly units", "r_bsf_units", BSFUnit.objects.all(), active),
    ]
    measures = [
        {"label": "Hives in registered apiaries", "value": Apiary.objects.filter(status="active").aggregate(t=Sum("hives"))["t"] or 0, "color": "orange"},
        {"label": "Vermin reports this month", "value": vermin.count(), "color": "pink"},
        {"label": "High-severity vermin reports this month", "value": vermin.filter(severity="high").count(), "color": "red"},
        {"label": "Vermin controlled this month", "value": vermin.filter(controlled=True).count(), "color": "green"},
        {"label": "Collaborations this month", "value": _month(Collaboration.objects.all()).count(), "color": "purple"},
    ]
    return {"rows": rows, "measures": measures}