from datetime import timedelta

from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.utils import timezone

from learning.models import Assignment, Cohort

from .models import CATALOG_SERVICE_USERNAME, User
from .services import save_user_with_cohort


def available_cohorts():
    """Return cohorts that can be selected for a new or existing student.

    Legacy cohorts created before itineraries were introduced intentionally
    remain in the database, but they are not selectable from the account
    workflow until an administrator gives them a track and the catalog has at
    least one published challenge in that same language.  Keeping this filter
    here also means a closed academic year cannot accidentally receive new
    students from the local dashboard.
    """

    published_assignment = Assignment.objects.filter(
        cohort_links__cohort=OuterRef("pk"),
        status=Assignment.Status.PUBLISHED,
        activity_version__language=OuterRef("track"),
    )
    return (
        Cohort.objects.filter(active=True, academic_year__active=True)
        .exclude(track__isnull=True)
        .exclude(track="")
        .filter(Exists(published_assignment))
        .select_related("academic_year")
        .order_by("track", "name", "academic_year__name")
    )


class CohortChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        track_label = obj.get_track_display() if obj.track else "Itinerario sin nombre"
        return f"{track_label} · {obj.name} · {obj.academic_year.name}"


class LocalAuthenticationForm(AuthenticationForm):
    MAX_FAILURES = 10
    LOCKOUT_WINDOW = timedelta(minutes=5)

    username = forms.CharField(label="Usuario", max_length=150)
    password = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_locked = False

    def clean(self):
        username = (self.data.get("username") or "").strip()
        user = User.objects.filter(username=username).only("failed_login_count", "last_failed_login_at").first()
        if (
            user
            and user.failed_login_count >= self.MAX_FAILURES
            and user.last_failed_login_at
            and timezone.now() - user.last_failed_login_at < self.LOCKOUT_WINDOW
        ):
            self.login_locked = True
            raise ValidationError(
                "Demasiados intentos. Espera cinco minutos antes de volver a probar.",
                code="login_locked",
            )
        return super().clean()


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña inicial",
        required=False,
        widget=forms.PasswordInput,
        help_text="Si se deja vacía, crea la cuenta bloqueada; usa después “Restablecer contraseña”.",
    )
    cohort = CohortChoiceField(
        queryset=Cohort.objects.none(),
        label="Ciclo e itinerario",
        required=False,
        empty_label="Selecciona un ciclo e itinerario",
        help_text=(
            "Obligatorio para alumnos. Al guardarlo, se activan sus retos "
            "precargados y el primero aparecerá al iniciar sesión."
        ),
    )

    class Meta:
        model = User
        fields = ("username", "display_name", "role", "is_active", "password")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cohort"].queryset = available_cohorts()
        self.order_fields(("username", "display_name", "role", "cohort", "is_active", "password"))

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if username.casefold() == CATALOG_SERVICE_USERNAME.casefold():
            raise ValidationError("Ese usuario está reservado para el catálogo interno.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        cohort = cleaned_data.get("cohort")
        if role == User.Role.STUDENT and cohort is None:
            self.add_error("cohort", "Selecciona un ciclo e itinerario para crear la cuenta de alumno.")
        elif role != User.Role.STUDENT:
            # A teacher/admin can never keep an enrollment.  Discarding a
            # value submitted by a stale form makes role changes predictable
            # and lets the transaction service clear any old enrollment.
            cleaned_data["cohort"] = None
        return cleaned_data

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
            user.must_change_password = True
        if commit:
            save_user_with_cohort(user, self.cleaned_data.get("cohort"))
        return user


class UserUpdateForm(forms.ModelForm):
    cohort = CohortChoiceField(
        queryset=Cohort.objects.none(),
        label="Ciclo e itinerario",
        required=False,
        empty_label="Sin itinerario (solo cuentas no académicas)",
        help_text=(
            "Para un alumno, cambiar este valor cambia su acceso al instante: "
            "solo verá los retos publicados de su nuevo itinerario."
        ),
    )

    class Meta:
        model = User
        fields = ("display_name", "role", "is_active", "must_change_password")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cohort"].queryset = available_cohorts()
        self.order_fields(("display_name", "role", "cohort", "is_active", "must_change_password"))
        if self.instance and self.instance.pk and self.instance.is_superuser:
            self.initial["role"] = User.Role.ADMIN
        if self.instance and self.instance.pk:
            enrollment = getattr(self.instance, "active_enrollment_records", None)
            if enrollment is None:
                enrollment = list(
                    self.instance.enrollments.filter(active=True)
                    .select_related("cohort", "cohort__academic_year")[:1]
                )
            if enrollment:
                self.initial["cohort"] = enrollment[0].cohort_id

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        if self.instance and self.instance.is_superuser:
            role = User.Role.ADMIN
            cleaned_data["role"] = role
        if role != User.Role.STUDENT:
            cleaned_data["cohort"] = None
        elif cleaned_data.get("cohort") is None:
            self.add_error("cohort", "Selecciona un ciclo e itinerario para una cuenta de alumno.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            save_user_with_cohort(user, self.cleaned_data.get("cohort"))
        return user


class LocalSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Repite la contraseña", widget=forms.PasswordInput)
