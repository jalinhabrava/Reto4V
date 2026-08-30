from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from grading.services import DraftConflict, create_submission, get_or_create_draft, save_draft

from .models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Draft,
    Enrollment,
    Module,
    TeachingAssignment,
)
from .models import (
    TestCase as ActivityTestCase,
)


class LearningFactoryMixin:
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="UnaClaveSegura123!", role=User.Role.TEACHER)
        self.student = User.objects.create_user(username="student", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        self.other_student = User.objects.create_user(username="other", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        self.year = AcademicYear.objects.create(name="2025-2026")
        self.cohort = Cohort.objects.create(name="1SMR-A", academic_year=self.year)
        Enrollment.objects.create(cohort=self.cohort, student=self.student)
        TeachingAssignment.objects.create(cohort=self.cohort, teacher=self.teacher)
        self.course = Course.objects.create(title="Web", slug="web", created_by=self.teacher)
        self.module = Module.objects.create(course=self.course, title="Unidad", position=1)
        self.activity = Activity.objects.create(module=self.module, title="Actividad", slug="actividad", created_by=self.teacher)
        self.version = ActivityVersion.objects.create(activity=self.activity, version_number=1, created_by=self.teacher, starter_files={"html": "<main></main>", "css": "body{}", "javascript": ""}, learning_outcomes=["RA1"], assessment_criteria=["RA1.a"], curriculum_scope="Navarra")
        self.activity.current_version = self.version
        self.activity.save(update_fields=["current_version", "updated_at"])
        self.assignment = Assignment.objects.create(activity=self.activity, activity_version=self.version, created_by=self.teacher, status=Assignment.Status.PUBLISHED, published_at=timezone.now())
        AssignmentCohort.objects.create(assignment=self.assignment, cohort=self.cohort)


class DraftTests(LearningFactoryMixin, TestCase):
    def test_seed_bash_is_idempotent_and_does_not_overwrite_assigned_versions(self):
        call_command("seed_bash", owner=self.teacher.username, cohort="2ASIR", academic_year="2025-2026")
        versions = ActivityVersion.objects.filter(language=ActivityVersion.Language.BASH)
        self.assertEqual(versions.count(), 12)
        self.assertEqual(ActivityTestCase.objects.filter(activity_version__in=versions).count(), 48)
        self.assertEqual(Assignment.objects.filter(activity_version__in=versions).count(), 12)
        self.assertTrue(all(not version.learning_outcomes and not version.assessment_criteria for version in versions))
        changed = versions.order_by("id").first()
        changed.reference_solution = {"bash": "solución docente externa"}
        ActivityVersion.objects.filter(pk=changed.pk).update(reference_solution=changed.reference_solution)
        call_command("seed_bash", owner=self.teacher.username, cohort="2ASIR", academic_year="2025-2026", stdout=None)
        changed.refresh_from_db()
        self.assertEqual(changed.reference_solution, {"bash": "solución docente externa"})

    def test_activity_version_language_scopes_files(self):
        bash_version = ActivityVersion(
            activity=self.activity,
            version_number=2,
            language=ActivityVersion.Language.BASH,
            starter_files={"html": "<p>no</p>"},
            created_by=self.teacher,
        )
        with self.assertRaises(ValidationError):
            bash_version.full_clean()
        valid = ActivityVersion(
            activity=self.activity,
            version_number=2,
            language=ActivityVersion.Language.BASH,
            starter_files={"bash": "#!/usr/bin/env bash\nprintf ok\n"},
            reference_solution={"bash": "#!/usr/bin/env bash\nprintf solution\n"},
            hints=["Primera pista"],
            created_by=self.teacher,
        )
        valid.full_clean()
        valid.save()
        self.assertEqual(valid.files, {"bash": "#!/usr/bin/env bash\nprintf ok\n"})

    def test_web_version_rejects_bash_files(self):
        invalid = ActivityVersion(
            activity=self.activity,
            version_number=2,
            language=ActivityVersion.Language.WEB,
            starter_files={"bash": "printf nope\n"},
            created_by=self.teacher,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_bash_draft_and_submission_use_only_bash_snapshot(self):
        bash_activity = Activity.objects.create(
            module=self.module,
            title="Reto Bash",
            slug="reto-bash",
            created_by=self.teacher,
            status=Activity.Status.PUBLISHED,
        )
        bash_version = ActivityVersion.objects.create(
            activity=bash_activity,
            version_number=1,
            language=ActivityVersion.Language.BASH,
            starter_files={"bash": "#!/usr/bin/env bash\n"},
            reference_solution={"bash": "#!/usr/bin/env bash\nprintf ok\n"},
            grading_mode=ActivityVersion.GradingMode.AUTOMATIC_STATIC,
            created_by=self.teacher,
        )
        bash_activity.current_version = bash_version
        bash_activity.save(update_fields=["current_version", "updated_at"])
        ActivityTestCase.objects.create(
            activity_version=bash_version,
            name="sintaxis",
            type="bash.syntax_valid",
            definition={},
        )
        assignment = Assignment.objects.create(
            activity=bash_activity,
            activity_version=bash_version,
            created_by=self.teacher,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        AssignmentCohort.objects.create(assignment=assignment, cohort=self.cohort)
        draft = get_or_create_draft(self.student, assignment)
        self.assertEqual(draft.files, {"bash": "#!/usr/bin/env bash\n"})
        submission, report = create_submission(
            self.student,
            assignment,
            {"bash": "#!/usr/bin/env bash\nprintf ok\n"},
        )
        self.assertEqual(submission.files.count(), 1)
        self.assertEqual(submission.files.get().path, "bash")
        self.assertEqual(report.score, 10)

    def test_revision_conflict_does_not_overwrite(self):
        draft = get_or_create_draft(self.student, self.assignment)
        updated = save_draft(self.student, self.assignment, {"html": "<h1>uno</h1>", "css": "", "javascript": "", "revision": draft.revision})
        self.assertEqual(updated.revision, 1)
        with self.assertRaises(DraftConflict) as raised:
            save_draft(self.student, self.assignment, {"html": "<h1>viejo</h1>", "css": "", "javascript": "", "revision": 0})
        self.assertEqual(raised.exception.draft.files["html"], "<h1>uno</h1>")
        self.assertEqual(Draft.objects.get(pk=draft.pk).files["html"], "<h1>uno</h1>")

    def test_other_student_has_no_draft_access(self):
        self.assertFalse(Assignment.objects.filter(pk=self.assignment.pk, cohort_links__cohort__enrollments__student=self.other_student).exists())

    def test_activity_version_used_by_assignment_is_append_only(self):
        self.version.instructions = "cambio no permitido"
        with self.assertRaises(ValidationError):
            self.version.save()

    def test_assigned_version_rejects_new_or_deleted_tests(self):
        with self.assertRaises(ValidationError):
            ActivityTestCase.objects.create(
                activity_version=self.version,
                name="nuevo",
                type="html.selector_exists",
                definition={"selector": "main"},
            )

        # Simulate legacy data created before the assignment was published;
        # bulk/queryset deletion must be blocked as well.
        legacy_version = ActivityVersion.objects.create(
            activity=self.activity,
            version_number=3,
            created_by=self.teacher,
        )
        legacy_test = ActivityTestCase.objects.create(
            activity_version=legacy_version,
            name="protegido",
            type="html.selector_exists",
            definition={"selector": "main"},
        )
        protected_assignment = Assignment.objects.create(
            activity=self.activity,
            activity_version=legacy_version,
            created_by=self.teacher,
            status=Assignment.Status.DRAFT,
        )
        with self.assertRaises(ValidationError), transaction.atomic():
            ActivityTestCase.objects.filter(pk=legacy_test.pk).delete()
        self.assertTrue(ActivityTestCase.objects.filter(pk=legacy_test.pk).exists())
        protected_assignment.delete()

        unlocked = ActivityVersion.objects.create(
            activity=self.activity,
            version_number=2,
            created_by=self.teacher,
        )
        test_case = ActivityTestCase.objects.create(
            activity_version=unlocked,
            name="borrable",
            type="html.selector_exists",
            definition={"selector": "main"},
        )
        test_case.delete()
        self.assertFalse(ActivityTestCase.objects.filter(pk=test_case.pk).exists())

    def test_teacher_only_sees_students_from_cohorts_they_teach(self):
        own_submission, _ = create_submission(
            self.student,
            self.assignment,
            {"html": "<main>propio</main>", "css": "", "javascript": ""},
        )
        other_teacher = User.objects.create_user(
            username="teacher2",
            password="UnaClaveSegura123!",
            role=User.Role.TEACHER,
        )
        other_cohort = Cohort.objects.create(name="1SMR-B", academic_year=self.year)
        Enrollment.objects.create(cohort=other_cohort, student=self.other_student)
        TeachingAssignment.objects.create(cohort=other_cohort, teacher=other_teacher)
        AssignmentCohort.objects.create(assignment=self.assignment, cohort=other_cohort)
        other_submission, _ = create_submission(
            self.other_student,
            self.assignment,
            {"html": "<main>ajeno</main>", "css": "", "javascript": ""},
        )

        self.client.force_login(self.teacher)
        dashboard = self.client.get(reverse("teacher_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["assignments"][0]["submissions"], 1)
        self.assertEqual(self.client.get(reverse("teacher_review", args=[own_submission.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse("teacher_review", args=[other_submission.id])).status_code, 404)
        export = self.client.get(reverse("teacher_export"))
        csv_text = export.content.decode("utf-8-sig")
        self.assertIn(self.student.username, csv_text)
        self.assertNotIn(self.other_student.username, csv_text)

    def test_student_dashboard_reload_returns_normalised_counts_and_gamification(self):
        self.client.force_login(self.student)
        initial = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(initial.json()["assignments"][0]["submissions"], 0)
        self.assertEqual(initial.json()["gamification"]["total_xp"], 0)

        create_submission(
            self.student,
            self.assignment,
            {"html": "<main>entrega</main>", "css": "body{}", "javascript": ""},
        )
        refreshed = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(refreshed.status_code, 200)
        assignment = refreshed.json()["assignments"][0]
        self.assertEqual(assignment["submissions"], 1)
        self.assertEqual(assignment["language"], "web")
        self.assertEqual(assignment["xp_reward"], 100)
        self.assertEqual(assignment["earned_xp"], 0)
        self.assertFalse(assignment["completed"])
