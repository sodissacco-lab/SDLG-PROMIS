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
        .defer("data")
        .order_by("activity__date", "activity_id", "id")
    )
    out = []
    counts = {}
    stats = {"total": photos.count(), "missing": 0, "bad": 0}
    collect_photos.last = stats
    for p in photos:
        if counts.get(p.activity_id, 0) >= per_activity:
            continue
        content = p.get_bytes()
        if not content:
            stats["missing"] += 1
            continue
        counts[p.activity_id] = counts.get(p.activity_id, 0) + 1
        a = p.activity
        place = str(a.sub_county) if a.sub_county else ""
        if a.parish:
            place += ", " + a.parish.name
        out.append(
            {
                "data": content,
                "caption": "%s | %s | %s"
                % (a.activity_type, a.date.strftime("%d %b %Y"), place),
            }
        )
        if len(out) >= limit:
            break
    return out
