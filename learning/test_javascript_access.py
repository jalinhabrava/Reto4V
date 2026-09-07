from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from grading.models import Submission
from grading.services import (
    JAVASCRIPT_LOCK_REASON,
    create_manual_grade,
    create_submission,
    get_or_create_draft,
    run_formative_tests,
    student_assignment_or_404,
)
from learning.models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Enrollment,
    Module,
)
from learning.models import TestCase as ActivityTestCase


class JavaScriptAccessTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            password="UnaClaveSegura123!",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            password="UnaClaveSegura123!",
            role=User.Role.STUDENT,
        )
        self.other_student = User.objects.create_user(
            username="other",
            password="UnaClaveSegura123!",
            role=User.Role.STUDENT,
        )
        self.year = AcademicYear.objects.create(name="2026-2027")
        self.web = Cohort.objects.create(
            name="1SMR-A",
            academic_year=self.year,
            track=Cohort.Track.WEB,
        )
        self.other_web = Cohort.objects.create(
            name="1SMR-B",
            academic_year=self.year,
            track=Cohort.Track.WEB,
        )
        Enrollment.objects.create(student=self.student, cohort=self.web)
        Enrollment.objects.create(student=self.other_student, cohort=self.other_web)
        self.client.force_login(self.student)

    def assignment(self, *, stage, title, cohort=None, grading_mode=ActivityVersion.GradingMode.AUTOMATIC_STATIC):
        course = Course.objects.create(
            title=title,
            slug=title.lower().replace(" ", "-"),
            web_stage=stage,
            created_by=self.teacher,
        )
        module = Module.objects.create(course=course, title="Unidad", position=1)
        activity = Activity.objects.create(
            module=module,
            title=title,
            slug="reto",
            status=Activity.Status.PUBLISHED,
            created_by=self.teacher,
        )
        version = ActivityVersion.objects.create(
            activity=activity,
            version_number=1,
            language=ActivityVersion.Language.WEB,
            grading_mode=grading_mode,
            starter_files={"html": "<main></main>", "css": "", "javascript": ""},
            created_by=self.teacher,
        )
        ActivityTestCase.objects.create(
            activity_version=version,
            name="main",
            type="html.selector_exists",
            definition={"selector": "main"},
            points=Decimal("1"),
        )
        assignment = Assignment.objects.create(
            activity=activity,
            activity_version=version,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.teacher,
        )
        AssignmentCohort.objects.create(assignment=assignment, cohort=cohort or self.web)
        return assignment

    def submit_passing(self, assignment):
        submission, report = create_submission(
            self.student,
            assignment,
            {"html": "<main></main>", "css": "", "javascript": ""},
        )
        self.assertEqual(report.score, Decimal("10"))
        return submission

    def test_no_html_css_requirements_leaves_javascript_closed(self):
        javascript = self.assignment(
            stage=Course.WebStage.JAVASCRIPT,
            title="JavaScript inicial",
        )

        self.assertIsNone(student_assignment_or_404(self.student, javascript.id))
        response = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.json()["assignments"] if item["id"] == str(javascript.id))
        self.assertTrue(row["locked"])
        self.assertEqual(row["lock_reason"], JAVASCRIPT_LOCK_REASON)
        self.assertEqual(row["pathway"], Course.WebStage.JAVASCRIPT)
        pathways = {item["id"]: item for item in response.json()["pathways"]}
        self.assertEqual(pathways[Course.WebStage.HTML_CSS]["total"], 0)
        self.assertTrue(pathways[Course.WebStage.JAVASCRIPT]["locked"])

    def test_partial_and_preliminary_progress_do_not_unlock_javascript(self):
        first = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS uno")
        second = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS dos")
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="JavaScript inicial")

        report = run_formative_tests(
            self.student,
            first,
            {"html": "<main></main>", "css": "", "javascript": ""},
        )
        self.assertEqual(report.score, Decimal("10"))
        self.assertIsNone(student_assignment_or_404(self.student, javascript.id))

        self.submit_passing(first)
        self.assertIsNone(student_assignment_or_404(self.student, javascript.id))
        self.assertEqual(second.submissions.count(), 0)

    def test_all_html_css_automatic_completions_unlock_javascript(self):
        first = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS uno")
        second = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS dos")
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="JavaScript inicial")

        self.submit_passing(first)
        self.submit_passing(second)

        visible = student_assignment_or_404(self.student, javascript.id)
        self.assertEqual(visible.id, javascript.id)
        detail = self.client.get(reverse("workspace_detail_api", args=[javascript.id]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["pathway"], Course.WebStage.JAVASCRIPT)
        self.assertEqual(detail.json()["version"]["pathway"], Course.WebStage.JAVASCRIPT)

    def test_completion_threshold_is_exactly_eight(self):
        html_css = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS umbral")
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="JavaScript inicial")
        submission = self.submit_passing(html_css)

        Submission.objects.filter(pk=submission.pk).update(auto_score=Decimal("7.99"))
        self.assertIsNone(student_assignment_or_404(self.student, javascript.id))
        Submission.objects.filter(pk=submission.pk).update(auto_score=Decimal("8"))
        self.assertEqual(student_assignment_or_404(self.student, javascript.id).id, javascript.id)

    def test_best_valid_score_unlocks_despite_a_later_worse_attempt(self):
        html_css = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS mejor intento")
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="JavaScript inicial")
        best = self.submit_passing(html_css)
        worse = self.submit_passing(html_css)
        Submission.objects.filter(pk=best.pk).update(auto_score=Decimal("8"))
        Submission.objects.filter(pk=worse.pk).update(auto_score=Decimal("1"))

        self.assertEqual(student_assignment_or_404(self.student, javascript.id).id, javascript.id)

    def test_infrastructure_errors_and_drafts_do_not_unlock_javascript(self):
        html_css = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS sin entrega válida")
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="JavaScript inicial")
        get_or_create_draft(self.student, html_css)
        self.assertIsNone(student_assignment_or_404(self.student, javascript.id))

        submission = self.submit_passing(html_css)
        Submission.objects.filter(pk=submission.pk).update(
            status=Submission.Status.INFRA_ERROR,
            auto_score=Decimal("10"),
        )
        self.assertIsNone(student_assignment_or_404(self.student, javascript.id))

    def test_draft_and_archived_html_css_assignments_are_not_requirements(self):
        published = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS publicada")
        draft = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS borrador")
        archived = self.assignment(stage=Course.WebStage.HTML_CSS, title="HTML y CSS archivada")
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="JavaScript inicial")
        Assignment.objects.filter(pk=draft.pk).update(status=Assignment.Status.DRAFT)
        Assignment.objects.filter(pk=archived.pk).update(status=Assignment.Status.ARCHIVED)

        self.submit_passing(published)
        self.assertEqual(student_assignment_or_404(self.student, javascript.id).id, javascript.id)

    def test_manual_grade_never_counts_as_automatic_completion(self):
        manual = self.assignment(
            stage=Course.WebStage.HTML_CSS,
            title="HTML y CSS manual",
            grading_mode=ActivityVersion.GradingMode.MANUAL,
        )
        version = manual.activity_version
        ActivityVersion.objects.filter(pk=version.pk).update(auto_weight=Decimal("0"), manual_weight=Decimal("1"))
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="JavaScript inicial")

        submission, report = create_submission(
            self.student,
            manual,
            {"html": "<main></main>", "css": "", "javascript": ""},
        )
        self.assertIsNone(report)
        create_manual_grade(actor=self.teacher, submission=submission, score=Decimal("10"), publish=True)
        self.assertIsNone(student_assignment_or_404(self.student, javascript.id))

    def test_override_opens_and_disabling_it_relocks_every_student_route(self):
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="JavaScript inicial")
        self.student.javascript_enabled = True
        self.student.save(update_fields=["javascript_enabled"])
        self.assertEqual(student_assignment_or_404(self.student, javascript.id).id, javascript.id)
        dashboard = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json").json()
        javascript_path = next(
            item for item in dashboard["pathways"] if item["id"] == Course.WebStage.JAVASCRIPT
        )
        self.assertTrue(javascript_path["unlock_override"])
        self.assertEqual(javascript_path["completed"], 0)
        submission = self.submit_passing(javascript)

        self.student.javascript_enabled = False
        self.student.save(update_fields=["javascript_enabled"])
        routes = (
            ("workspace_page_root", "get"),
            ("student_workspace", "get"),
            ("workspace_detail_api", "get"),
            ("workspace_draft_api", "get"),
            ("workspace_tests_api", "post"),
            ("workspace_submit_api", "post"),
        )
        for name, method in routes:
            response = getattr(self.client, method)(reverse(name, args=[javascript.id]), data={})
            self.assertEqual(response.status_code, 404, name)
        self.assertEqual(
            self.client.get(reverse("student_submission", args=[submission.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("submission_detail_api", args=[submission.id])).status_code,
            404,
        )

    def test_override_does_not_bypass_foreign_cohort_membership(self):
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="JavaScript inicial")
        self.other_student.javascript_enabled = True
        self.other_student.save(update_fields=["javascript_enabled"])

        self.assertIsNone(student_assignment_or_404(self.other_student, javascript.id))
        self.client.force_login(self.other_student)
        self.assertEqual(
            self.client.get(reverse("workspace_detail_api", args=[javascript.id])).status_code,
            404,
        )

    def test_bash_track_remains_ungated_and_has_no_web_pathways(self):
        bash_student = User.objects.create_user(
            username="bash-student",
            password="UnaClaveSegura123!",
            role=User.Role.STUDENT,
            javascript_enabled=True,
        )
        bash = Cohort.objects.create(name="2ASIR-A", academic_year=self.year, track=Cohort.Track.BASH)
        Enrollment.objects.create(student=bash_student, cohort=bash)
        course = Course.objects.create(title="Bash", slug="bash", created_by=self.teacher)
        module = Module.objects.create(course=course, title="Unidad", position=1)
        activity = Activity.objects.create(module=module, title="Bash inicial", slug="bash-inicial", created_by=self.teacher)
        version = ActivityVersion.objects.create(
            activity=activity,
            version_number=1,
            language=ActivityVersion.Language.BASH,
            starter_files={"bash": "echo hola\n"},
            created_by=self.teacher,
        )
        assignment = Assignment.objects.create(
            activity=activity,
            activity_version=version,
            status=Assignment.Status.PUBLISHED,
            created_by=self.teacher,
        )
        AssignmentCohort.objects.create(assignment=assignment, cohort=bash)

        self.assertEqual(student_assignment_or_404(bash_student, assignment.id).id, assignment.id)
        self.client.force_login(bash_student)
        dashboard = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json").json()
        self.assertEqual(dashboard["pathways"], [])
        self.assertFalse(dashboard["assignments"][0]["locked"])

    def test_html_css_courses_are_listed_before_javascript_courses(self):
        javascript = self.assignment(stage=Course.WebStage.JAVASCRIPT, title="A JavaScript")
        html_css = self.assignment(stage=Course.WebStage.HTML_CSS, title="Z HTML y CSS")

        assignments = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json").json()["assignments"]
        ordered_ids = [row["id"] for row in assignments]
        self.assertLess(ordered_ids.index(str(html_css.id)), ordered_ids.index(str(javascript.id)))
