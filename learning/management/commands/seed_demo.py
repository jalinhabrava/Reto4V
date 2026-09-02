"""Create a small, safe-to-repeat Programmy4V demonstration dataset."""

from __future__ import annotations

import secrets
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from learning.models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Module,
    TeachingAssignment,
    TestCase,
)
from learning.services import set_student_cohort

from ._catalog import ensure_cohort_track, get_or_create_catalog_assignment

CURRICULUM_SOURCE = "https://www.lexnavarra.navarra.es/detalle.asp?r=9129"
# This vertical slice demonstrates only the criteria evidenced by its files;
# the full Navarra RA1 remains outside the Fase 0 activity.
RA1_CRITERIA = ["RA1.b", "RA1.d", "RA1.g"]


class Command(BaseCommand):
    help = "Crea datos ficticios para probar Programmy4V (las contraseñas generadas solo se muestran una vez)."

    def add_arguments(self, parser):
        parser.add_argument("--academic-year", default=None)
        parser.add_argument("--admin-username", default="demo-admin")
        parser.add_argument("--teacher-username", default="demo-profesor")
        parser.add_argument("--student-prefix", default="demo-alumno")
        parser.add_argument("--admin-password", default=None)
        parser.add_argument("--teacher-password", default=None)
        parser.add_argument("--student-password", default=None)
        parser.add_argument("--students", type=int, default=5)

    def _credential(self, explicit):
        return explicit or secrets.token_urlsafe(18)

    def _user(self, *, username, role, display_name, password):
        user, created = User.objects.get_or_create(username=username, defaults={"role": role, "display_name": display_name})
        if created:
            user.set_password(password)
            user.must_change_password = False
            user.save()
            return user, True
        changed = False
        if user.role != role:
            user.role = role
            changed = True
        if not user.display_name:
            user.display_name = display_name
            changed = True
        if changed:
            user.save()
        return user, False

    @transaction.atomic
    def handle(self, *args, **options):
        today = date.today()
        academic_year = options["academic_year"] or f"{today.year if today.month >= 9 else today.year - 1}-{(today.year + 1) if today.month >= 9 else today.year}"
        credentials = []
        admin_password = self._credential(options["admin_password"])
        teacher_password = self._credential(options["teacher_password"])
        admin, admin_created = self._user(username=options["admin_username"], role=User.Role.ADMIN, display_name="Administrador de demo", password=admin_password)
        teacher, teacher_created = self._user(username=options["teacher_username"], role=User.Role.TEACHER, display_name="Profesor de demo", password=teacher_password)
        if admin_created and not options["admin_password"]:
            credentials.append((admin.username, admin_password))
        if teacher_created and not options["teacher_password"]:
            credentials.append((teacher.username, teacher_password))

        students = []
        student_count = max(1, min(options["students"], 100))
        for index in range(1, student_count + 1):
            username = f"{options['student_prefix']}{index:02d}"
            password = self._credential(options["student_password"])
            student, created = self._user(username=username, role=User.Role.STUDENT, display_name=f"Alumno demo {index:02d}", password=password)
            students.append(student)
            if created and not options["student_password"]:
                credentials.append((student.username, password))

        year, _ = AcademicYear.objects.get_or_create(name=academic_year, defaults={"active": True})
        cohort, _ = Cohort.objects.get_or_create(
            name="1SMR-Demo",
            academic_year=year,
            defaults={"active": True, "track": Cohort.Track.WEB},
        )
        ensure_cohort_track(cohort, Cohort.Track.WEB)
        TeachingAssignment.objects.get_or_create(cohort=cohort, teacher=teacher, defaults={"active": True})

        course, _ = Course.objects.get_or_create(slug="fundamentos-web-smr", defaults={"title": "Fundamentos web para SMR", "description": "Actividad de demostración de HTML, CSS y JavaScript.", "created_by": teacher})
        module, _ = Module.objects.get_or_create(course=course, position=1, defaults={"title": "Lenguajes de marcas web"})
        activity, _ = Activity.objects.get_or_create(module=module, slug="estructura-web", defaults={"title": "Estructura web: HTML, CSS y JavaScript", "kind": Activity.Kind.CODE, "status": Activity.Status.PUBLISHED, "created_by": teacher})
        version, _ = ActivityVersion.objects.get_or_create(activity=activity, version_number=1, defaults={
            "instructions": "Crea una página HTML semántica, aplica una hoja CSS y declara una función JavaScript sencilla. Esta práctica cubre una parte introductoria del RA1 navarro; no sustituye el módulo completo.",
            "objectives": ["Identificar etiquetas y atributos HTML", "Aplicar CSS a una interfaz", "Reconocer la estructura de un script"],
            "learning_outcomes": ["RA1"],
            "assessment_criteria": RA1_CRITERIA,
            "professional_module_code": "0228",
            "curriculum_scope": "Navarra",
            "curriculum_edition": "navarra-2025",
            "curriculum_unit": "",
            "curriculum_source": CURRICULUM_SOURCE,
            "starter_files": {"html": "<!doctype html>\n<html lang=\"es\">\n  <head><meta charset=\"utf-8\"><title>Mi página</title></head>\n  <body>\n    <main><h1>Mi página SMR</h1><p>Escribe aquí tu contenido.</p></main>\n  </body>\n</html>\n", "css": "body { font-family: sans-serif; }\n", "javascript": "function saludar() {\n  console.log('Hola, SMR');\n}\n"},
            "grading_mode": ActivityVersion.GradingMode.AUTOMATIC_STATIC,
            "auto_weight": "1.0000",
            "manual_weight": "0.0000",
            "created_by": teacher,
        })
        if activity.current_version_id != version.id:
            activity.current_version = version
            activity.status = Activity.Status.PUBLISHED
            activity.save(update_fields=["current_version", "status", "updated_at"])
        tests = [
            ("Documento HTML", "html.selector_exists", {"selector": "main"}, 2, "Añade un elemento main para el contenido principal."),
            ("Título de la página", "html.selector_exists", {"selector": "h1"}, 2, "Incluye un encabezado de nivel 1."),
            ("Hoja de estilos", "css.selector_exists", {"selector": "body"}, 2, "Define al menos una regla para body."),
            ("Función JavaScript", "js.function_declared", {"name": "saludar"}, 2, "Declara una función saludar."),
            ("JavaScript válido", "js.syntax_valid", {}, 2, "Comprueba que el JavaScript se puede analizar."),
        ]
        for position, (name, test_type, definition, points, feedback) in enumerate(tests):
            TestCase.objects.get_or_create(activity_version=version, name=name, defaults={"type": test_type, "definition": definition, "points": points, "feedback": feedback, "position": position, "visibility": TestCase.Visibility.PUBLIC})
        assignment, _ = get_or_create_catalog_assignment(
            activity=activity,
            version=version,
            defaults={
                "status": Assignment.Status.PUBLISHED,
                "created_by": teacher,
                "attempt_policy": Assignment.AttemptPolicy.BEST,
                "max_attempts": 3,
                "weight": 100,
                "published_at": timezone.now(),
            },
        )
        AssignmentCohort.objects.get_or_create(assignment=assignment, cohort=cohort)
        for student in students:
            set_student_cohort(student, cohort)

        self.stdout.write(self.style.SUCCESS(f"Demo creada: {course.title}, grupo {cohort.name}, {len(students)} alumnos."))
        if credentials:
            self.stdout.write(self.style.WARNING("Credenciales generadas (se muestran una sola vez; no se guardan en claro):"))
            for username, password in credentials:
                self.stdout.write(f"  {username}: {password}")
        elif not any((options["admin_password"], options["teacher_password"], options["student_password"])):
            self.stdout.write("Las cuentas ya existían; no se regeneraron ni se muestran contraseñas.")
