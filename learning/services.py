"""Domain services for assigning students to learning itineraries.

The dashboard uses an ``Enrollment`` as the single source of truth for route
visibility.  Keeping the mutation here makes account creation, account edits,
imports and future admin actions share the same invariants instead of each
implementing a subtly different update sequence.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User

from .models import Assignment, Cohort, Enrollment


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
