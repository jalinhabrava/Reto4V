import ast

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from grading.evaluator import evaluate_tests
from learning.management.commands.seed_python import (
    CHALLENGES,
    CURRICULUM_SOURCE,
    PYTHON_CATALOG_VERSION,
    V2_TITLES,
)

from .models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Module,
)


class PythonCatalogTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="python-teacher",
            password="UnaClaveSegura123!",
            role=User.Role.TEACHER,
        )
        self.year = AcademicYear.objects.create(name="2026-2027")

    def seed(self, cohort="2DAM"):
        call_command(
            "seed_python",
            owner=self.teacher.username,
            cohort=cohort,
            academic_year=self.year.name,
            stdout=None,
        )

    def test_v3_catalog_is_complete_idempotent_and_all_solutions_score_ten(self):
        self.seed()

        self.assertEqual(
            [challenge["slug"] for challenge in CHALLENGES],
            [
                "01-salida-y-variables",
                "02-tipos-y-cadenas",
                "03-condicionales-de-stock",
                "04-listas-y-bucles",
                "05-diccionarios-de-registro",
                "06-funciones-reutilizables",
                "07-excepciones-de-datos",
                "08-imports-y-fechas",
                "09-rutas-con-pathlib",
                "10-lectura-de-texto",
                "11-escritura-json",
                "12-integracion-archivos",
            ],
        )
        self.assertEqual(len(V2_TITLES), len(CHALLENGES))
        self.assertTrue(all("### Concepto" in item["theory"] for item in CHALLENGES))
        self.assertTrue(all("### Ejemplo" in item["theory"] for item in CHALLENGES))
        self.assertIn("`pass` es un marcador temporal", CHALLENGES[5]["theory"])
        second_tree = ast.parse(CHALLENGES[1]["solution"]["python"])
        self.assertFalse(any(isinstance(node, ast.JoinedStr) for node in ast.walk(second_tree)))
        for challenge in CHALLENGES[:6]:
            tree = ast.parse(challenge["solution"]["python"])
            self.assertFalse(any(isinstance(node, ast.For) for node in ast.walk(tree)))
        function_steps = [
            (CHALLENGES[8], "saludar", [], False),
            (CHALLENGES[9], "mostrar", ["producto"], False),
            (CHALLENGES[10], "duplicar", ["numero"], True),
        ]
        for challenge, name, args, has_return in function_steps:
            tree = ast.parse(challenge["solution"]["python"])
            function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
            self.assertEqual(function.name, name)
            self.assertEqual([arg.arg for arg in function.args.args], args)
            self.assertEqual(any(isinstance(node, ast.Return) for node in ast.walk(function)), has_return)
        review_tree = ast.parse(CHALLENGES[11]["solution"]["python"])
        self.assertTrue(any(isinstance(node, ast.List) for node in ast.walk(review_tree)))
        self.assertTrue(any(isinstance(node, ast.For) for node in ast.walk(review_tree)))
        self.assertTrue(
            all(
                not any(test[1] == "python.file_opened" for test in challenge["tests"])
                for challenge in CHALLENGES
            )
        )

        course = Course.objects.get(slug="introduccion-python-sge-dam")
        versions = list(
            ActivityVersion.objects.filter(
                activity__module__course=course,
                language=ActivityVersion.Language.PYTHON,
            )
            .prefetch_related("test_cases")
            .select_related("activity")
            .order_by("activity__title")
        )
        self.assertEqual(len(CHALLENGES), 12)
        self.assertEqual(len(versions), 12)
        self.assertEqual(
            sum(len(challenge["tests"]) for challenge in CHALLENGES),
            58,
        )
        self.assertEqual(
            sum(version.test_cases.count() for version in versions),
            58,
        )
        self.assertEqual(
            Assignment.objects.filter(activity_version__in=versions).count(),
            12,
        )

        by_slug = {challenge["slug"]: challenge for challenge in CHALLENGES}
        self.assertEqual(
            [
                next(version.activity.position for version in versions if version.activity.slug == challenge["slug"])
                for challenge in CHALLENGES
            ],
            list(range(1, len(CHALLENGES) + 1)),
        )
        for version in versions:
            challenge = by_slug[version.activity.slug]
            self.assertEqual(version.version_number, PYTHON_CATALOG_VERSION)
            self.assertEqual(version.starter_files, challenge["starter"])
            self.assertEqual(version.reference_solution, challenge["solution"])
            self.assertEqual(version.hints, challenge["hints"])
            self.assertEqual(version.objectives, challenge["objectives"])
            self.assertEqual(version.learning_outcomes, [])
            self.assertEqual(version.assessment_criteria, [])
            self.assertEqual(version.professional_module_code, "0491")
            self.assertEqual(version.curriculum_source, CURRICULUM_SOURCE)
            self.assertEqual(version.activity.current_version_id, version.id)
            self.assertEqual(set(version.starter_files), {"python"})
            starter_report = evaluate_tests(
                version.starter_files,
                list(version.test_cases.all()),
                language="python",
            )
            self.assertIsNotNone(starter_report.score, version.activity.slug)
            self.assertLess(starter_report.score, 8, version.activity.slug)
            report = evaluate_tests(
                version.reference_solution,
                list(version.test_cases.all()),
                language="python",
            )
            self.assertEqual(report.status, "passed", version.activity.slug)
            self.assertEqual(report.score, 10, version.activity.slug)

        self.assertEqual(course.title, "Introducción a Python para SGE · DAM")
        self.assertEqual(
            Course.objects.filter(slug="introduccion-python-sge-dam").count(),
            1,
        )
        self.seed()
        self.assertEqual(
            ActivityVersion.objects.filter(
                activity__module__course=course,
                language=ActivityVersion.Language.PYTHON,
            ).count(),
            12,
        )
        self.assertEqual(
            Assignment.objects.filter(
                activity_version__language=ActivityVersion.Language.PYTHON,
                activity_version__version_number=PYTHON_CATALOG_VERSION,
            ).count(),
            12,
        )

    def test_v3_migrates_assigned_v2_and_updates_only_known_catalog_titles(self):
        course = Course.objects.create(
            title="Python antiguo · DAM",
            slug="introduccion-python-sge-dam",
            created_by=self.teacher,
        )
        module = Module.objects.create(course=course, title="Módulo antiguo", position=1)
        challenge = CHALLENGES[0]
        activity = Activity.objects.create(
            module=module,
            title="Título histórico",
            slug=challenge["slug"],
            status=Activity.Status.PUBLISHED,
            created_by=self.teacher,
        )
        old_files = {"python": "print('entrega antigua')\n"}
        old_version = ActivityVersion.objects.create(
            activity=activity,
            version_number=2,
            language=ActivityVersion.Language.PYTHON,
            starter_files=old_files,
            reference_solution=old_files,
            created_by=self.teacher,
            published_at=timezone.now(),
        )
        old_assignment = Assignment.objects.create(
            activity=activity,
            activity_version=old_version,
            status=Assignment.Status.PUBLISHED,
            created_by=self.teacher,
            published_at=timezone.now(),
            title_override=V2_TITLES[challenge["slug"]],
        )
        cohort = Cohort.objects.create(
            name="2DAM",
            academic_year=self.year,
            track=Cohort.Track.PYTHON,
        )
        AssignmentCohort.objects.create(assignment=old_assignment, cohort=cohort)
        activity.current_version = old_version
        activity.save(update_fields=["current_version", "updated_at"])

        customized_challenge = CHALLENGES[1]
        customized_activity = Activity.objects.create(
            module=module,
            title="Actividad con título docente",
            slug=customized_challenge["slug"],
            status=Activity.Status.PUBLISHED,
            created_by=self.teacher,
        )
        customized_version = ActivityVersion.objects.create(
            activity=customized_activity,
            version_number=2,
            language=ActivityVersion.Language.PYTHON,
            starter_files=old_files,
            reference_solution=old_files,
            created_by=self.teacher,
            published_at=timezone.now(),
        )
        customized_assignment = Assignment.objects.create(
            activity=customized_activity,
            activity_version=customized_version,
            status=Assignment.Status.PUBLISHED,
            created_by=self.teacher,
            published_at=timezone.now(),
            title_override="Taller docente de variables",
        )
        AssignmentCohort.objects.create(assignment=customized_assignment, cohort=cohort)
        customized_activity.current_version = customized_version
        customized_activity.save(update_fields=["current_version", "updated_at"])

        self.seed()

        activity.refresh_from_db()
        old_version.refresh_from_db()
        old_assignment.refresh_from_db()
        customized_assignment.refresh_from_db()
        course.refresh_from_db()
        module.refresh_from_db()
        new_version = ActivityVersion.objects.get(
            activity=activity,
            version_number=PYTHON_CATALOG_VERSION,
        )
        new_assignment = Assignment.objects.get(
            activity_version=new_version,
            cohort_links__cohort=cohort,
        )
        customized_new_version = ActivityVersion.objects.get(
            activity=customized_activity,
            version_number=PYTHON_CATALOG_VERSION,
        )
        customized_new_assignment = Assignment.objects.get(
            activity_version=customized_new_version,
            cohort_links__cohort=cohort,
        )
        self.assertEqual(activity.title, "Título histórico")
        self.assertEqual(activity.current_version_id, new_version.id)
        self.assertEqual(old_version.starter_files, old_files)
        self.assertEqual(old_version.reference_solution, old_files)
        self.assertEqual(old_assignment.status, Assignment.Status.ARCHIVED)
        self.assertEqual(new_assignment.title, challenge["title"])
        self.assertEqual(customized_new_assignment.title_override, "Taller docente de variables")
        self.assertEqual(customized_assignment.status, Assignment.Status.ARCHIVED)
        self.assertEqual(
            Activity.objects.filter(module=module).count(),
            12,
        )
        self.assertEqual(course.title, "Introducción a Python para SGE · DAM")
        self.assertEqual(module.title, "De los primeros programas a las funciones")

    def test_seed_does_not_lower_current_pointer_when_a_later_revision_exists(self):
        course = Course.objects.create(
            title="Python docente · DAM",
            slug="introduccion-python-sge-dam",
            created_by=self.teacher,
        )
        module = Module.objects.create(course=course, title="Módulo docente", position=1)
        challenge = CHALLENGES[0]
        activity = Activity.objects.create(
            module=module,
            title="Actividad docente",
            slug=challenge["slug"],
            status=Activity.Status.PUBLISHED,
            created_by=self.teacher,
        )
        later = ActivityVersion.objects.create(
            activity=activity,
            version_number=4,
            language=ActivityVersion.Language.PYTHON,
            starter_files={"python": "print('v3')\n"},
            reference_solution={"python": "print('v3')\n"},
            created_by=self.teacher,
            published_at=timezone.now(),
        )
        activity.current_version = later
        activity.save(update_fields=["current_version", "updated_at"])

        self.seed()

        activity.refresh_from_db()
        self.assertEqual(activity.current_version_id, later.id)
        self.assertFalse(
            ActivityVersion.objects.filter(
                activity=activity,
                version_number=PYTHON_CATALOG_VERSION,
            ).exists()
        )
        self.assertEqual(activity.position, 0)
