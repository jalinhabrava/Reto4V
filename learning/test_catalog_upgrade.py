from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from grading.models import Submission
from learning.management.commands._catalog import get_or_create_catalog_revision_assignment
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
    TeachingAssignment,
)
from learning.services import supersede_catalog_assignments
from learning.views import _activity_public_payload, teacher_assignments_for


class CatalogAssignmentUpgradeTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="catalog-owner",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            role=User.Role.STUDENT,
        )
        year = AcademicYear.objects.create(name="2026-2027")
        self.cohort_a = Cohort.objects.create(
            name="1SMR-A",
            academic_year=year,
            track=Cohort.Track.WEB,
        )
        self.cohort_b = Cohort.objects.create(
            name="1SMR-B",
            academic_year=year,
            track=Cohort.Track.WEB,
        )
        course = Course.objects.create(
            title="Web",
            slug="catalog-upgrade-web",
            created_by=self.owner,
        )
        module = Module.objects.create(course=course, title="Inicio", position=1)
        self.activity = Activity.objects.create(
            module=module,
            title="Primera web",
            slug="primera-web",
            created_by=self.owner,
        )
        self.old_version = ActivityVersion.objects.create(
            activity=self.activity,
            version_number=1,
            language=ActivityVersion.Language.WEB,
            starter_files={"html": "<h1>Antes</h1>", "css": "", "javascript": ""},
            created_by=self.owner,
        )
        self.new_version = ActivityVersion.objects.create(
            activity=self.activity,
            version_number=2,
            language=ActivityVersion.Language.WEB,
            starter_files={"html": "<h1>Hola</h1>"},
            created_by=self.owner,
        )
        self.old_assignment = Assignment.objects.create(
            activity=self.activity,
            activity_version=self.old_version,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.owner,
        )
        AssignmentCohort.objects.create(assignment=self.old_assignment, cohort=self.cohort_a)
        AssignmentCohort.objects.create(assignment=self.old_assignment, cohort=self.cohort_b)
        TeachingAssignment.objects.create(cohort=self.cohort_a, teacher=self.owner)
        self.new_assignment = Assignment.objects.create(
            activity=self.activity,
            activity_version=self.new_version,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.owner,
        )

    def test_upgrade_copies_cohorts_archives_old_assignment_and_preserves_evidence(self):
        self.assertEqual(
            _activity_public_payload(self.new_assignment)["version"]["editor_files"],
            ["html"],
        )
        draft = Draft.objects.create(
            assignment=self.old_assignment,
            student=self.student,
            activity_version=self.old_version,
            files={"html": "<h1>Trabajo en curso</h1>", "css": "", "javascript": ""},
            revision=3,
        )
        submission = Submission.objects.create(
            assignment=self.old_assignment,
            activity_version=self.old_version,
            student=self.student,
            attempt_number=1,
            status=Submission.Status.GRADED,
            auto_score="8.00000",
        )

        result = supersede_catalog_assignments(self.new_assignment)

        self.assertEqual(result, {"migrated_links": 2, "archived_assignments": 1})
        self.old_assignment.refresh_from_db()
        self.assertEqual(self.old_assignment.status, Assignment.Status.ARCHIVED)
        self.assertIsNotNone(self.old_assignment.closed_at)
        self.assertSetEqual(
            set(self.new_assignment.cohort_links.values_list("cohort_id", flat=True)),
            {self.cohort_a.pk, self.cohort_b.pk},
        )
        draft.refresh_from_db()
        submission.refresh_from_db()
        self.assertEqual(draft.assignment_id, self.old_assignment.pk)
        self.assertEqual(draft.activity_version_id, self.old_version.pk)
        self.assertEqual(submission.assignment_id, self.old_assignment.pk)
        self.assertEqual(submission.activity_version_id, self.old_version.pk)

        self.assertEqual(
            list(
                teacher_assignments_for(
                    self.owner,
                    include_archived=False,
                ).values_list("pk", flat=True)
            ),
            [self.new_assignment.pk],
        )
        self.assertSetEqual(
            set(teacher_assignments_for(self.owner).values_list("pk", flat=True)),
            {self.old_assignment.pk, self.new_assignment.pk},
        )

        self.client.force_login(self.owner)
        export = self.client.get(reverse("teacher_export"), {"format": "wide"})
        self.assertEqual(export.status_code, 200)
        csv_text = export.content.decode("utf-8-sig")
        self.assertEqual(csv_text.count(self.new_assignment.title), 1)

        repeated = supersede_catalog_assignments(self.new_assignment)
        self.assertEqual(repeated, {"migrated_links": 0, "archived_assignments": 0})
        self.assertEqual(self.new_assignment.cohort_links.count(), 2)

    def test_bootstrap_can_repeat_after_current_revision_is_closed(self):
        self.new_assignment.status = Assignment.Status.CLOSED
        self.new_assignment.closed_at = timezone.now()
        self.new_assignment.save(update_fields=["status", "closed_at"])

        result = supersede_catalog_assignments(self.new_assignment)

        self.assertEqual(result, {"migrated_links": 2, "archived_assignments": 1})
        self.old_assignment.refresh_from_db()
        self.assertEqual(self.old_assignment.status, Assignment.Status.ARCHIVED)

    def test_draft_revision_does_not_hide_the_published_catalogue(self):
        self.new_assignment.status = Assignment.Status.DRAFT
        self.new_assignment.published_at = None
        self.new_assignment.save(update_fields=["status", "published_at"])

        result = supersede_catalog_assignments(self.new_assignment)

        self.assertEqual(result, {"migrated_links": 0, "archived_assignments": 0})
        self.old_assignment.refresh_from_db()
        self.assertEqual(self.old_assignment.status, Assignment.Status.PUBLISHED)

    def test_revision_helper_keeps_teacher_assignment_settings(self):
        activity = Activity.objects.create(
            module=self.activity.module,
            title="Segundo reto",
            slug="segundo-reto",
            created_by=self.owner,
        )
        old_version = ActivityVersion.objects.create(
            activity=activity,
            version_number=1,
            language=ActivityVersion.Language.WEB,
            created_by=self.owner,
        )
        new_version = ActivityVersion.objects.create(
            activity=activity,
            version_number=2,
            language=ActivityVersion.Language.WEB,
            created_by=self.owner,
        )
        due_at = timezone.now() + timedelta(days=10)
        old_assignment = Assignment.objects.create(
            activity=activity,
            activity_version=old_version,
            title_override="Reto adaptado por el centro",
            status=Assignment.Status.PUBLISHED,
            due_at=due_at,
            max_attempts=5,
            attempt_policy=Assignment.AttemptPolicy.LATEST,
            weight=75,
            allow_late=False,
            published_at=timezone.now(),
            created_by=self.owner,
        )
        AssignmentCohort.objects.create(assignment=old_assignment, cohort=self.cohort_a)
        AssignmentCohort.objects.create(assignment=old_assignment, cohort=self.cohort_b)

        assignment, created, upgrade = get_or_create_catalog_revision_assignment(
            activity=activity,
            version=new_version,
            cohort=self.cohort_a,
            defaults={
                "status": Assignment.Status.PUBLISHED,
                "created_by": self.owner,
                "published_at": timezone.now(),
            },
        )

        self.assertTrue(created)
        self.assertEqual(upgrade["archived_assignments"], 1)
        self.assertEqual(assignment.title_override, old_assignment.title_override)
        self.assertEqual(assignment.due_at, due_at)
        self.assertEqual(assignment.max_attempts, 5)
        self.assertEqual(assignment.attempt_policy, Assignment.AttemptPolicy.LATEST)
        self.assertEqual(assignment.weight, 75)
        self.assertFalse(assignment.allow_late)
        self.assertSetEqual(
            set(assignment.cohort_links.values_list("cohort_id", flat=True)),
            {self.cohort_a.pk, self.cohort_b.pk},
        )
