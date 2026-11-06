import io
import uuid

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

MAX_PHOTOS = 6
MAX_UPLOAD_MB = 12
MAX_SIDE = 1600


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def stamp_lines(activity, user):
    place = str(activity.sub_county) if activity.sub_county else "Location not set"
    if activity.parish:
        place += ", " + activity.parish.name
    now = timezone.localtime()
    lines = [
        "%s | %s" % (activity.activity_type, now.strftime("%d/%m/%Y %H:%M")),
        "%s | %s" % (user.get_full_name() or user.username, place),
    ]
    if activity.latitude is not None and activity.longitude is not None:
        lines.append("GPS %s, %s" % (activity.latitude, activity.longitude))
    return lines


def process_image(uploaded, lines):
    if uploaded.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError("%s is larger than %d MB." % (uploaded.name, MAX_UPLOAD_MB))
    try:
        img = Image.open(uploaded)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError("%s is not a valid image." % uploaded.name)

    img.thumbnail((MAX_SIDE, MAX_SIDE))
    draw = ImageDraw.Draw(img, "RGBA")
    size = max(14, img.width // 45)
    font = _font(size)
    pad = size // 2
    line_h = size + pad // 2
    band = line_h * len(lines) + pad
    draw.rectangle([0, img.height - band, img.width, img.height], fill=(0, 0, 0, 150))
    y = img.height - band + pad // 2
    for text in lines:
        draw.text((pad, y), text, fill=(255, 255, 255, 255), font=font)
        y += line_h

    out = io.BytesIO()
    img.save(out, "JPEG", quality=80, optimize=True)
    return ContentFile(out.getvalue(), name="%s.jpg" % uuid.uuid4().hex)


def save_photos(activity, user, files):
    from .photo_models import ActivityPhoto

    errors = []
    room = MAX_PHOTOS - activity.photos.count()
    lines = stamp_lines(activity, user)
    for f in files:
        if room <= 0:
            errors.append("Only %d photos are allowed per activity." % MAX_PHOTOS)
            break
        try:
            content = process_image(f, lines)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        ActivityPhoto.objects.create(activity=activity, image=content, uploaded_by=user)
        room -= 1
    return errors