import os

from django.conf import settings

from .photo_models import ActivityPhoto


def collect_photos(qs, period, department=None, sub_county=None, limit=12, per_activity=2):
    qs = qs.filter(
        status="approved", date__gte=period["start"], date__lte=period["end"]
    )
    if department:
        qs = qs.filter(department=department)
    if sub_county:
        qs = qs.filter(sub_county=sub_county)

    photos = (
        ActivityPhoto.objects.filter(activity__in=qs.values("pk"))
        .select_related("activity", "activity__sub_county", "activity__parish")
        .order_by("activity__date", "activity_id", "id")
    )
    out = []
    counts = {}
    stats = {"total": photos.count(), "missing": 0, "bad": 0}
    collect_photos.last = stats
    root = str(settings.MEDIA_ROOT)
    n_files = 0
    if os.path.isdir(root):
        for _r, _d, fs in os.walk(root):
            n_files += len(fs)
    stats["root"] = root
    stats["root_exists"] = os.path.isdir(root)
    stats["root_files"] = n_files
    for p in photos:
        if counts.get(p.activity_id, 0) >= per_activity:
            continue
        try:
            path = p.image.path
        except ValueError:
            stats["bad"] += 1
            continue
        if not os.path.exists(path):
            stats["missing"] += 1
            stats.setdefault("example", path)
            continue
        counts[p.activity_id] = counts.get(p.activity_id, 0) + 1
        a = p.activity
        place = str(a.sub_county) if a.sub_county else ""
        if a.parish:
            place += ", " + a.parish.name
        out.append(
            {
                "path": path,
                "caption": "%s | %s | %s"
                % (a.activity_type, a.date.strftime("%d %b %Y"), place),
            }
        )
        if len(out) >= limit:
            break
    return out
