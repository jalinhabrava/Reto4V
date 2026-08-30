from django.urls import path

from .views import (
    student_dashboard,
    student_submission,
    teacher_export,
    teacher_review,
    workspace_detail_api,
    workspace_draft_api,
    workspace_submit_api,
    workspace_tests_api,
)

urlpatterns = [
    path("assignments/<uuid:assignment_id>/", workspace_detail_api, name="workspace_detail_api"),
    path(
        "assignments/<uuid:assignment_id>/draft/", workspace_draft_api, name="workspace_draft_api"
    ),
    path(
        "assignments/<uuid:assignment_id>/tests/", workspace_tests_api, name="workspace_tests_api"
    ),
    path(
        "assignments/<uuid:assignment_id>/submit/",
        workspace_submit_api,
        name="workspace_submit_api",
    ),
    path(
        "workspace/assignments/<uuid:assignment_id>/",
        workspace_detail_api,
        name="workspace_detail_api_alias",
    ),
    path(
        "workspace/assignments/<uuid:assignment_id>/draft/",
        workspace_draft_api,
        name="workspace_draft_api_alias",
    ),
    path(
        "workspace/assignments/<uuid:assignment_id>/tests/",
        workspace_tests_api,
        name="workspace_tests_api_alias",
    ),
    path(
        "workspace/assignments/<uuid:assignment_id>/submit/",
        workspace_submit_api,
        name="workspace_submit_api_alias",
    ),
    path("submissions/<uuid:submission_id>/", student_submission, name="submission_detail_api"),
    path("teacher/review/<uuid:submission_id>/", teacher_review, name="teacher_review_api"),
    path("teacher/exports/", teacher_export, name="teacher_export_api"),
    path("student/dashboard/", student_dashboard, name="student_dashboard_api"),
]
