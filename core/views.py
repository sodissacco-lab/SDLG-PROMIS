from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .activity_types import allowed_types
from .forms import ActivityForm
from .models import Activity, Department
from .photos import save_photos


def visible_activities(user):
    qs = Activity.objects.all()
    if user.is_superuser or user.role in ("admin", "dpo", "viewer"):
        return qs
    if user.role == "head" and user.department_id:
        return qs.filter(department=user.department)
    return _own_or_subcounty(user, qs)


def reviewable_activities(user):
    qs = Activity.objects.filter(status="submitted")
    if user.is_superuser or user.role == "admin":
        return qs
    if user.role == "dpo":
        return qs.exclude(officer=user)
    if user.role == "head" and user.department_id:
        return qs.filter(department=user.department).exclude(officer=user)
    return qs.none()


def is_reviewer(user):
    return user.is_superuser or user.role in ("admin", "dpo", "head")


def types_by_department():
    return {str(d.id): allowed_types(d.name) for d in Department.objects.all()}


@login_required
def dashboard(request):
    today = timezone.localdate()
    qs = visible_activities(request.user)
    month = qs.filter(date__year=today.year, date__month=today.month)
    totals = month.aggregate(m=Sum("male"), f=Sum("female"))
    context = {
        "month_name": today.strftime("%B %Y"),
        "activity_count": month.count(),
        "reached": (totals["m"] or 0) + (totals["f"] or 0),
        "by_department": month.values("department__name")
        .annotate(n=Count("id"))
        .order_by("-n"),
        "recent": qs.select_related("department", "sub_county")[:5],
        "is_reviewer": is_reviewer(request.user),
        "pending_count": reviewable_activities(request.user).count(),
    }
    return render(request, "core/dashboard.html", context)


@login_required
def activity_new(request):
    if request.method == "POST":
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.officer = request.user
            if request.POST.get("action") == "submit":
                activity.status = "submitted"
            else:
                activity.status = "draft"
            activity.save()
            for error in save_photos(
                activity, request.user, request.FILES.getlist("photos")
            ):
                messages.error(request, error)
            return redirect("activity_list")
    else:
        form = ActivityForm(
            initial={
                "date": timezone.localdate(),
                "department": request.GET.get("department")
                or request.user.department_id,
            }
        )
    return render(
        request,
        "core/activity_form.html",
        {"form": form, "types_by_department": types_by_department()},
    )


@login_required
def activity_list(request):
    mine = Activity.objects.filter(officer=request.user)
    counts = dict(mine.order_by().values_list("status").annotate(n=Count("id")))
    current = request.GET.get("status", "")
    qs = mine.select_related("department", "sub_county", "parish")
    if current in dict(Activity.STATUS):
        qs = qs.filter(status=current)
    else:
        current = ""
    statuses = [
        {"value": value, "label": label, "count": counts.get(value, 0)}
        for value, label in Activity.STATUS
    ]
    return render(
        request,
        "core/activity_list.html",
        {
            "activities": qs,
            "statuses": statuses,
            "current": current,
            "total": sum(counts.values()),
        },
    )


@login_required
def activity_edit(request, pk):
    activity = get_object_or_404(Activity, pk=pk, officer=request.user)
    if activity.status not in ("draft", "returned"):
        return redirect("activity_detail", pk=pk)
    if request.method == "POST":
        form = ActivityForm(request.POST, instance=activity)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.POST.get("action") == "submit":
                obj.status = "submitted"
            else:
                obj.status = "draft"
            obj.save()
            for error in save_photos(obj, request.user, request.FILES.getlist("photos")):
                messages.error(request, error)
            return redirect("activity_list")
    else:
        form = ActivityForm(instance=activity)
    return render(
        request,
        "core/activity_form.html",
        {
            "form": form,
            "activity": activity,
            "types_by_department": types_by_department(),
            "title": "Edit activity",
        },
    )


@login_required
def activity_detail(request, pk):
    activity = get_object_or_404(visible_activities(request.user), pk=pk)
    can_review = (
        activity.status == "submitted"
        and reviewable_activities(request.user).filter(pk=activity.pk).exists()
    )
    return render(
        request,
        "core/activity_detail.html",
        {"activity": activity, "can_review": can_review},
    )


@login_required
def review_queue(request):
    qs = reviewable_activities(request.user).select_related(
        "department", "sub_county", "parish", "officer"
    )
    return render(request, "core/review_queue.html", {"activities": qs})


@login_required
@require_POST
def activity_review(request, pk):
    activity = get_object_or_404(reviewable_activities(request.user), pk=pk)
    decision = request.POST.get("decision")
    comment = request.POST.get("comment", "").strip()
    if decision == "approve":
        activity.status = "approved"
    elif decision == "return":
        if not comment:
            messages.error(request, "Please say what needs to be corrected.")
            return redirect("activity_detail", pk=pk)
        activity.status = "returned"
    else:
        return redirect("activity_detail", pk=pk)
    activity.review_comment = comment
    activity.reviewed_by = request.user
    activity.reviewed_at = timezone.now()
    activity.save()
    return redirect("review_queue")
def _own_or_subcounty(user, qs):
    if user.role == "subcounty" and user.sub_county:
        from django.db.models import Q
        return qs.filter(
            Q(sub_county__name__iexact=user.sub_county.strip()) | Q(officer=user)
        )
    return qs.filter(officer=user)
