"""Populate the built-in learning catalogues on a fresh local installation.

This command creates only one inactive, passwordless service owner for seeded
content.  It never creates demo students or exposes credentials.  The command
is safe to run at every container start: seed commands use get-or-create and
never edit an activity version that has already been assigned.
"""

from __future__ import annotations

from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import CATALOG_SERVICE_USERNAME, User
from learning.models import AcademicYear


class Command(BaseCommand):
    help = "Precarga los itinerarios Web · SMR, Bash · ASIR y Python · DAM sin crear alumnos."

    @staticmethod
    def academic_year_name():
        today = date.today()
        start = today.year if today.month >= 9 else today.year - 1
        return f"{start}-{start + 1}"

    def _catalog_academic_year(self):
        """Return an active year without reviving an intentionally closed one.

        A centre may keep the calendar year's row for historical reporting but
        mark it inactive before the next deployment.  Bootstrap must still be
        able to start: it first reuses another active year, and if none exists
        creates a stable ``-catalogo`` fallback.  The inactive historical row
        is never modified.
        """

        current_name = self.academic_year_name()
        current = AcademicYear.objects.filter(name=current_name).first()
        if current is not None and current.active:
            return current
        if current is None:
            current, _ = AcademicYear.objects.get_or_create(
                name=current_name,
                defaults={"active": True},
            )
            if current.active:
                return current

        existing_active = AcademicYear.objects.filter(active=True).order_by("-name", "id").first()
        if existing_active is not None:
            return existing_active

        # AcademicYear.name is capped at 20 characters.  This suffix remains
        # human-readable and deterministic across restarts; if an operator has
        # archived it too, advance a small counter rather than reactivating it.
        base_name = f"{current_name}-catalogo"[:20]
        candidate_name = base_name
        counter = 2
        while True:
            candidate, _ = AcademicYear.objects.get_or_create(
                name=candidate_name,
                defaults={"active": True},
            )
            if candidate.active:
                return candidate
            suffix = f"-{counter}"
            candidate_name = f"{base_name[:20 - len(suffix)]}{suffix}"
            counter += 1

    def _catalog_owner(self):
        owner, created = User.objects.get_or_create(
            username=CATALOG_SERVICE_USERNAME,
            defaults={
                "role": User.Role.TEACHER,
                "display_name": "Propietario interno de catálogos",
                "is_active": False,
            },
        )
        if not created:
            # Never silently demote or invalidate a real account that happens
            # to use the reserved username.  An administrator can resolve the
            # collision explicitly before retrying the safe bootstrap.
            if (
                owner.role != User.Role.TEACHER
                or owner.is_active
                or owner.is_superuser
                or owner.is_staff
                or owner.has_usable_password()
            ):
                raise CommandError(
                    f"La cuenta reservada {CATALOG_SERVICE_USERNAME!r} existe pero no está "
                    "bloqueada como propietario interno; corrígela o cambia su nombre antes de precargar."
                )
            return owner

        owner.set_unusable_password()
        owner.save()
        return owner

    @transaction.atomic
    def handle(self, *args, **options):
        year = self._catalog_academic_year()

        owner = self._catalog_owner()
        # Keep these calls explicit so an operator can see the three routes in
        # logs and so each existing seed remains independently reusable.
        call_command("seed_web", owner=owner.username, cohort="1SMR", academic_year=year.name)
        call_command("seed_bash", owner=owner.username, cohort="2ASIR", academic_year=year.name)
        call_command("seed_python", owner=owner.username, cohort="2DAM", academic_year=year.name)

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogos precargados en {year.name}: 12 retos Web · SMR, "
                "12 Bash · ASIR y 12 Python · DAM."
            )
        )
        self.stdout.write("No se han creado alumnos ni contraseñas de demostración.")
