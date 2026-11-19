"""E-mail alerts when an entry changes hands.

returned -> the officer who wrote it, straight away (they need to fix it)
submitted -> NOT one e-mail per entry; reviewers get one morning digest (send_review_digests)
Sent in the background so saving is never slowed down, and never raises.
"""
import logging
import threading

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Activity

log = logging.getLogger(__name__)


def _name(user):
    return user.get_full_name() or user.username


def _reviewers(activity):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    officer = activity.officer
    sup = getattr(officer, "supervisor", None)
    if sup and sup.is_active and sup.email:
        return [sup.email]
    heads = User.objects.filter(
        role="head", department_id=activity.department_id, is_active=True
    ).exclude(pk=officer.pk).exclude(email="")
    emails = list(heads.values_list("email", flat=True))
    if not emails:
        emails = list(
            User.objects.filter(role="dpo", is_active=True).exclude(email="").exclude(pk=officer.pk)
            .values_list("email", flat=True)
        )
    return emails


def _send(to, subject, text):
    from .mailer import send_email

    def run():
        try:
            send_email(to, subject, text)
        except Exception:  # an alert must never break saving
            log.exception("Alert e-mail failed")

    threading.Thread(target=run, daemon=True).start()


def _link(activity):
    from .report_jobs import site_url

    return "%s/activity/%s/" % (site_url(), activity.pk)


@receiver(pre_save, sender=Activity)
def _remember_status(sender, instance, **kwargs):
    old = None
    if instance.pk:
        old = (
            Activity.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        )
    instance._old_status = old
    if instance.status == "submitted":
        try:
            from django.utils import timezone

            from .schedule_models import ReportSettings

            if not ReportSettings.get().require_approval:
                instance.status = "approved"
                instance.reviewed_at = timezone.now()
                if not instance.review_comment:
                    instance.review_comment = "Approved automatically (approval is switched off)."
        except Exception:
            log.exception("Could not check the approval setting")


@receiver(post_save, sender=Activity)
def _status_changed(sender, instance, **kwargs):
    old = getattr(instance, "_old_status", None)
    new = instance.status
    if old == new or kwargs.get("raw"):
        return
    try:
        what = instance.activity_label
        if new == "returned" and instance.officer.email:
            subject = "Your entry was returned for correction: %s" % what
            body = "Your entry (%s, %s) was returned for correction." % (what, instance.date.strftime("%d %b %Y"))
            if instance.review_comment:
                body += "\n\nReason: %s" % instance.review_comment
            _send(instance.officer.email, subject, body + "\n\nOpen it: %s" % _link(instance))
    except Exception:
        log.exception("Could not prepare alert e-mail")


def send_review_digests():
    """One e-mail per reviewer listing what is waiting for them. Called by the daily timer."""
    from collections import Counter

    from django.contrib.auth import get_user_model
    from django.db.models import Q

    from .report_jobs import site_url
    from .views import reviewable_activities

    User = get_user_model()
    people = User.objects.filter(is_active=True).exclude(email="").filter(
        Q(role__in=("admin", "dpo", "head")) | Q(reports__isnull=False)
    ).distinct()
    sent = 0
    for person in people:
        waiting = reviewable_activities(person).select_related("officer")
        count = Counter(_name(a.officer) for a in waiting)
        total = sum(count.values())
        if not total:
            continue
        lines = ["%s: %d" % (n, c) for n, c in sorted(count.items())]
        body = (
            "%d entr%s waiting for your review:\n\n%s\n\nOpen the review queue: %s/review/"
            % (total, "y is" if total == 1 else "ies are", "\n".join(lines), site_url())
        )
        _send(person.email, "%d entr%s waiting for your review" % (total, "y" if total == 1 else "ies"), body)
        sent += 1
    return "%d digests" % sent
