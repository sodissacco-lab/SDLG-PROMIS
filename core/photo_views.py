from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .photo_models import ActivityPhoto
from .views import visible_activities


@login_required
def photo_file(request, pk):
    photo = get_object_or_404(ActivityPhoto, pk=pk)
    if not visible_activities(request.user).filter(pk=photo.activity_id).exists():
        raise Http404
    try:
        return FileResponse(photo.image.open("rb"), content_type="image/jpeg")
    except FileNotFoundError:
        raise Http404


@login_required
@require_POST
def photo_delete(request, pk):
    photo = get_object_or_404(
        ActivityPhoto,
        pk=pk,
        activity__officer=request.user,
        activity__status__in=("draft", "returned"),
    )
    activity_id = photo.activity_id
    photo.image.delete(save=False)
    photo.delete()
    return redirect("activity_edit", pk=activity_id)