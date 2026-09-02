from datetime import timedelta

from django.test import TestCase
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
    Enrollment,
    Module,
)

from .forms import UserCreateForm, UserUpdateForm
from .models import CATALOG_SERVICE_USERNAME, User


class AccountTests(TestCase):
    def test_password_is_hashed_and_role_redirects(self):
        user = User.objects.create_user(username="alumno", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        self.assertNotEqual(user.password, "UnaClaveSegura123!")
        self.assertTrue(user.check_password("UnaClaveSegura123!"))
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("student_dashboard"))

    def test_deactivated_user_cannot_access_dashboard(self):
        user = User.objects.create_user(username="alumno", password="UnaClaveSegura123!", role=User.Role.STUDENT, is_active=False)
        self.client.force_login(user)
        response = self.client.get(reverse("student_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_demoting_admin_removes_staff_flag(self):
        user = User.objects.create_user(username="admin", password="UnaClaveSegura123!", role=User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        user.role = User.Role.TEACHER
        user.save()
        self.assertFalse(user.is_staff)

    def test_createsuperuser_is_always_an_admin_role(self):
        user = User.objects.create_superuser(
            username="root",
            password="UnaClaveSegura123!",
            email="root@example.test",
        )
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


    def test_logout_requires_post(self):
        user = User.objects.create_user(username="alumno", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))

    def test_temporary_password_cannot_bypass_forced_change(self):
        user = User.objects.create_user(
            username="temporal",
            password="UnaClaveTemporal123!",
            role=User.Role.STUDENT,
            must_change_password=True,
        )
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse("student_dashboard")), reverse("password_change"))
        response = self.client.get(reverse("student_dashboard_api"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "password_change_required")
        self.assertEqual(self.client.get(reverse("password_change")).status_code, 200)

    def test_repeated_login_failures_apply_a_short_lockout(self):
        user = User.objects.create_user(
            username="bloqueado",
            password="UnaClaveSegura123!",
            role=User.Role.STUDENT,
            failed_login_count=10,
            last_failed_login_at=timezone.now(),
        )
        response = self.client.post(
            reverse("login"),
            {"username": user.username, "password": "UnaClaveSegura123!"},
        )
        self.assertEqual(response.status_code, 429)

        User.objects.filter(pk=user.pk).update(last_failed_login_at=timezone.now() - timedelta(minutes=6))
        response = self.client.post(
            reverse("login"),
            {"username": user.username, "password": "UnaClaveSegura123!"},
        )
        self.assertRedirects(response, reverse("student_dashboard"))


class AdminItineraryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="UnaClaveSegura123!",
            role=User.Role.ADMIN,
        )
        self.year = AcademicYear.objects.create(name="2026-2027", active=True)
        self.web = Cohort.objects.create(name="1SMR-A", academic_year=self.year, track=Cohort.Track.WEB)
        self.bash = Cohort.objects.create(name="2ASIR-A", academic_year=self.year, track=Cohort.Track.BASH)
        self.python = Cohort.objects.create(name="2DAM-A", academic_year=self.year, track=Cohort.Track.PYTHON)
        # The account workflow must never offer an itinerary that would leave
        # a newly-created student with an empty dashboard.  Keep Web empty in
        # this fixture so the regression tests can assert that it is filtered
        # out; Bash and Python receive one published challenge each for the
        # create/switch form tests below.
        catalog_course = Course.objects.create(
            title="Rutas de prueba",
            slug="rutas-de-prueba",
            created_by=self.admin,
        )
        catalog_module = Module.objects.create(course=catalog_course, title="Unidad", position=1)
        for index, cohort in enumerate((self.bash, self.python), start=1):
            activity = Activity.objects.create(
                module=catalog_module,
                title=f"Reto de prueba {index}",
                slug=f"reto-de-prueba-{index}",
                status=Activity.Status.PUBLISHED,
                created_by=self.admin,
            )
            version = ActivityVersion.objects.create(
                activity=activity,
                version_number=1,
                language=cohort.track,
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
        self.client.force_login(self.admin)

    def _student_data(self, username="alumno", cohort=None, role=User.Role.STUDENT):
        return {
            "username": username,
            "display_name": "Alumno de prueba",
            "role": role,
            "cohort": str((cohort or self.web).pk) if role == User.Role.STUDENT else "",
            "is_active": "on",
            "password": "UnaClaveSegura123!",
        }

    def test_create_student_requires_cohort_and_enrolls_atomically(self):
        response = self.client.post(reverse("user_create"), self._student_data(cohort=self.python))
        self.assertRedirects(response, reverse("user_list"))
        student = User.objects.get(username="alumno")
        enrollment = Enrollment.objects.get(student=student, active=True)
        self.assertEqual(enrollment.cohort, self.python)

        missing = self._student_data(username="sin-itinerario")
        missing["cohort"] = ""
        response = self.client.post(reverse("user_create"), missing)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecciona un ciclo e itinerario")
        self.assertFalse(User.objects.filter(username="sin-itinerario").exists())

    def test_update_switches_the_single_active_enrollment(self):
        student = User.objects.create_user(username="alumno", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        first = Enrollment.objects.create(student=student, cohort=self.web)
        response = self.client.post(
            reverse("user_update", args=[student.pk]),
            {
                "display_name": student.display_name,
                "role": User.Role.STUDENT,
                "cohort": str(self.bash.pk),
                "is_active": "on",
                "must_change_password": "",
            },
        )
        self.assertRedirects(response, reverse("user_list"))
        first.refresh_from_db()
        self.assertFalse(first.active)
        self.assertTrue(Enrollment.objects.get(student=student, cohort=self.bash).active)
        self.assertEqual(Enrollment.objects.filter(student=student, active=True).count(), 1)

    def test_changing_role_away_from_student_clears_enrollment(self):
        student = User.objects.create_user(username="alumno", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        Enrollment.objects.create(student=student, cohort=self.web)
        response = self.client.post(
            reverse("user_update", args=[student.pk]),
            {
                "display_name": student.display_name,
                "role": User.Role.TEACHER,
                "cohort": "",
                "is_active": "on",
                "must_change_password": "",
            },
        )
        self.assertRedirects(response, reverse("user_list"))
        student.refresh_from_db()
        self.assertEqual(student.role, User.Role.TEACHER)
        self.assertFalse(Enrollment.objects.filter(student=student, active=True).exists())
        self.assertTrue(Enrollment.objects.filter(student=student).exists())

    def test_user_list_and_json_expose_itinerary_without_n_plus_one(self):
        student = User.objects.create_user(username="alumno", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        Enrollment.objects.create(student=student, cohort=self.web)
        response = self.client.get(reverse("user_list"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["users"]
        row = next(item for item in payload if item["username"] == "alumno")
        self.assertEqual(row["cohort"]["track"], Cohort.Track.WEB)
        self.assertEqual(row["cohort"]["name"], self.web.name)

    def test_catalog_service_account_is_hidden_and_not_editable(self):
        catalog = User.objects.create_user(
            username=CATALOG_SERVICE_USERNAME,
            password="UnaClaveSegura123!",
            role=User.Role.TEACHER,
            is_active=False,
        )
        response = self.client.get(reverse("user_list"))
        self.assertNotContains(response, CATALOG_SERVICE_USERNAME)
        self.assertEqual(self.client.get(reverse("user_update", args=[catalog.pk])).status_code, 404)
        self.assertEqual(
            self.client.post(reverse("user_reset_password", args=[catalog.pk])).status_code,
            404,
        )
        form = UserCreateForm(data=self._student_data(username=CATALOG_SERVICE_USERNAME))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_classrooms_overview_is_admin_only_and_reports_catalog_access(self):
        course = Course.objects.create(
            title="Web",
            slug="test-web",
            created_by=self.admin,
        )
        module = Module.objects.create(course=course, title="Módulo", position=1)
        activity = Activity.objects.create(
            module=module,
            title="Reto",
            slug="reto",
            status=Activity.Status.PUBLISHED,
            created_by=self.admin,
        )
        version = ActivityVersion.objects.create(
            activity=activity,
            version_number=1,
            language=ActivityVersion.Language.WEB,
            created_by=self.admin,
        )
        assignment = Assignment.objects.create(
            activity=activity,
            activity_version=version,
            status=Assignment.Status.PUBLISHED,
            created_by=self.admin,
        )
        AssignmentCohort.objects.create(assignment=assignment, cohort=self.web)
        student = User.objects.create_user(username="alumno", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        Enrollment.objects.create(student=student, cohort=self.web)

        response = self.client.get(reverse("classrooms_overview"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        web = next(item for item in response.json()["itineraries"] if item["value"] == Cohort.Track.WEB)
        self.assertEqual(web["student_count"], 1)
        self.assertEqual(web["challenge_count"], 1)
        self.assertEqual(web["cohorts"][0]["name"], self.web.name)

        self.client.force_login(student)
        self.assertEqual(self.client.get(reverse("classrooms_overview")).status_code, 403)

    def test_forms_only_offer_active_tracked_cohorts_in_active_year(self):
        inactive_year = AcademicYear.objects.create(name="2025-2026", active=False)
        Cohort.objects.create(name="legacy", academic_year=self.year, track="")
        Cohort.objects.create(name="inactiva", academic_year=self.year, active=False, track=Cohort.Track.WEB)
        Cohort.objects.create(name="pasada", academic_year=inactive_year, track=Cohort.Track.BASH)
        values = set(UserCreateForm().fields["cohort"].queryset.values_list("pk", flat=True))
        self.assertEqual(values, {self.bash.pk, self.python.pk})

    def test_student_form_excludes_tracked_cohort_without_published_challenges(self):
        form = UserCreateForm()
        self.assertNotIn(self.web.pk, set(form.fields["cohort"].queryset.values_list("pk", flat=True)))

        # A published link to the wrong language is not enough to make a
        # cohort selectable: otherwise a legacy/misconfigured link could
        # still produce an empty itinerary after the student's route filter.
        mismatch_course = Course.objects.create(
            title="Ruta cruzada",
            slug="ruta-cruzada",
            created_by=self.admin,
        )
        mismatch_module = Module.objects.create(course=mismatch_course, title="Unidad", position=1)
        mismatch_activity = Activity.objects.create(
            module=mismatch_module,
            title="Bash en Web",
            slug="bash-en-web",
            status=Activity.Status.PUBLISHED,
            created_by=self.admin,
        )
        mismatch_version = ActivityVersion.objects.create(
            activity=mismatch_activity,
            version_number=1,
            language=ActivityVersion.Language.BASH,
            created_by=self.admin,
        )
        mismatch_assignment = Assignment.objects.create(
            activity=mismatch_activity,
            activity_version=mismatch_version,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.admin,
        )
        AssignmentCohort.objects.create(assignment=mismatch_assignment, cohort=self.web)
        self.assertNotIn(self.web.pk, set(UserCreateForm().fields["cohort"].queryset.values_list("pk", flat=True)))
        overview = self.client.get(reverse("classrooms_overview"), HTTP_ACCEPT="application/json")
        web_summary = next(
            item for item in overview.json()["itineraries"] if item["value"] == Cohort.Track.WEB
        )
        self.assertEqual(web_summary["challenge_count"], 0)

        bound = self._student_data(username="sin-retos", cohort=self.web)
        response = self.client.post(reverse("user_create"), bound)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecciona un ciclo e itinerario")
        self.assertFalse(User.objects.filter(username="sin-retos").exists())

    def test_superuser_edit_is_presented_as_admin_without_cohort(self):
        superuser = User.objects.create_superuser(
            username="root",
            password="UnaClaveSegura123!",
            email="root@example.test",
        )
        form = UserUpdateForm(instance=superuser)
        self.assertEqual(form.initial["role"], User.Role.ADMIN)
        self.assertFalse(form.is_bound)
        bound = UserUpdateForm(
            data={
                "display_name": "Root",
                "role": User.Role.STUDENT,
                "cohort": "",
                "is_active": "on",
                "must_change_password": "",
            },
            instance=superuser,
        )
        self.assertTrue(bound.is_valid())
        bound.save()
        superuser.refresh_from_db()
        self.assertEqual(superuser.role, User.Role.ADMIN)
        self.assertFalse(Enrollment.objects.filter(student=superuser, active=True).exists())


class AdminMutationGuardTests(TestCase):
    """The generic Django admin must not bypass the local academic services."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="root",
            password="UnaClaveSegura123!",
            email="root@example.test",
        )
        self.student = User.objects.create_user(
            username="alumno",
            password="UnaClaveSegura123!",
            role=User.Role.STUDENT,
        )
        year = AcademicYear.objects.create(name="2026-2027", active=True)
        cohort = Cohort.objects.create(name="1SMR-A", academic_year=year, track=Cohort.Track.WEB)
        Enrollment.objects.create(student=self.student, cohort=cohort)
        course = Course.objects.create(title="Web", slug="web-admin-guard", created_by=self.admin)
        module = Module.objects.create(course=course, title="Unidad", position=1)
        activity = Activity.objects.create(
            module=module,
            title="Reto",
            slug="reto-admin-guard",
            status=Activity.Status.PUBLISHED,
            created_by=self.admin,
        )
        version = ActivityVersion.objects.create(
            activity=activity,
            version_number=1,
            language=ActivityVersion.Language.WEB,
            created_by=self.admin,
        )
        assignment = Assignment.objects.create(
            activity=activity,
            activity_version=version,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.admin,
        )
        self.assignment_cohort = AssignmentCohort.objects.create(assignment=assignment, cohort=cohort)
        self.enrollment = Enrollment.objects.get(student=self.student, active=True)
        self.client.force_login(self.admin)

    def test_user_admin_is_read_only_and_blocks_account_mutations(self):
        add_url = reverse("admin:accounts_user_add")
        change_url = reverse("admin:accounts_user_change", args=[self.student.pk])
        self.assertEqual(self.client.get(add_url).status_code, 403)
        self.assertEqual(self.client.get(change_url).status_code, 200)
        response = self.client.post(change_url, {"display_name": "Manipulado", "role": User.Role.TEACHER})
        self.assertEqual(response.status_code, 403)
        self.student.refresh_from_db()
        self.assertEqual(self.student.display_name, "alumno")
        self.assertEqual(self.student.role, User.Role.STUDENT)

    def test_enrollment_and_assignment_cohort_admin_are_read_only(self):
        for model_name, obj in (
            ("enrollment", self.enrollment),
            ("assignmentcohort", self.assignment_cohort),
        ):
            add_url = reverse(f"admin:learning_{model_name}_add")
            change_url = reverse(f"admin:learning_{model_name}_change", args=[obj.pk])
            self.assertEqual(self.client.get(add_url).status_code, 403)
            self.assertEqual(self.client.get(change_url).status_code, 200)
            response = self.client.post(change_url, {})
            self.assertEqual(response.status_code, 403)

        self.assertTrue(Enrollment.objects.filter(pk=self.enrollment.pk, active=True).exists())
        self.assertTrue(AssignmentCohort.objects.filter(pk=self.assignment_cohort.pk).exists())
