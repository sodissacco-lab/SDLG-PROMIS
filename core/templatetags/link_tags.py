from django import template
from django.urls import reverse

from core.models import Activity
from core.views import visible_activities

register = template.Library()

LINK_FIELD = {
    "landing-sites": "landing_site",
    "fish-farmers": "farmer",
    "farmer-registry": "farmer",
    "fish-ponds": "pond",
}


@register.inclusion_tag("core/_linked_activities.html", takes_context=True)
def linked_activities(context, cfg, obj):
    field = LINK_FIELD.get(cfg.key)
    if not field:
        return {"show": False}
    user = context["request"].user
    qs = (
        visible_activities(user)
        .filter(**{field: obj}, status="approved")
        .select_related("officer")
        .order_by("-date")
    )
    last_inspection = None
    if field == "landing_site":
        last = qs.filter(activity_type="Landing site inspection").first()
        last_inspection = last.date if last else None
    return {
        "show": True,
        "label": cfg.singular,
        "items": list(qs[:10]),
        "total": qs.count(),
        "is_site": field == "landing_site",
        "last_inspection": last_inspection,
        "new_url": reverse("activity_new") + "?%s=%s" % (field, obj.pk),
    }


@register.simple_tag
def activity_links(activity):
    from django.utils.html import format_html, format_html_join

    items = []
    if activity.landing_site_id:
        items.append(("Landing site", activity.landing_site, "landing-sites", activity.landing_site_id))
    if activity.farmer_id:
        items.append(("Farmer", activity.farmer, "farmer-registry", activity.farmer_id))
    if activity.pond_id:
        items.append(("Fish pond", activity.pond, "fish-ponds", activity.pond_id))
    if not items:
        return ""
    rows = format_html_join(
        "",
        '<div class="row"><span>{}</span><span><a href="{}">{}</a></span></div>',
        ((label, reverse("reg_detail", args=[key, pk]), str(obj)) for label, obj, key, pk in items),
    )
    return format_html('<div class="card" style="margin-top:12px"><span>Related records</span>{}</div>', rows)