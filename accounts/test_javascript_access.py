from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from learning.models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Module,
)

from .models import User


class JavaScriptOverrideAdministrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="UnaClaveSegura123!",
            role=User.Role.ADMIN,
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            password="UnaClaveSegura123!",
            role=User.Role.TEACHER,
        )
        self.year = AcademicYear.objects.create(name="2026-2027")
        self.web = Cohort.objects.create(name="1SMR-A", academic_year=self.year, track=Cohort.Track.WEB)
        self.bash = Cohort.objects.create(name="2ASIR-A", academic_year=self.year, track=Cohort.Track.BASH)
        self._published_assignment(self.web, ActivityVersion.Language.WEB, "web")
        self._published_assignment(self.bash, ActivityVersion.Language.BASH, "bash")

    def _published_assignment(self, cohort, language, slug):
        course = Course.objects.create(title=f"Curso {slug}", slug=f"curso-{slug}", created_by=self.admin)
        module = Module.objects.create(course=course, title="Unidad", position=1)
        activity = Activity.objects.create(module=module, title=f"Reto {slug}", slug=slug, created_by=self.admin)
        version = ActivityVersion.objects.create(
            activity=activity,
            version_number=1,
            language=language,
            starter_files={"bash": "echo hola"} if language == "bash" else {"html": "", "css": "", "javascript": ""},
            created_by=self.admin,
        )
        assignment = Assignment.objects.create(
            activity=activity,
            activity_version=version,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.admin,
        )
        AssignmentCohort.objects.create(assignment=assignment, cohort=cohort)

    def _student_data(self, username, cohort, *, javascript_enabled=True):
        return {
            "username": username,
            "display_name": username,
            "role": User.Role.STUDENT,
            "cohort": str(cohort.id),
            "javascript_enabled": "on" if javascript_enabled else "",
            "is_active": "on",
            "password": "UnaClaveSegura123!",
        }

    def test_admin_post_with_csrf_can_enable_web_override_and_disable_it(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.get(reverse("user_create"))
        self.assertEqual(response.status_code, 200)
        token = client.cookies["csrftoken"].value
        response = client.post(
            reverse("user_create"),
            self._student_data("web-student", self.web),
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 302)
        student = User.objects.get(username="web-student")
        self.assertTrue(student.javascript_enabled)

        response = client.get(reverse("user_update", args=[student.id]))
        token = client.cookies["csrftoken"].value
        response = client.post(
            reverse("user_update", args=[student.id]),
            {
                "display_name": student.display_name,
                "role": User.Role.STUDENT,
                "cohort": str(self.web.id),
                "javascript_enabled": "",
                "is_active": "on",
                "must_change_password": "",
            },
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 302)
        student.refresh_from_db()
        self.assertFalse(student.javascript_enabled)

    def test_override_is_ignored_for_non_web_and_non_admin_posts_are_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("user_create"),
            self._student_data("bash-student", self.bash),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.get(username="bash-student").javascript_enabled)

        self.client.force_login(self.teacher)
        self.assertEqual(
            self.client.post(reverse("user_create"), self._student_data("forbidden", self.web)).status_code,
            403,
        )
