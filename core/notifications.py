from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from .crop_vet_models import DiseaseReport, Outbreak, PestDiseaseReport
from .ent_com_models import LoanIntervention, Trap, TrapInspection, VectorIncident
from .models import Activity
from .reg_models import FishingLicence
from .templatetags.register_tags import _stale_sites
from .views import reviewable_activities, visible_activities


def _can(user, department_name):
    if user.is_superuser or user.role in ("admin", "dpo", "viewer"):
        return True
    return user.department_id is not None and user.department.name == department_name


def collect(user):
    today = timezone.localdate()
    items = []

    def add(group, level, text, url=None):
        items.append({"group": group, "level": level, "text": text, "url": url})

    returned = Activity.objects.filter(officer=user, status="returned").count()
    if returned:
        add("Your work", "warning", "%d of your entries were returned for correction." % returned,
            reverse("activity_list") + "?status=returned")
    old = timezone.now() - timedelta(days=3)
    drafts = Activity.objects.filter(officer=user, status="draft", created_at__lt=old).count()
    if drafts:
        add("Your work", "info", "%d drafts have been waiting more than 3 days. Finish and submit them." % drafts,
            reverse("activity_list") + "?status=draft")

    if user.is_superuser or user.role in ("admin", "dpo", "head"):
        pending = reviewable_activities(user).count()
        if pending:
            add("Approvals", "warning", "%d entries are waiting for your review." % pending, reverse("review_queue"))

    if _can(user, "Fisheries"):
        soon = today + timedelta(days=30)
        licences = FishingLicence.objects.select_related("boat")
        for lic in licences.filter(expiry_date__gte=today, expiry_date__lte=soon).order_by("expiry_date")[:10]:
            add("Fisheries", "warning",
                "Licence %s (boat %s) expires on %s." % (lic.licence_number, lic.boat.registration_number, lic.expiry_date.strftime("%d %b %Y")),
                reverse("reg_detail", args=["fishing-licences", lic.pk]))
        expired = licences.filter(expiry_date__lt=today).count()
        if expired:
            add("Fisheries", "info", "%d licences have expired." % expired, reverse("r_fishing_licences"))
        for s in _stale_sites(today)[:10]:
            when = "last inspected %s" % s["last"].strftime("%d %b %Y") if s["last"] else "never inspected"
            add("Fisheries", "info", "%s: no inspection in the last 30 days (%s)." % (s["name"], when), s["url"])

    if _can(user, "Veterinary"):
        for o in Outbreak.objects.filter(status="active").select_related("sub_county").order_by("-start_date")[:10]:
            add("Veterinary", "urgent",
                "Active outbreak: %s in %s (%d confirmed cases)." % (o.disease, o.sub_county, o.confirmed_cases),
                reverse("reg_detail", args=["outbreak-management", o.pk]))
        confirmed = DiseaseReport.objects.filter(status="confirmed", date__year=today.year, date__month=today.month).count()
        if confirmed:
            add("Veterinary", "warning", "%d disease reports were confirmed this month." % confirmed,
                reverse("r_disease_surveillance"))

    if _can(user, "Crops"):
        since = today - timedelta(days=14)
        pests = PestDiseaseReport.objects.filter(severity="high", date__gte=since).select_related("sub_county")
        for r in pests.order_by("-date")[:10]:
            add("Crops", "warning", "High-severity %s on %s in %s (%s)." % (r.pest_or_disease, r.crop, r.sub_county, r.date.strftime("%d %b")),
                reverse("reg_detail", args=["pest-disease-surveillance", r.pk]))

    if _can(user, "Entomology"):
        cutoff = today - timedelta(days=30)
        recent = set(TrapInspection.objects.filter(date__gte=cutoff).values_list("trap_id", flat=True))
        shown = 0
        for t in Trap.objects.filter(status="active", installed_date__lte=cutoff).order_by("code"):
            if t.pk not in recent and shown < 10:
                add("Entomology", "warning", "Trap %s has not been inspected in 30 days." % t.code,
                    reverse("reg_detail", args=["trap-register", t.pk]))
                shown += 1
        for i in VectorIncident.objects.filter(status="active").select_related("sub_county")[:5]:
            add("Entomology", "warning", "Open vector incident: %s in %s." % (i.vector, i.sub_county),
                reverse("reg_detail", args=["vector-incidents", i.pk]))

    if _can(user, "Commercial"):
        for ln in LoanIntervention.objects.filter(status="overdue").order_by("-date")[:10]:
            add("Commercial", "warning", "Overdue: %s (balance UGX %s)." % (ln.description, "{:,}".format(ln.balance)),
                reverse("reg_detail", args=["loans-interventions", ln.pk]))

    if user.is_superuser or user.role in ("admin", "dpo", "head", "viewer"):
        base = visible_activities(user).filter(status="approved", date__year=today.year, date__month=today.month)
        for count, text in [
            (base.filter(latitude__isnull=True).count(), "approved activities this month have no GPS location."),
            (base.filter(parish__isnull=True).count(), "approved activities this month have no parish."),
            (base.filter(photos__isnull=True).count(), "approved activities this month have no photo."),
        ]:
            if count:
                add("Data quality", "info", "%d %s" % (count, text))

    return items