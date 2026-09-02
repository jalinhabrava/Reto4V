from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from grading.evaluator import evaluate_tests
from grading.models import Submission
from learning.management.commands.seed_bash import (
    BASH_CATALOG_VERSION,
    CHALLENGES,
    TRACK_SLUG,
)
from learning.models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Draft,
    Module,
)


class BashCatalogTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="bash-catalog-owner",
            password="UnaClaveSegura123!",
            role=User.Role.TEACHER,
        )

    def seed(self, cohort="2ASIR", academic_year="2026-2027"):
        call_command(
            "seed_bash",
            owner=self.owner.username,
            cohort=cohort,
            academic_year=academic_year,
            stdout=StringIO(),
        )

    def test_catalog_is_a_guided_progression_with_static_solutions(self):
        self.seed()

        course = Course.objects.get(slug=TRACK_SLUG)
        versions = list(
            ActivityVersion.objects.filter(activity__module__course=course)
            .prefetch_related("test_cases")
            .order_by("activity__slug")
        )
        self.assertEqual(len(versions), len(CHALLENGES))
        self.assertEqual(
            [version.activity.slug for version in versions],
            sorted(item["slug"] for item in CHALLENGES),
        )
        self.assertTrue(all(version.version_number == BASH_CATALOG_VERSION for version in versions))
        self.assertTrue(all(version.language == ActivityVersion.Language.BASH for version in versions))
        self.assertTrue(all(not version.learning_outcomes for version in versions))
        self.assertTrue(all(not version.assessment_criteria for version in versions))
        self.assertEqual(
            Assignment.objects.filter(activity_version__in=versions).count(),
            len(CHALLENGES),
        )

        for version in versions:
            item = next(item for item in CHALLENGES if item["slug"] == version.activity.slug)
            self.assertEqual(version.starter_files, {"bash": item["starter"]})
            self.assertEqual(version.reference_solution, {"bash": item["solution"]})
            self.assertTrue(item["task"].startswith("1."))
            self.assertIn("\n2.", item["task"])
            self.assertNotEqual(version.starter_files, version.reference_solution)
            self.assertEqual(version.test_cases.count(), 4)
            self.assertEqual(set(version.starter_files), {"bash"})
            self.assertEqual(set(version.reference_solution), {"bash"})
            report = evaluate_tests(
                version.reference_solution,
                list(version.test_cases.all()),
                language="bash",
            )
            self.assertEqual(report.status, "passed", version.activity.slug)
            self.assertEqual(report.score, 10, version.activity.slug)

    def test_reseeding_v2_is_idempotent_and_keeps_teacher_solution_edits(self):
        self.seed()
        versions = list(
            ActivityVersion.objects.filter(language=ActivityVersion.Language.BASH)
            .order_by("activity__slug")
        )
        self.assertEqual(len(versions), 12)
        changed = versions[0]
        changed_solution = {"bash": "#!/usr/bin/env bash\nprintf 'adaptado por el centro\\n'\n"}
        ActivityVersion.objects.filter(pk=changed.pk).update(reference_solution=changed_solution)
        course = Course.objects.get(slug=TRACK_SLUG)
        Module.objects.filter(course=course, position=1).update(title="Bloque antiguo", description="Texto antiguo")
        Course.objects.filter(pk=course.pk).update(title="Curso antiguo", description="Texto antiguo")

        self.seed()

        self.assertEqual(
            ActivityVersion.objects.filter(language=ActivityVersion.Language.BASH).count(),
            12,
        )
        self.assertEqual(
            Assignment.objects.filter(activity_version__language=ActivityVersion.Language.BASH).count(),
            12,
        )
        changed.refresh_from_db()
        self.assertEqual(changed.version_number, BASH_CATALOG_VERSION)
        self.assertEqual(changed.reference_solution, changed_solution)
        course.refresh_from_db()
        module = Module.objects.get(course=course, position=1)
        self.assertEqual(course.title, "Laboratorio Bash para Seguridad · ASIR")
        self.assertEqual(module.title, "De cero a tus primeras automatizaciones")

    def test_v1_evidence_is_preserved_when_catalogue_moves_to_v2(self):
        year = AcademicYear.objects.create(name="2026-2027")
        cohort = Cohort.objects.create(
            name="2ASIR",
            academic_year=year,
            track=Cohort.Track.BASH,
        )
        course = Course.objects.create(
            title="Laboratorio Bash antiguo",
            slug=TRACK_SLUG,
            created_by=self.owner,
        )
        module = Module.objects.create(course=course, title="Bloque antiguo", position=1)
        item = CHALLENGES[0]
        activity = Activity.objects.create(
            module=module,
            slug=item["slug"],
            title="Reto Bash antiguo",
            status=Activity.Status.PUBLISHED,
            created_by=self.owner,
        )
        old_version = ActivityVersion.objects.create(
            activity=activity,
            version_number=1,
            language=ActivityVersion.Language.BASH,
            starter_files={"bash": "#!/usr/bin/env bash\n"},
            reference_solution={"bash": "#!/usr/bin/env bash\necho antiguo\n"},
            created_by=self.owner,
            published_at=timezone.now(),
        )
        activity.current_version = old_version
        activity.save(update_fields=["current_version", "updated_at"])
        old_assignment = Assignment.objects.create(
            activity=activity,
            activity_version=old_version,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.owner,
            due_at=timezone.now(),
            max_attempts=3,
            weight=70,
            allow_late=False,
        )
        AssignmentCohort.objects.create(assignment=old_assignment, cohort=cohort)

        student = User.objects.create_user(
            username="bash-history-student",
            password="UnaClaveSegura123!",
            role=User.Role.STUDENT,
        )
        draft = Draft.objects.create(
            assignment=old_assignment,
            student=student,
            activity_version=old_version,
            files={"bash": "#!/usr/bin/env bash\necho en curso\n"},
            revision=2,
        )
        submission = Submission.objects.create(
            assignment=old_assignment,
            activity_version=old_version,
            student=student,
            attempt_number=1,
            status=Submission.Status.GRADED,
            auto_score="8.00000",
        )

        self.seed(cohort=cohort.name, academic_year=year.name)

        activity.refresh_from_db()
        old_assignment.refresh_from_db()
        draft.refresh_from_db()
        submission.refresh_from_db()
        new_version = ActivityVersion.objects.get(activity=activity, version_number=BASH_CATALOG_VERSION)
        new_assignment = Assignment.objects.get(activity=activity, activity_version=new_version)

        self.assertEqual(activity.current_version_id, new_version.pk)
        self.assertEqual(old_assignment.status, Assignment.Status.ARCHIVED)
        self.assertEqual(old_assignment.weight, 70)
        self.assertFalse(old_assignment.allow_late)
        self.assertEqual(new_assignment.weight, 70)
        self.assertFalse(new_assignment.allow_late)
        self.assertTrue(
            AssignmentCohort.objects.filter(assignment=new_assignment, cohort=cohort).exists()
        )
        self.assertEqual(draft.assignment_id, old_assignment.pk)
        self.assertEqual(draft.activity_version_id, old_version.pk)
        self.assertEqual(submission.assignment_id, old_assignment.pk)
        self.assertEqual(submission.activity_version_id, old_version.pk)

    def test_a_newer_hand_authored_revision_is_never_downgraded(self):
        course = Course.objects.create(
            title="Bash del centro",
            slug=TRACK_SLUG,
            created_by=self.owner,
        )
        module = Module.objects.create(course=course, title="Bloque del centro", position=1)
        item = CHALLENGES[0]
        activity = Activity.objects.create(
            module=module,
            slug=item["slug"],
            title="Actividad del centro",
            status=Activity.Status.PUBLISHED,
            created_by=self.owner,
        )
        ActivityVersion.objects.create(
            activity=activity,
            version_number=BASH_CATALOG_VERSION + 1,
            language=ActivityVersion.Language.BASH,
            starter_files={"bash": "#!/usr/bin/env bash\n# versión del centro\n"},
            created_by=self.owner,
        )

        self.seed()

        activity.refresh_from_db()
        self.assertIsNone(activity.current_version_id)
        self.assertEqual(
            set(ActivityVersion.objects.filter(activity=activity).values_list("version_number", flat=True)),
            {BASH_CATALOG_VERSION + 1},
        )
