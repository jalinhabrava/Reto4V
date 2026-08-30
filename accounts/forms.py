from datetime import timedelta

from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import User


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

    class Meta:
        model = User
        fields = ("username", "display_name", "role", "is_active", "password")

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
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "role", "is_active", "must_change_password")


class LocalSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Repite la contraseña", widget=forms.PasswordInput)
