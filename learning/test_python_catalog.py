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

    def test_v2_catalog_is_complete_idempotent_and_all_solutions_score_ten(self):
        self.seed()

        final_tree = ast.parse(CHALLENGES[-1]["solution"]["python"])
        self.assertTrue(
            any(
                isinstance(node, ast.Constant) and node.value == "\n"
                for node in ast.walk(final_tree)
            ),
            "El flujo final debe separar los registros con saltos de línea reales.",
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
            67,
        )
        self.assertEqual(
            sum(version.test_cases.count() for version in versions),
            67,
        )
        self.assertEqual(
            Assignment.objects.filter(activity_version__in=versions).count(),
            12,
        )

        by_slug = {challenge["slug"]: challenge for challenge in CHALLENGES}
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

    def test_v2_migrates_an_assigned_v1_without_rewriting_evidence(self):
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
            version_number=1,
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
        )
        cohort = Cohort.objects.create(
            name="2DAM",
            academic_year=self.year,
            track=Cohort.Track.PYTHON,
        )
        AssignmentCohort.objects.create(assignment=old_assignment, cohort=cohort)
        activity.current_version = old_version
        activity.save(update_fields=["current_version", "updated_at"])

        self.seed()

        activity.refresh_from_db()
        old_version.refresh_from_db()
        old_assignment.refresh_from_db()
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
        self.assertEqual(activity.title, "Título histórico")
        self.assertEqual(activity.current_version_id, new_version.id)
        self.assertEqual(old_version.starter_files, old_files)
        self.assertEqual(old_version.reference_solution, old_files)
        self.assertEqual(old_assignment.status, Assignment.Status.ARCHIVED)
        self.assertEqual(new_assignment.title, challenge["title"])
        self.assertEqual(
            Activity.objects.filter(module=module).count(),
            12,
        )
        self.assertEqual(course.title, "Introducción a Python para SGE · DAM")
        self.assertEqual(module.title, "De los primeros datos a los archivos")

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
            version_number=3,
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
