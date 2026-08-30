from django.contrib import admin

from .models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Draft,
    Enrollment,
    Module,
    Rubric,
    RubricCriterion,
    TeachingAssignment,
    TestCase,
)


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ("name", "activity_version", "type", "visibility", "points")
    list_filter = ("visibility", "type")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.activity_version.assignments.exists():
            return tuple(field.name for field in self.model._meta.fields)
        return ()

    def has_delete_permission(self, request, obj=None):
        if obj and obj.activity_version.assignments.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(ActivityVersion)
class ActivityVersionAdmin(admin.ModelAdmin):
    list_display = ("activity", "version_number", "language", "difficulty", "xp_reward", "grading_mode", "published_at")
    list_filter = ("language", "difficulty", "grading_mode")
    search_fields = ("activity__title", "instructions")


admin.site.register([AcademicYear, Cohort, Enrollment, TeachingAssignment, Course, Module, Activity, Rubric, RubricCriterion, Assignment, AssignmentCohort, Draft])
