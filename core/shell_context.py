from .models import SubCounty
from .registers import build_menu, shared_menu
from .sectors import other_departments, sectors

DISTRICT_ROLES = ("admin", "dpo", "head", "viewer")


def _context_of(request):
    match = request.resolver_match
    if match is None:
        return None, None
    name = match.url_name or ""
    if name == "sector":
        return match.kwargs.get("pk"), None
    if name == "register":
        raw = request.GET.get("s", "")
        return (int(raw) if raw.isdigit() else None), match.kwargs.get("slug")
    if name.startswith("pdm_"):
        return None, "pdm-register"
    if name.startswith("r_") or name in ("reg_new", "reg_detail", "reg_edit"):
        return None, match.kwargs.get("key")
    return None, None


def _has_active(entries):
    for e in entries:
        if e.get("active"):
            return True
        for c in e.get("children") or []:
            if c["active"]:
                return True
    return False


def shell(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    from .views import reviewable_activities

    all_sectors = sectors()
    others = other_departments()
    if user.is_superuser or user.role in ("admin", "dpo", "viewer"):
        my_sectors, my_others = all_sectors, others
    else:
        my_sectors = [d for d in all_sectors if d.pk == user.department_id]
        my_others = [d for d in others if d.pk == user.department_id]

    my_subcounty = None
    if user.role == "subcounty" and user.sub_county:
        my_subcounty = SubCounty.objects.filter(
            name__iexact=user.sub_county.strip()
        ).first()

    open_pk, current_slug = _context_of(request)

    def menus(depts):
        out = []
        for d in depts:
            entries = build_menu(d.name, d.pk, current_slug)
            out.append(
                {
                    "dept": d,
                    "open": d.pk == open_pk or _has_active(entries),
                    "entries": entries,
                }
            )
        return out

    return {
        "nav_menus": menus(my_sectors),
        "nav_dept_menus": menus(my_others),
        "nav_shared": shared_menu(current_slug),
        "nav_cur_slug": current_slug,
        "nav_pending": reviewable_activities(user).count(), "nav_alerts": reviewable_activities(user).count() + user.activities.filter(status="returned").count(),
        "nav_reviewer": user.is_superuser or user.role in ("admin", "dpo", "head"),
        "nav_district": user.is_superuser or user.role in DISTRICT_ROLES,
        "nav_subcounties": user.is_superuser or user.role in DISTRICT_ROLES,
        "nav_my_subcounty": my_subcounty,
        "nav_admin": user.is_staff,
    }