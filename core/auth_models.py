from django.db import models


class LoginThrottle(models.Model):
    """Counts wrong-password attempts so guessing is slowed down."""

    key = models.CharField(max_length=120, unique=True)  # "u:<username>" or "ip:<address>"
    fails = models.PositiveIntegerField(default=0)
    window_start = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.key
