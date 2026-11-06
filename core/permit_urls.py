from django.urls import path

from . import permit_views as v

urlpatterns = [
    path("permits/", v.permit_list, name="permit_list"),
    path("permits/new/<slug:kind>/", v.permit_new, name="permit_new"),
    path("permits/<int:pk>/", v.permit_detail, name="permit_detail"),
    path("permits/<int:pk>/edit/", v.permit_edit, name="permit_edit"),
    path("permits/<int:pk>/print/", v.permit_pdf, name="permit_pdf"),
    path("permits/<int:pk>/action/", v.permit_action, name="permit_action"),
    path("verify/<str:code>/", v.permit_verify, name="permit_verify"),
]
