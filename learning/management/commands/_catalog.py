"""Shared safety helpers for the built-in catalogue seed commands."""

from __future__ import annotations

from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.db.models import Case, IntegerField, Value, When

from learning.models import Activity, Assignment, AssignmentCohort, Cohort


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
    # Bootstrap normally runs in one container, but locking the activity also
    # makes two concurrent starts deterministic on PostgreSQL even though the
    # legacy schema does not yet enforce assignment identity as a constraint.
    with transaction.atomic():
        Activity.objects.select_for_update().only("pk").get(pk=activity.pk)
        existing = (
            Assignment.objects.filter(activity=activity, activity_version=version)
            .order_by(status_order, "created_at", "id")
            .first()
        )
        if existing is not None:
            return existing, False

        try:
            # Keep a savepoint for deployments where a future migration adds
            # an identity constraint independently of this compatibility code.
            with transaction.atomic():
                assignment = Assignment.objects.create(
                    activity=activity,
                    activity_version=version,
                    **defaults,
                )
            return assignment, True
        except IntegrityError:
            existing = (
                Assignment.objects.filter(activity=activity, activity_version=version)
                .order_by(status_order, "created_at", "id")
                .first()
            )
            if existing is None:
                raise
            return existing, False


def get_or_create_catalog_revision_assignment(*, activity, version, cohort, defaults):
    """Create the active assignment for a newer built-in catalogue revision.

    A revision is a new immutable ``ActivityVersion`` and therefore needs a
    new assignment.  Relevant teacher settings from the latest older
    assignment are retained, all matching cohort links are migrated by
    the domain service, and old assignments are archived without touching
    their drafts, submissions or grades.
    """

    if version.activity_id != activity.pk:
        raise CommandError("La versión del catálogo no pertenece a la actividad indicada.")
    if not cohort.track or cohort.track != version.language:
        raise CommandError("El itinerario del grupo no coincide con la revisión del catálogo.")

    previous = (
        Assignment.objects.filter(
            activity=activity,
            activity_version__language=version.language,
            activity_version__version_number__lt=version.version_number,
            cohort_links__cohort__track=version.language,
        )
        .order_by("-activity_version__version_number", "-created_at", "-id")
        .first()
    )
    create_defaults = dict(defaults)
    if previous is not None:
        # Keep a title explicitly customised by a teacher.  A blank legacy
        # override must not erase the clearer title supplied by the new
        # catalogue revision.
        if previous.title_override:
            create_defaults["title_override"] = previous.title_override
        for field in (
            "opens_at",
            "due_at",
            "max_attempts",
            "attempt_policy",
            "weight",
            "allow_late",
        ):
            create_defaults[field] = getattr(previous, field)

    assignment, created = get_or_create_catalog_assignment(
        activity=activity,
        version=version,
        defaults=create_defaults,
    )
    AssignmentCohort.objects.get_or_create(assignment=assignment, cohort=cohort)

    from learning.services import supersede_catalog_assignments

    upgrade = supersede_catalog_assignments(assignment)
    return assignment, created, upgrade
