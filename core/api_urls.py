from django.urls import path

from . import api_views as v

urlpatterns = [
    path("api/login/", v.login, name="api_login"),
    path("api/me/", v.me, name="api_me"),
    path("api/bootstrap/", v.bootstrap, name="api_bootstrap"),
    path("api/sync/", v.sync, name="api_sync"),
    path("api/mine/", v.mine, name="api_mine"),
    path("api/summary/", v.summary, name="api_summary"),
    path("api/approvals/", v.approvals, name="api_approvals"),
    path("api/approvals/<int:pk>/", v.decide, name="api_decide"),
]
