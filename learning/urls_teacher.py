from django.urls import path

from .views import teacher_dashboard, teacher_export, teacher_review

urlpatterns = [
    path("dashboard/", teacher_dashboard, name="teacher_dashboard"),
    path("review/<uuid:submission_id>/", teacher_review, name="teacher_review"),
    path("exports/", teacher_export, name="teacher_export"),
]
