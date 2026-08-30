import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from learning.models import ActivityVersion, Assignment


class Submission(models.Model):
    """Immutable evidence of one explicit student submission.

    The application never edits this row after creation.  Regrading creates a
    new TestRun and GradeCalculation instead, preserving the original evidence
    and the activity version used by the student.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", "Recibida"
        PROCESSING = "processing", "Procesando"
        GRADED = "graded", "Corregida"
        INFRA_ERROR = "infra_error", "Error del corrector"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT, related_name="submissions")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT, related_name="submissions")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submissions")
    attempt_number = models.PositiveIntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    is_late = models.BooleanField(default=False)
    auto_score = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True, validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("10"))])
    feedback = models.TextField(blank=True)
    files_digest = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("student", "assignment", "attempt_number")
        constraints = [models.UniqueConstraint(fields=("assignment", "student", "attempt_number"), name="uniq_submission_attempt")]
        indexes = [models.Index(fields=("assignment", "student", "-submitted_at"))]

    def clean(self):
        if self.assignment_id and self.activity_version_id and self.assignment.activity_version_id != self.activity_version_id:
            raise ValidationError("Una entrega debe conservar la versión fijada por la asignación.")
        if self.student_id and self.student.role != "student":
            raise ValidationError("Solo un alumno puede entregar una actividad.")

    def save(self, *args, **kwargs):
        if not self._state.adding and not kwargs.pop("_creating_regrade", False):
            raise ValidationError("Las entregas son inmutables; crea un nuevo cálculo de nota.")
        super().save(*args, **kwargs)


class SubmissionFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT, related_name="files")
    path = models.CharField(max_length=80)
    content = models.TextField()
    size_bytes = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("submission", "path"), name="uniq_submission_file")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Los archivos de una entrega son inmutables.")
        super().save(*args, **kwargs)


class TestRun(models.Model):
    class Status(models.TextChoices):
        PASSED = "passed", "Completada"
        FAILED = "failed", "Con fallos"
        INFRA_ERROR = "infra_error", "Error del corrector"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT, related_name="test_runs")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT, related_name="test_runs")
    evaluator_version = models.CharField(max_length=30, default="static-v1")
    status = models.CharField(max_length=20, choices=Status.choices)
    passed_points = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("0"))
    total_points = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("0"))
    score = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ("-started_at",)


class TestResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test_run = models.ForeignKey(TestRun, on_delete=models.PROTECT, related_name="results")
    test_case_id = models.UUIDField(null=True, blank=True)
    name = models.CharField(max_length=160)
    type = models.CharField(max_length=80)
    passed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="failed")
    points = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("0"))
    earned_points = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("0"))
    feedback = models.TextField(blank=True)
    detail = models.JSONField(default=dict, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("position", "name")


class GradeCalculation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        READY = "ready", "Lista"
        PUBLISHED = "published", "Publicada"
        RETRACTED = "retracted", "Retirada"
        PENDING_REVIEW = "pending_review", "Pendiente de revisión"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT, related_name="grade_calculations")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT, related_name="grade_calculations")
    auto_score = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    manual_score = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    final_score = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    auto_weight = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("1.0000"))
    manual_weight = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0000"))
    formula_version = models.CharField(max_length=30, default="grade-v1")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    breakdown = models.JSONField(default=dict, blank=True)
    teacher_comment = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="grade_calculations_made")
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("submission", "status"))]


class GradeOverride(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT, related_name="grade_overrides")
    previous_score = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    new_score = models.DecimalField(max_digits=8, decimal_places=5, validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("10"))])
    reason = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="grade_overrides_made")
    created_at = models.DateTimeField(auto_now_add=True)


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="audit_events")
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
