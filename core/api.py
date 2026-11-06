from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Parish


@login_required
def parishes(request):
    sub_county = request.GET.get("sub_county")
    data = []
    if sub_county and sub_county.isdigit():
        data = list(
            Parish.objects.filter(sub_county_id=sub_county)
            .order_by("name")
            .values("id", "name")
        )
    return JsonResponse({"parishes": data})