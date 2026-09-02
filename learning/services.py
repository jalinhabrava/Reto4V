"""Domain services for assigning students to learning itineraries.

The dashboard uses an ``Enrollment`` as the single source of truth for route
visibility.  Keeping the mutation here makes account creation, account edits,
imports and future admin actions share the same invariants instead of each
implementing a subtly different update sequence.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User

from .models import Assignment, AssignmentCohort, Cohort, Enrollment


def _locked_student(student):
    if not getattr(student, "pk", None):
        raise ValidationError("La cuenta de alumno debe estar guardada antes de matricularla.")
    try:
        return type(student).objects.select_for_update().get(pk=student.pk)
    except type(student).DoesNotExist as exc:
        raise ValidationError("La cuenta de alumno ya no existe.") from exc


def _locked_cohort(cohort):
    if not getattr(cohort, "pk", None):
        raise ValidationError("Selecciona un ciclo e itinerario válido.")
    try:
        return Cohort.objects.select_for_update().select_related("academic_year").get(pk=cohort.pk)
    except Cohort.DoesNotExist as exc:
        raise ValidationError("El ciclo e itinerario seleccionado ya no existe.") from exc


@transaction.atomic
def set_student_cohort(student, cohort) -> Enrollment:
    """Set the student's one active cohort and return its enrollment.

    Existing enrollments are kept as history.  If the selected cohort was used
    before, its inactive row is reactivated; otherwise a new row is created.
    The student row is locked before the old enrollment is deactivated, while
    the conditional database constraint is the final guard against concurrent
    writers.
    """

    locked_student = _locked_student(student)
    if locked_student.role != User.Role.STUDENT:
        raise ValidationError("Solo se pueden matricular cuentas de alumno.")

    locked_cohort = _locked_cohort(cohort)
    if not locked_cohort.active:
        raise ValidationError("El grupo seleccionado está inactivo.")
    if not locked_cohort.academic_year.active:
        raise ValidationError("El curso académico seleccionado está inactivo.")
    if not locked_cohort.track:
        raise ValidationError("El grupo seleccionado todavía no tiene itinerario.")
    if locked_cohort.track not in Cohort.Track.values:
        raise ValidationError("El grupo seleccionado tiene un itinerario no válido.")
    if not Assignment.objects.filter(
        cohort_links__cohort=locked_cohort,
        status=Assignment.Status.PUBLISHED,
        activity_version__language=locked_cohort.track,
    ).exists():
        raise ValidationError(
            "El grupo seleccionado todavía no tiene un primer reto publicado para su itinerario."
        )

    enrollment = (
        Enrollment.objects.select_for_update()
        .filter(student=locked_student, cohort=locked_cohort)
        .first()
    )

    # Deactivate first when moving to another cohort, so the partial unique
    # constraint cannot be violated while an old active row still exists.
    Enrollment.objects.filter(student=locked_student, active=True).exclude(
        pk=enrollment.pk if enrollment else None
    ).update(active=False)

    if enrollment is None:
        enrollment = Enrollment.objects.create(
            student=locked_student,
            cohort=locked_cohort,
            active=True,
        )
    elif not enrollment.active:
        enrollment.active = True
        enrollment.save(update_fields=["active"])
    return enrollment


@transaction.atomic
def clear_student_enrollment(student) -> int:
    """Deactivate all current enrollments for a user and return the count.

    Historical rows remain available to teachers and administrators for audit
    purposes.  The operation is intentionally valid for a user whose role is
    being changed away from ``student``.
    """

    locked_student = _locked_student(student)
    return Enrollment.objects.filter(student=locked_student, active=True).update(active=False)


@transaction.atomic
def supersede_catalog_assignments(current_assignment: Assignment) -> dict[str, int]:
    """Publish a new catalogue version without rewriting academic evidence.

    Built-in catalogue content can improve after a centre has already used an
    older version.  An ``Assignment`` pins its version permanently, so an
    upgrade must create a new assignment.  This service copies the matching cohort
    links to that new assignment and archives only older visible assignments
    for the same activity and language.  Drafts, submissions and grades remain
    attached to the archived assignment for audit and teacher review.

    The caller still owns the explicit link to a newly requested cohort.  The
    returned counters are useful for deterministic command output and tests.
    """

    if not getattr(current_assignment, "pk", None):
        raise ValidationError("La nueva asignación de catálogo debe estar guardada.")

    try:
        current = (
            Assignment.objects.select_for_update()
            .select_related("activity_version")
            .get(pk=current_assignment.pk)
        )
    except Assignment.DoesNotExist as exc:
        raise ValidationError("La nueva asignación de catálogo ya no existe.") from exc

    # Bootstrap runs on every container start. A teacher may deliberately
    # leave the current revision as a draft; do not fail the restart or hide
    # the previously published revision in that case.
    if current.status == Assignment.Status.DRAFT:
        return {"migrated_links": 0, "archived_assignments": 0}

    version = current.activity_version
    matching_assignment_ids = AssignmentCohort.objects.filter(
        cohort__track=version.language,
    ).values("assignment_id")
    older = list(
        Assignment.objects.select_for_update()
        .filter(
            activity_id=current.activity_id,
            activity_version__language=version.language,
            activity_version__version_number__lt=version.version_number,
            id__in=matching_assignment_ids,
            status__in=(
                Assignment.Status.PUBLISHED,
                Assignment.Status.CLOSED,
                Assignment.Status.ARCHIVED,
            ),
        )
        .order_by("created_at", "id")
    )

    migrated_links = 0
    archived_assignments = 0
    now = timezone.now()
    for previous in older:
        cohort_ids = previous.cohort_links.filter(
            cohort__track=version.language,
        ).values_list("cohort_id", flat=True)
        for cohort_id in cohort_ids:
            _, created = AssignmentCohort.objects.get_or_create(
                assignment=current,
                cohort_id=cohort_id,
            )
            migrated_links += int(created)

        if previous.status != Assignment.Status.ARCHIVED:
            previous.status = Assignment.Status.ARCHIVED
            update_fields = ["status"]
            if previous.closed_at is None:
                previous.closed_at = now
                update_fields.append("closed_at")
            previous.save(update_fields=update_fields)
            archived_assignments += 1

    return {
        "migrated_links": migrated_links,
        "archived_assignments": archived_assignments,
    }
