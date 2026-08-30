from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import User


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
