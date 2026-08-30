from django.contrib import admin

from .models import (
    AuditEvent,
    GradeCalculation,
    GradeOverride,
    Submission,
    SubmissionFile,
    TestResult,
    TestRun,
)


class ImmutableEvidenceAdmin(admin.ModelAdmin):
    """Expose academic evidence for inspection, never for in-place editing."""

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Submission)
class SubmissionAdmin(ImmutableEvidenceAdmin):
    list_display = ("id", "student", "assignment", "attempt_number", "status", "submitted_at", "auto_score")
    list_filter = ("status", "is_late")


admin.site.register([SubmissionFile, TestRun, TestResult, GradeCalculation, GradeOverride, AuditEvent], ImmutableEvidenceAdmin)
