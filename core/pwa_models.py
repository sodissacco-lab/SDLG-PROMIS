from django.db import models


class OfflineSync(models.Model):
    """Remembers which phone-made record became which Activity, so a record
    that is sent twice (weak signal, retry) is never saved twice."""

    client_id = models.CharField(max_length=64, unique=True)
    activity = models.ForeignKey(
        "core.Activity", on_delete=models.CASCADE, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.client_id
