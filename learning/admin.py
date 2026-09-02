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

    def save_model(self, request, obj, form, change):
        # Keep the DSL and per-version test limit enforced even if an admin
        # integration saves an object without going through the form.
        obj.full_clean()
        super().save_model(request, obj, form, change)

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


class ReadOnlyAcademicAdmin(admin.ModelAdmin):
    """Expose academic links for inspection without bypassing domain services."""

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Enrollment)
class EnrollmentAdmin(ReadOnlyAcademicAdmin):
    list_display = ("student", "cohort", "active", "enrolled_at")
    list_filter = ("active", "cohort__track", "cohort__academic_year")
    search_fields = ("student__username", "student__display_name", "cohort__name")


@admin.register(AssignmentCohort)
class AssignmentCohortAdmin(ReadOnlyAcademicAdmin):
    list_display = ("assignment", "cohort", "assigned_at")
    list_filter = ("cohort__track", "cohort__academic_year", "assignment__status")
    search_fields = ("assignment__activity__title", "cohort__name")


admin.site.register(
    [
        AcademicYear,
        Cohort,
        TeachingAssignment,
        Course,
        Module,
        Activity,
        Rubric,
        RubricCriterion,
        Assignment,
        Draft,
    ]
)
