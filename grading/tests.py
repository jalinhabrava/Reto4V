from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
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
    Enrollment,
    Module,
    TeachingAssignment,
)
from learning.models import TestCase as LearningTestCase
from learning.views import _select_attempt

from .evaluator import evaluate_tests, validate_test_definition
from .services import create_manual_grade, create_submission, gamification_for_assignment


class GradingFactoryMixin:
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="UnaClaveSegura123!", role=User.Role.TEACHER)
        self.student = User.objects.create_user(username="student", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        year = AcademicYear.objects.create(name="2025-2026")
        cohort = Cohort.objects.create(name="1SMR-A", academic_year=year)
        Enrollment.objects.create(cohort=cohort, student=self.student)
        TeachingAssignment.objects.create(cohort=cohort, teacher=self.teacher)
        course = Course.objects.create(title="Web", slug="web", created_by=self.teacher)
        module = Module.objects.create(course=course, title="Unidad", position=1)
        activity = Activity.objects.create(module=module, title="Actividad", slug="actividad", created_by=self.teacher)
        self.version = ActivityVersion.objects.create(activity=activity, version_number=1, created_by=self.teacher, grading_mode=ActivityVersion.GradingMode.AUTOMATIC_STATIC, starter_files={"html": "<main></main>", "css": "body{}", "javascript": ""})
        activity.current_version = self.version
        activity.save(update_fields=["current_version", "updated_at"])
        LearningTestCase.objects.create(activity_version=self.version, name="main", type="html.selector_exists", definition={"selector": "main"}, points=Decimal("2"), feedback="Añade main")
        LearningTestCase.objects.create(activity_version=self.version, name="body", type="css.selector_exists", definition={"selector": "body"}, points=Decimal("1"), feedback="Añade body")
        LearningTestCase.objects.create(
            activity_version=self.version,
            name="criterio secreto",
            type="html.forbidden_element_absent",
            definition={"selector": "script"},
            points=Decimal("7"),
            visibility=LearningTestCase.Visibility.PRIVATE,
            feedback="solución privada",
        )
        self.assignment = Assignment.objects.create(activity=activity, activity_version=self.version, created_by=self.teacher, status=Assignment.Status.PUBLISHED, max_attempts=2, published_at=timezone.now())
        AssignmentCohort.objects.create(assignment=self.assignment, cohort=cohort)


class EvaluatorTests(TestCase):
    def test_evaluator_uses_html_css_and_js_ast_without_execution(self):
        tests = [
            {"name": "main", "type": "html.selector_exists", "definition": {"selector": "main"}, "points": 2},
            {"name": "function", "type": "js.function_declared", "definition": {"name": "saludar"}, "points": 1},
            {"name": "no eval", "type": "js.forbidden_api_absent", "definition": {"api": "eval"}, "points": 1},
        ]
        report = evaluate_tests({"html": "<main>ok</main>", "css": "", "javascript": "function saludar() {}"}, tests)
        self.assertEqual(report.status, "passed")
        self.assertEqual(report.score, Decimal("10"))

    def test_unknown_dsl_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_definition("html.selector_exists", {"selector": "main", "arbitrary": "x"})

    def test_bash_evaluator_uses_ast_and_supports_core_static_checks(self):
        source = """#!/usr/bin/env bash
DEST=\"laboratorio/backup.tgz\"
if [ -d \"$DEST\" ]; then
  tar -czf \"$DEST\" laboratorio/fuente
fi
for item in uno dos; do printf '%s\\n' \"$item\"; done
backup() { printf 'preparado\\n'; }
"""
        tests = [
            {"name": "sintaxis", "type": "bash.syntax_valid", "definition": {}, "points": 1},
            {"name": "shebang", "type": "bash.shebang", "definition": {"interpreter": "bash"}, "points": 1},
            {"name": "variable", "type": "bash.variable_assigned", "definition": {"name": "DEST"}, "points": 1},
            {"name": "condición", "type": "bash.node_kind", "definition": {"kind": "if_statement"}, "points": 1},
            {"name": "bucle", "type": "bash.node_kind", "definition": {"kind": "for"}, "points": 1},
            {"name": "pipeline no requerido", "type": "bash.command_used", "definition": {"command": "tar", "args": ["-czf", "$DEST", "laboratorio/fuente"]}, "points": 1},
        ]
        report = evaluate_tests({"bash": source}, tests, language="bash")
        self.assertEqual(report.status, "passed")
        self.assertEqual(report.score, Decimal("10"))

    def test_bash_definitions_reject_unsupported_parameters_and_mixed_files(self):
        with self.assertRaises(ValueError):
            validate_test_definition("bash.command_used", {"command": "tar", "shell": True})
        with self.assertRaises(ValueError):
            validate_test_definition("bash.node_kind", {"kind": "arbitrary_node"})
        with self.assertRaises(ValueError):
            evaluate_tests({"bash": "echo hola", "html": "<p>no</p>"}, [{"type": "bash.syntax_valid", "definition": {}}], language="bash")

    def test_bash_tree_is_parsed_once_for_a_batch(self):
        from unittest.mock import patch

        with patch("grading.evaluator._parse_bash", wraps=__import__("grading.evaluator", fromlist=["_parse_bash"])._parse_bash) as parse:
            evaluate_tests(
                {"bash": "#!/usr/bin/env bash\nVALUE=1\nprintf '%s\\n' \"$VALUE\""},
                [
                    {"name": "sintaxis", "type": "bash.syntax_valid", "definition": {}, "points": 1},
                    {"name": "variable", "type": "bash.variable_assigned", "definition": {"name": "VALUE"}, "points": 1},
                    {"name": "printf", "type": "bash.command_used", "definition": {"command": "printf"}, "points": 1},
                ],
                language="bash",
            )
            parse.assert_called_once()


class SubmissionTests(GradingFactoryMixin, TestCase):
    def test_submission_snapshot_and_attempts(self):
        files = {"html": "<main>ok</main>", "css": "body{}", "javascript": ""}
        first, report = create_submission(self.student, self.assignment, files)
        self.assertEqual(first.attempt_number, 1)
        self.assertEqual(first.files.count(), 3)
        self.assertEqual(report.score, Decimal("10"))
        second, _ = create_submission(self.student, self.assignment, files)
        self.assertEqual(second.attempt_number, 2)
        with self.assertRaises(ValidationError):
            first.save()
        with self.assertRaises(ValidationError):
            first.files.first().save()

    def test_max_attempts_is_enforced(self):
        files = {"html": "<main></main>", "css": "body{}", "javascript": ""}
        create_submission(self.student, self.assignment, files)
        create_submission(self.student, self.assignment, files)
        with self.assertRaises(ValidationError):
            create_submission(self.student, self.assignment, files)

    def test_workspace_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        response = client.post(reverse("workspace_draft_api", args=[self.assignment.id]), data='{"html":"<main/>","css":"","javascript":"","revision":0}', content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_workspace_contract_sets_csrf_and_accepts_optimistic_draft(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        response = client.get(reverse("workspace_draft_api", args=[self.assignment.id]))
        self.assertEqual(response.status_code, 200)
        token = client.cookies["csrftoken"].value
        response = client.post(
            reverse("workspace_draft_api", args=[self.assignment.id]),
            data='{"html":"<main>ok</main>","css":"body{}","javascript":"","revision":0}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["revision"], 1)
        self.assertEqual(response["ETag"], '"1"')

    def test_submission_response_never_exposes_private_test_details(self):
        client = Client()
        client.force_login(self.student)
        response = client.post(
            reverse("workspace_submit_api", args=[self.assignment.id]),
            data='{"html":"<main>ok</main>","css":"body{}","javascript":""}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        encoded = response.content.decode("utf-8")
        self.assertNotIn("criterio secreto", encoded)
        self.assertNotIn('"selector": "script"', encoded)
        self.assertNotIn("solución privada", encoded)
        self.assertEqual(len(response.json()["report"]["results"]), 2)
        self.assertEqual(response.json()["gamification"]["earned_xp"], 100)
        self.assertTrue(response.json()["gamification"]["completed"])

    def test_all_attempt_selection_policies_use_published_grades(self):
        first, _ = create_submission(
            self.student,
            self.assignment,
            {"html": "<main>ok</main>", "css": "body{}", "javascript": ""},
        )
        first_grade = create_manual_grade(
            actor=self.teacher,
            submission=first,
            score=None,
            publish=True,
        )
        second, _ = create_submission(
            self.student,
            self.assignment,
            {"html": "<main>ok</main>", "css": "", "javascript": ""},
        )
        second_grade = create_manual_grade(
            actor=self.teacher,
            submission=second,
            score=None,
            publish=True,
        )

        self.assignment.attempt_policy = Assignment.AttemptPolicy.BEST
        selected, grade, aggregate = _select_attempt(self.assignment, [first, second])
        self.assertEqual((selected, grade, aggregate), (first, first_grade, None))

        self.assignment.attempt_policy = Assignment.AttemptPolicy.LATEST
        selected, grade, aggregate = _select_attempt(self.assignment, [first, second])
        self.assertEqual((selected, grade, aggregate), (second, second_grade, None))

        self.assignment.attempt_policy = Assignment.AttemptPolicy.AVERAGE
        selected, grade, aggregate = _select_attempt(self.assignment, [first, second])
        self.assertEqual(selected, second)
        self.assertEqual(grade, second_grade)
        self.assertEqual(aggregate, Decimal("9.5"))

        now = timezone.now()
        type(first).objects.filter(pk=first.pk).update(submitted_at=now - timedelta(days=2))
        type(second).objects.filter(pk=second.pk).update(submitted_at=now)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assignment.attempt_policy = Assignment.AttemptPolicy.LATEST_BEFORE_DUE
        self.assignment.due_at = now - timedelta(days=1)
        selected, grade, aggregate = _select_attempt(self.assignment, [first, second])
        self.assertEqual((selected, grade, aggregate), (first, first_grade, None))

    def test_gamification_uses_best_automatic_score_without_farming(self):
        first, _ = create_submission(
            self.student,
            self.assignment,
            {"html": "<main>ok</main>", "css": "body{}", "javascript": ""},
        )
        second, _ = create_submission(
            self.student,
            self.assignment,
            {"html": "<main>ok</main>", "css": "", "javascript": ""},
        )
        # Simulate evaluator results from two attempts.  XP must use the best
        # automatic score only and must not depend on teacher publication.
        type(first).objects.filter(pk=first.pk).update(auto_score=Decimal("6"))
        type(second).objects.filter(pk=second.pk).update(auto_score=Decimal("8.75"))
        first.refresh_from_db()
        second.refresh_from_db()
        gamification = gamification_for_assignment(self.student, self.assignment, [first, second])
        self.assertEqual(gamification["best_score"], "8.75")
        self.assertEqual(gamification["earned_xp"], 87)
        self.assertTrue(gamification["completed"])
        self.assertEqual(gamification["progress"], 87)

    def test_gamification_ignores_invalid_or_ungraded_automatic_scores(self):
        submission, _ = create_submission(
            self.student,
            self.assignment,
            {"html": "<main>ok</main>", "css": "body{}", "javascript": ""},
        )
        type(submission).objects.filter(pk=submission.pk).update(auto_score=Decimal("10"), status="received")
        submission.refresh_from_db()
        gamification = gamification_for_assignment(self.student, self.assignment, [submission])
        self.assertIsNone(gamification["best_score"])
        self.assertEqual(gamification["earned_xp"], 0)
        self.assertFalse(gamification["completed"])
