"""Exercise the published catalogue through the student HTTP workflow."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from learning.management.commands.seed_javascript import CHALLENGES as JS_CHALLENGES
from learning.management.commands.seed_web import CHALLENGES as HTML_CSS_CHALLENGES
from learning.models import Assignment, Cohort, Course
from learning.services import set_student_cohort


class PublishedWebPathwayFlowTests(TestCase):
    def test_last_html_css_submission_unlocks_the_separate_javascript_workspace(self):
        owner = User.objects.create_user(username="catalogue-owner", role=User.Role.TEACHER)
        student = User.objects.create_user(username="pathway-student", role=User.Role.STUDENT)
        call_command(
            "seed_web", owner=owner.username, cohort="Web-flow",
            academic_year="2026-2027", stdout=StringIO(),
        )
        set_student_cohort(student, Cohort.objects.get(name="Web-flow"))
        self.client.force_login(student)

        dashboard_url = reverse("student_dashboard")
        initial = self.client.get(dashboard_url, HTTP_ACCEPT="application/json").json()
        self.assertEqual(
            len(initial["assignments"]), len(HTML_CSS_CHALLENGES) + len(JS_CHALLENGES),
        )
        javascript_rows = [
            row for row in initial["assignments"] if row["pathway"] == Course.WebStage.JAVASCRIPT
        ]
        self.assertTrue(all(row["locked"] for row in javascript_rows))
        javascript_id = javascript_rows[0]["id"]
        detail_url = reverse("workspace_detail_api", args=[javascript_id])
        self.assertEqual(self.client.get(detail_url).status_code, 404)

        html_css = list(
            Assignment.objects.filter(
                cohort_links__cohort__name="Web-flow",
                activity__module__course__web_stage=Course.WebStage.HTML_CSS,
                status=Assignment.Status.PUBLISHED,
            ).select_related("activity_version").order_by("activity__title")
        )
        for index, assignment in enumerate(html_css):
            if index == 0:
                checks = self.client.post(
                    reverse("workspace_tests_api", args=[assignment.id]),
                    {"files": assignment.activity_version.reference_solution},
                    content_type="application/json",
                )
                self.assertEqual(checks.status_code, 200)
                checked = self.client.get(dashboard_url, HTTP_ACCEPT="application/json").json()
                row = next(row for row in checked["assignments"] if row["id"] == str(assignment.id))
                self.assertFalse(row["completed"])
                self.assertEqual(row["submissions"], 0)
                self.assertEqual(row["earned_xp"], 0)
            # Access is still denied immediately before the last prerequisite.
            if index == len(html_css) - 1:
                self.assertEqual(self.client.get(detail_url).status_code, 404)
            response = self.client.post(
                reverse("workspace_submit_api", args=[assignment.id]),
                {"files": assignment.activity_version.reference_solution},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 201, response.content)
            self.assertTrue(response.json()["gamification"]["completed"], assignment.title)
            immediate = self.client.get(dashboard_url, HTTP_ACCEPT="application/json").json()
            row = next(row for row in immediate["assignments"] if row["id"] == str(assignment.id))
            self.assertEqual(row["submissions"], 1)
            self.assertEqual(row["status"], "submitted")
            for key in ("completed", "earned_xp", "progress"):
                self.assertEqual(row[key], response.json()["gamification"][key])
            current_pathways = {row["id"]: row for row in immediate["pathways"]}
            self.assertEqual(current_pathways["html_css"]["completed"], index + 1)
            self.assertEqual(current_pathways["javascript"]["locked"], index < len(html_css) - 1)

        unlocked = self.client.get(dashboard_url, HTTP_ACCEPT="application/json").json()
        pathways = {row["id"]: row for row in unlocked["pathways"]}
        self.assertEqual(pathways["html_css"]["completed"], len(HTML_CSS_CHALLENGES))
        self.assertFalse(pathways["javascript"]["locked"])
        self.assertFalse(pathways["javascript"]["unlock_override"])
        workspace = self.client.get(detail_url)
        self.assertEqual(workspace.status_code, 200)
        self.assertEqual(workspace.json()["version"]["editor_files"], ["javascript"])
        javascript = Assignment.objects.select_related("activity_version").get(id=javascript_id)
        submission = self.client.post(
            reverse("workspace_submit_api", args=[javascript_id]),
            {"files": javascript.activity_version.reference_solution},
            content_type="application/json",
        )
        self.assertEqual(submission.status_code, 201, submission.content)
        self.assertTrue(submission.json()["gamification"]["completed"])
