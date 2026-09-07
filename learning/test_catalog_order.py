"""The student sees the teaching sequence even after a teacher renames a step."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from learning.management.commands.seed_bash import CHALLENGES as BASH_CHALLENGES
from learning.management.commands.seed_javascript import CHALLENGES as JS_CHALLENGES
from learning.management.commands.seed_python import CHALLENGES as PYTHON_CHALLENGES
from learning.management.commands.seed_web import CHALLENGES as WEB_CHALLENGES
from learning.management.commands.seed_web import TRACK_SLUG, WEB_CATALOG_VERSION
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
from learning.services import set_student_cohort


class CatalogOrderTests(TestCase):
    def test_upgrade_replaces_a_carried_over_semantics_title_in_the_student_workspace(self):
        owner = User.objects.create_user(username="legacy-order-owner", role=User.Role.TEACHER)
        student = User.objects.create_user(username="legacy-order-student", role=User.Role.STUDENT)
        year = AcademicYear.objects.create(name="2026-2027")
        cohort = Cohort.objects.create(name="legacy-order-web", academic_year=year, track="web")
        course = Course.objects.create(slug=TRACK_SLUG, title="Web histórico", created_by=owner)
        module = Module.objects.create(course=course, title="Web histórico", position=1)
        activity = Activity.objects.create(
            module=module, slug=WEB_CHALLENGES[0]["slug"],
            title="01 · Estructura semántica", created_by=owner,
        )
        old_files = {"html": "<main>Trabajo anterior</main>", "css": "", "javascript": ""}
        version = ActivityVersion.objects.create(
            activity=activity, version_number=4, language="web",
            instructions="Enunciado anterior", starter_files=old_files, created_by=owner,
        )
        old_assignment = Assignment.objects.create(
            activity=activity, activity_version=version, created_by=owner,
            status=Assignment.Status.PUBLISHED, title_override="01 · Estructura semántica",
        )
        AssignmentCohort.objects.create(assignment=old_assignment, cohort=cohort)
        draft = Draft.objects.create(
            assignment=old_assignment, activity_version=version, student=student,
            files=old_files, revision=2,
        )
        set_student_cohort(student, cohort)
        call_command("seed_web", owner=owner.username, cohort=cohort.name,
                     academic_year=year.name, stdout=StringIO())
        self.client.force_login(student)
        dashboard = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json").json()
        rows = [row for row in dashboard["assignments"] if row["pathway"] == "html_css"]
        self.assertEqual(len(rows), len(WEB_CHALLENGES))
        self.assertEqual(rows[0]["title"], WEB_CHALLENGES[0]["title"])
        self.assertEqual(rows[0]["position"], 1)
        detail = self.client.get(reverse("workspace_detail_api", args=[rows[0]["id"]])).json()
        self.assertEqual(detail["version"]["number"], WEB_CATALOG_VERSION)
        self.assertEqual(detail["version"]["editor_files"], ["html"])
        self.assertEqual(detail["version"]["files"]["html"], WEB_CHALLENGES[0]["starter"]["html"])
        self.assertEqual(detail["draft"]["revision"], 0)
        self.assertNotEqual(detail["draft"]["id"], str(draft.pk))
        self.assertEqual(detail["draft"]["files"]["html"], WEB_CHALLENGES[0]["starter"]["html"])
        old_assignment.refresh_from_db()
        version.refresh_from_db()
        draft.refresh_from_db()
        self.assertEqual(old_assignment.status, Assignment.Status.ARCHIVED)
        self.assertEqual(old_assignment.title_override, "01 · Estructura semántica")
        self.assertEqual(version.instructions, "Enunciado anterior")
        self.assertEqual(draft.files, old_files)
        self.assertEqual(draft.assignment_id, old_assignment.pk)
        self.assertEqual(draft.activity_version_id, version.pk)

    def test_student_dashboard_and_workspace_keep_teaching_order_with_custom_titles(self):
        owner = User.objects.create_user(username="order-owner", role=User.Role.TEACHER)
        student = User.objects.create_user(username="order-student", role=User.Role.STUDENT)
        self.client.force_login(student)
        for command, track, challenges_by_pathway in (
            ("seed_web", "web", {"html_css": WEB_CHALLENGES, "javascript": JS_CHALLENGES}),
            ("seed_bash", "bash", {"bash": BASH_CHALLENGES}),
            ("seed_python", "python", {"python": PYTHON_CHALLENGES}),
        ):
            with self.subTest(track=track):
                cohort_name = f"order-{track}"
                call_command(command, owner=owner.username, cohort=cohort_name,
                             academic_year="2026-2027", stdout=StringIO())
                cohort = Cohort.objects.get(name=cohort_name)
                set_student_cohort(student, cohort)
                assignments = Assignment.objects.filter(
                    cohort_links__cohort=cohort, status=Assignment.Status.PUBLISHED,
                ).select_related("activity", "activity_version", "activity__module__course")
                for assignment in assignments:
                    # These titles deliberately reverse alphabetical order.
                    if assignment.activity.position == 1:
                        assignment.activity.title = "Z: comienzo personalizado"
                    elif assignment.activity.position == 2:
                        assignment.activity.title = "A: segundo paso personalizado"
                    else:
                        continue
                    assignment.activity.save(update_fields=["title"])
                    assignment.title_override = assignment.activity.title
                    assignment.save(update_fields=["title_override"])
                # Restarting bootstrap must also keep this sequence and titles.
                call_command(command, owner=owner.username, cohort=cohort_name,
                             academic_year="2026-2027", stdout=StringIO())
                payload = self.client.get(reverse("student_dashboard"),
                                          HTTP_ACCEPT="application/json").json()
                for pathway, challenges in challenges_by_pathway.items():
                    rows = [row for row in payload["assignments"] if row["pathway"] == pathway]
                    self.assertEqual([row["position"] for row in rows],
                                     list(range(1, len(challenges) + 1)))
                    self.assertEqual(rows[0]["title"], "Z: comienzo personalizado")
                    self.assertEqual(rows[1]["title"], "A: segundo paso personalizado")
                    self.assertEqual(
                        [str(assignments.get(activity__slug=item["slug"]).pk) for item in challenges],
                        [row["id"] for row in rows],
                    )
                    if not rows[0]["locked"]:
                        detail = self.client.get(reverse("workspace_detail_api", args=[rows[0]["id"]]))
                        self.assertEqual(detail.status_code, 200)
                        self.assertEqual(detail.json()["position"], 1)
                        self.assertEqual(detail.json()["title"], "Z: comienzo personalizado")
                        files = detail.json()["version"]["editor_files"]
                        expected_files = set(challenges[0]["starter"]) if track == "web" else {track}
                        self.assertEqual(set(files), expected_files)
