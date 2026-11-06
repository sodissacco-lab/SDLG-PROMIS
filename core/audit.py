import threading

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

_local = threading.local()
SKIP = {"auditlog"}


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None


def _user():
    user = getattr(getattr(_local, "request", None), "user", None)
    return user if user is not None and user.is_authenticated else None


def _log(user, action, model_name="", object_id="", summary=""):
    try:
        from .admin2_models import AuditLog

        AuditLog.objects.create(user=user, action=action, model_name=model_name,
                                object_id=str(object_id)[:30], summary=summary[:250])
    except Exception:
        pass


def _relevant(sender):
    meta = sender._meta
    return meta.app_label == "core" and not meta.auto_created and meta.model_name not in SKIP


@receiver(post_save)
def saved(sender, instance, created, **kwargs):
    if not _relevant(sender):
        return
    fields = kwargs.get("update_fields")
    if fields and set(fields) <= {"code", "last_login"}:
        return
    user = _user()
    if user is None:
        return
    _log(user, "created" if created else "updated", sender._meta.verbose_name, instance.pk, str(instance))


@receiver(post_delete)
def deleted(sender, instance, **kwargs):
    if not _relevant(sender):
        return
    user = _user()
    if user is None:
        return
    _log(user, "deleted", sender._meta.verbose_name, instance.pk, str(instance))


@receiver(user_logged_in)
def signed_in(sender, user, **kwargs):
    _log(user, "login", "user", user.pk, "Signed in")


@receiver(user_logged_out)
def signed_out(sender, user, **kwargs):
    if user is not None:
        _log(user, "logout", "user", user.pk, "Signed out")