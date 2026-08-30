from django.urls import path

from .views import student_dashboard, student_submission, workspace_page

urlpatterns = [
    path("dashboard/", student_dashboard, name="student_dashboard"),
    path("assignments/<uuid:assignment_id>/", workspace_page, name="student_workspace"),
    path("submissions/<uuid:submission_id>/", student_submission, name="student_submission"),
]
