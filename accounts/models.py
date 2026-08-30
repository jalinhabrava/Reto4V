from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        TEACHER = "teacher", "Profesor"
        STUDENT = "student", "Alumno"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT, db_index=True)
    display_name = models.CharField(max_length=160, blank=True)
    must_change_password = models.BooleanField(default=False)
    last_failed_login_at = models.DateTimeField(null=True, blank=True)
    failed_login_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("username",)

    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.get_full_name() or self.username
        # Django's admin checks this flag.  Recompute it on every save so
        # demoting an administrator cannot leave a stale staff privilege.
        self.is_staff = bool(self.is_superuser or self.role == self.Role.ADMIN)
        super().save(*args, **kwargs)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_teacher_role(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student_role(self):
        return self.role == self.Role.STUDENT
