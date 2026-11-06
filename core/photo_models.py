from django.conf import settings
from django.db import models


def photo_path(instance, filename):
    return "activity_photos/%s/%s" % (
        instance.activity.date.strftime("%Y/%m"),
        filename,
    )


class ActivityPhoto(models.Model):
    activity = models.ForeignKey(
        "core.Activity", on_delete=models.CASCADE, related_name="photos"
    )
    image = models.ImageField(upload_to=photo_path)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="activity_photos",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return "Photo %s of %s" % (self.pk, self.activity)