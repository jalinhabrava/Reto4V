from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from accounts.views import dashboard_redirect, login_view, logout_view, password_change_view
from aulaweb.health import health_view
from learning.views import workspace_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", login_view, name="login"),
    path("health/", health_view, name="health"),
    path("logout/", logout_view, name="logout"),
    path("password-change/", password_change_view, name="password_change"),
    path("dashboard/", dashboard_redirect, name="dashboard"),
    path("assignments/<uuid:assignment_id>/", workspace_page, name="workspace_page_root"),
    path("", RedirectView.as_view(pattern_name="login", permanent=False)),
    path("student/", include("learning.urls_student")),
    path("teacher/", include("learning.urls_teacher")),
    path("admin-ui/", include("accounts.urls")),
    path("api/", include("learning.urls_api")),
]
