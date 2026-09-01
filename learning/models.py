import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone


class AcademicYear(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=20, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-name",)

    def __str__(self):
        return self.name


class Cohort(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="cohorts")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=("academic_year", "name"), name="uniq_cohort_year_name")]

    def __str__(self):
        return f"{self.name} ({self.academic_year})"


class Enrollment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cohort = models.ForeignKey(Cohort, on_delete=models.PROTECT, related_name="enrollments")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="enrollments")
    active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("cohort", "student"), name="uniq_enrollment")]
        indexes = [models.Index(fields=("student", "active")), models.Index(fields=("cohort", "active"))]

    def clean(self):
        if self.student.role != "student":
            raise ValidationError("Solo se pueden matricular cuentas de alumno.")


class TeachingAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cohort = models.ForeignKey(Cohort, on_delete=models.PROTECT, related_name="teaching_assignments")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="teaching_assignments")
    active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("cohort", "teacher"), name="uniq_teaching_assignment")]

    def clean(self):
        if self.teacher.role not in {"teacher", "admin"} and not self.teacher.is_superuser:
            raise ValidationError("La cuenta debe ser de profesor o administrador.")


class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="courses_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title


class Module(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="modules")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    weight = models.PositiveIntegerField(default=100, validators=[MinValueValidator(0), MaxValueValidator(10000)])

    class Meta:
        ordering = ("course", "position", "title")
        constraints = [models.UniqueConstraint(fields=("course", "position"), name="uniq_module_position")]


class Activity(models.Model):
    class Kind(models.TextChoices):
        LESSON = "lesson", "Lección"
        CODE = "code", "Código"
        PROJECT = "project", "Proyecto"

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        PUBLISHED = "published", "Publicada"
        CLOSED = "closed", "Cerrada"
        ARCHIVED = "archived", "Archivada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.PROTECT, related_name="activities")
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CODE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="activities_created")
    current_version = models.ForeignKey("ActivityVersion", on_delete=models.PROTECT, null=True, blank=True, related_name="current_for")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("module", "title")
        constraints = [models.UniqueConstraint(fields=("module", "slug"), name="uniq_activity_module_slug")]

    def __str__(self):
        return self.title


class ActivityVersion(models.Model):
    class Language(models.TextChoices):
        WEB = "web", "HTML/CSS/JavaScript"
        BASH = "bash", "Bash"
        PYTHON = "python", "Python"

    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Inicial"
        INTERMEDIATE = "intermediate", "Intermedia"
        ADVANCED = "advanced", "Avanzada"

    class GradingMode(models.TextChoices):
        FEEDBACK_ONLY = "feedback_only", "Solo feedback"
        AUTOMATIC_STATIC = "automatic_static", "Automática estática"
        MANUAL = "manual", "Manual"
        HYBRID = "hybrid", "Híbrida"
        AUTOMATIC_SANDBOXED = "automatic_sandboxed", "Automática aislada (futura)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT, related_name="versions")
    version_number = models.PositiveIntegerField()
    language = models.CharField(max_length=20, choices=Language.choices, default=Language.WEB)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.BEGINNER)
    xp_reward = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        help_text="Experiencia máxima de la actividad; no es una calificación académica.",
    )
    hints = models.JSONField(default=list, blank=True, help_text="Pistas progresivas para el alumnado.")
    instructions = models.TextField(blank=True)
    objectives = models.JSONField(default=list, blank=True)
    learning_outcomes = models.JSONField(default=list, blank=True, help_text="Códigos RA del currículo que aborda la actividad.")
    assessment_criteria = models.JSONField(default=list, blank=True, help_text="Códigos CE del currículo que aborda la actividad.")
    professional_module_code = models.CharField(max_length=20, default="0228")
    curriculum_scope = models.CharField(max_length=80, blank=True, default="Navarra")
    curriculum_edition = models.CharField(max_length=80, blank=True, default="navarra-2025")
    # Navarra's DF 109/2024 removed the former UF units from the current
    # annex.  Keep the optional unit field for legacy content, but leave it
    # empty in new activities and cite the current official modification.
    curriculum_unit = models.CharField(max_length=80, blank=True, default="")
    curriculum_source = models.URLField(max_length=500, blank=True, default="https://www.educacion.navarra.es/documents/27590/558252/DF%2B109_2024%2Bmodificacion%2BGM.pdf/6641c899-fd0f-89e3-83f4-aa30c8224707")
    starter_files = models.JSONField(default=dict, blank=True)
    reference_solution = models.JSONField(default=dict, blank=True)
    grading_mode = models.CharField(max_length=30, choices=GradingMode.choices, default=GradingMode.FEEDBACK_ONLY)
    auto_weight = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("1.0000"), validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))])
    manual_weight = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0000"), validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="activity_versions_created")
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("activity", "-version_number")
        constraints = [models.UniqueConstraint(fields=("activity", "version_number"), name="uniq_activity_version")]

    def clean(self):
        if (self.auto_weight or Decimal("0")) + (self.manual_weight or Decimal("0")) > Decimal("1"):
            raise ValidationError("Los pesos automático y manual no pueden sumar más de 1.")
        for name, value in (("starter_files", self.starter_files), ("reference_solution", self.reference_solution)):
            if not isinstance(value, dict):
                raise ValidationError({name: "Debe ser un objeto de archivos."})
            if self.language == self.Language.BASH:
                allowed = {"bash"}
            elif self.language == self.Language.PYTHON:
                allowed = {"python"}
            else:
                allowed = {"html", "css", "javascript", "js"}
            unsupported = set(value) - allowed
            if unsupported:
                raise ValidationError(
                    {name: f"Los archivos {', '.join(sorted(unsupported))} no pertenecen al lenguaje de la versión."}
                )
            invalid_values = [key for key, content in value.items() if not isinstance(content, str)]
            if invalid_values:
                raise ValidationError({name: f"El contenido de {', '.join(invalid_values)} debe ser texto."})
        if not isinstance(self.hints, list) or any(not isinstance(hint, str) for hint in self.hints):
            raise ValidationError({"hints": "Las pistas deben ser una lista de textos."})
        if len(self.hints) > 10 or any(len(hint) > 1000 for hint in self.hints):
            raise ValidationError({"hints": "Se permiten como máximo 10 pistas de 1000 caracteres."})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            locked = ActivityVersion.objects.filter(pk=self.pk).filter(models.Q(assignments__isnull=False) | models.Q(published_at__isnull=False)).exists()
            if locked:
                raise ValidationError("Las versiones publicadas o utilizadas no se pueden modificar; crea una nueva versión.")
        super().save(*args, **kwargs)

    @property
    def files(self):
        if self.language == self.Language.BASH:
            return {"bash": self.starter_files.get("bash", "")}
        if self.language == self.Language.PYTHON:
            return {"python": self.starter_files.get("python", "")}
        return {"html": self.starter_files.get("html", ""), "css": self.starter_files.get("css", ""), "javascript": self.starter_files.get("javascript", self.starter_files.get("js", ""))}


class TestCase(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Público"
        PRIVATE = "private", "Privado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT, related_name="test_cases")
    name = models.CharField(max_length=160)
    type = models.CharField(max_length=80)
    definition = models.JSONField(default=dict)
    points = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("1.00"), validators=[MinValueValidator(Decimal("0"))])
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    feedback = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("position", "name")
        constraints = [models.UniqueConstraint(fields=("activity_version", "name"), name="uniq_test_name_version")]

    def clean(self):
        super().clean()
        from grading.evaluator import MAX_TESTS, validate_test_definition

        errors = {}
        try:
            validate_test_definition(self.type, self.definition, points=self.points)
        except (TypeError, ValueError, KeyError) as exc:
            errors["definition"] = str(exc)

        if self._state.adding and self.activity_version_id:
            existing = type(self).objects.filter(activity_version_id=self.activity_version_id).count()
            if existing >= MAX_TESTS:
                errors["activity_version"] = f"Una versión no puede tener más de {MAX_TESTS} tests."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.activity_version_id and self.activity_version.assignments.exists():
            raise ValidationError("No se pueden añadir ni modificar tests de una versión asignada; crea otra versión.")
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.activity_version_id and self.activity_version.assignments.exists():
            raise ValidationError("No se pueden eliminar tests de una versión asignada; crea otra versión.")
        return super().delete(*args, **kwargs)


@receiver(pre_delete, sender=TestCase)
def protect_assigned_test_case(sender, instance, **kwargs):
    # QuerySet.delete() does not call Model.delete(), so keep the same rule at
    # signal level for admin actions and application maintenance code.
    if instance.activity_version_id and instance.activity_version.assignments.exists():
        raise ValidationError("No se pueden eliminar tests de una versión asignada; crea otra versión.")


class Rubric(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_version = models.OneToOneField(ActivityVersion, on_delete=models.PROTECT, related_name="rubric")
    title = models.CharField(max_length=180, default="Rúbrica")


class RubricCriterion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rubric = models.ForeignKey(Rubric, on_delete=models.PROTECT, related_name="criteria")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    weight = models.PositiveIntegerField(default=1)
    position = models.PositiveIntegerField(default=0)


class Assignment(models.Model):
    class AttemptPolicy(models.TextChoices):
        BEST = "best", "Mejor"
        LATEST = "latest", "Último"
        AVERAGE = "average", "Media"
        LATEST_BEFORE_DUE = "latest_before_due", "Último antes de fecha límite"

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        PUBLISHED = "published", "Publicada"
        CLOSED = "closed", "Cerrada"
        ARCHIVED = "archived", "Archivada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT, related_name="assignments")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT, related_name="assignments")
    title_override = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    opens_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    attempt_policy = models.CharField(max_length=30, choices=AttemptPolicy.choices, default=AttemptPolicy.BEST)
    weight = models.PositiveIntegerField(default=100, validators=[MinValueValidator(0), MaxValueValidator(10000)])
    allow_late = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assignments_created")
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "due_at"))]

    def clean(self):
        if self.activity_version and self.activity and self.activity_version.activity_id != self.activity_id:
            raise ValidationError("La versión no pertenece a la actividad asignada.")
        if self.opens_at and self.due_at and self.due_at < self.opens_at:
            raise ValidationError("La fecha límite no puede ser anterior a la apertura.")

    def save(self, *args, **kwargs):
        if not self._state.adding:
            previous = Assignment.objects.filter(pk=self.pk).values_list("activity_version_id", flat=True).first()
            if previous and previous != self.activity_version_id:
                raise ValidationError("Una asignación no puede cambiar de versión; crea otra asignación.")
        super().save(*args, **kwargs)

    @property
    def title(self):
        return self.title_override or self.activity.title

    def is_open_for(self, at=None):
        at = at or timezone.now()
        if self.status != self.Status.PUBLISHED:
            return False
        if self.opens_at and at < self.opens_at:
            return False
        if self.due_at and at > self.due_at and not self.allow_late:
            return False
        return True


class AssignmentCohort(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT, related_name="cohort_links")
    cohort = models.ForeignKey(Cohort, on_delete=models.PROTECT, related_name="assignment_links")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("assignment", "cohort"), name="uniq_assignment_cohort")]
        indexes = [models.Index(fields=("cohort", "assignment"))]


class Draft(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT, related_name="drafts")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="drafts")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT, related_name="drafts")
    files = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("assignment", "student"), name="uniq_draft_student_assignment")]
        indexes = [models.Index(fields=("student", "updated_at"))]

    def clean(self):
        if self.assignment_id and self.activity_version_id and self.assignment.activity_version_id != self.activity_version_id:
            raise ValidationError("El borrador debe usar la versión fijada por la asignación.")
        if self.student_id and self.student.role != "student":
            raise ValidationError("Solo un alumno puede tener un borrador.")
