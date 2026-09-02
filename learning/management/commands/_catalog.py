"""Shared safety helpers for the built-in catalogue seed commands."""

from __future__ import annotations

from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.db.models import Case, IntegerField, Value, When

from learning.models import Assignment, AssignmentCohort, Cohort


def ensure_cohort_track(cohort: Cohort, expected_track: str) -> None:
    """Validate and, when safe, label a legacy cohort.

    A blank track is a supported legacy state.  It can be repaired only when
    every assignment already linked to the cohort uses the expected language;
    a mixed or incompatible catalogue is rejected instead of being relabelled
    in a way that could expose another itinerary to students.
    """

    if expected_track not in Cohort.Track.values:
        raise CommandError(f"Itinerario de catálogo desconocido: {expected_track!r}.")

    if cohort.track and cohort.track != expected_track:
        raise CommandError(
            f"El grupo {cohort.name!r} ya pertenece al itinerario "
            f"{cohort.get_track_display()}; no se ha cambiado silenciosamente."
        )

    existing_languages = set(
        AssignmentCohort.objects.filter(cohort=cohort)
        .values_list("assignment__activity_version__language", flat=True)
    )
    if existing_languages and existing_languages != {expected_track}:
        raise CommandError(
            f"El grupo {cohort.name!r} contiene asignaciones de otros itinerarios; "
            f"no se ha etiquetado silenciosamente como {dict(Cohort.Track.choices).get(expected_track, expected_track)}."
        )

    if not cohort.track:
        cohort.track = expected_track
        cohort.save(update_fields=["track"])


def get_or_create_catalog_assignment(*, activity, version, defaults):
    """Return a deterministic assignment for an activity/version identity.

    The original schema does not make ``(activity, activity_version)`` unique,
    so imported legacy data can contain duplicates.  ``QuerySet.get_or_create``
    would raise ``MultipleObjectsReturned`` there; selecting by a stable
    status/creation/id order keeps bootstrap repeatable without merging a
    different activity or version.
    """

    status_order = Case(
        When(status=Assignment.Status.PUBLISHED, then=Value(0)),
        When(status=Assignment.Status.CLOSED, then=Value(1)),
        When(status=Assignment.Status.DRAFT, then=Value(2)),
        When(status=Assignment.Status.ARCHIVED, then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )
    existing = (
        Assignment.objects.filter(activity=activity, activity_version=version)
        .order_by(status_order, "created_at", "id")
        .first()
    )
    if existing is not None:
        return existing, False

    try:
        # Isolate a possible race in a savepoint.  Catching IntegrityError
        # directly inside the command's outer atomic block would otherwise
        # leave that transaction unusable for the deterministic re-query.
        with transaction.atomic():
            assignment = Assignment.objects.create(
                activity=activity,
                activity_version=version,
                **defaults,
            )
        return assignment, True
    except IntegrityError:
        # This is mostly defensive for deployments where a future migration
        # adds an identity constraint or two bootstrap workers race each other.
        existing = (
            Assignment.objects.filter(activity=activity, activity_version=version)
            .order_by(status_order, "created_at", "id")
            .first()
        )
        if existing is None:
            raise
        return existing, False
