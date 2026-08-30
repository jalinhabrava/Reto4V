import secrets

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LocalAuthenticationForm, LocalSetPasswordForm, UserCreateForm, UserUpdateForm
from .models import User
from .permissions import role_required


def login_view(request):
    if request.user.is_authenticated:
        return dashboard_redirect(request)
    form = LocalAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        User.objects.filter(pk=user.pk).update(last_login=timezone.now(), failed_login_count=0)
        if user.must_change_password:
            return redirect("password_change")
        return dashboard_redirect(request)
    if request.method == "POST" and form.errors and not form.login_locked:
        failed_username = (request.POST.get("username") or "").strip()
        if failed_username:
            User.objects.filter(username=failed_username).update(last_failed_login_at=timezone.now(), failed_login_count=F("failed_login_count") + 1)
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"ok": False, "errors": form.errors}, status=429 if form.login_locked else 400)
    return render(request, "accounts/login.html", {"form": form}, status=429 if form.login_locked else 200)


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_redirect(request):
    if request.user.is_superuser or request.user.role == User.Role.ADMIN:
        return redirect("teacher_dashboard")
    if request.user.role == User.Role.TEACHER:
        return redirect("teacher_dashboard")
    return redirect("student_dashboard")


@login_required
def password_change_view(request):
    form = LocalSetPasswordForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"] if hasattr(user, "updated_at") else ["password", "must_change_password"])
        update_session_auth_hash(request, user)
        messages.success(request, "Contraseña actualizada.")
        return redirect("dashboard")
    return render(request, "accounts/password_change.html", {"form": form})


@role_required("admin")
def user_list(request):
    users = User.objects.all().only("id", "username", "display_name", "role", "is_active")
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"users": list(users.values("id", "username", "display_name", "role", "is_active"))})
    return render(request, "accounts/user_list.html", {"users": users})


@role_required("admin")
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Cuenta {user.username} creada.")
        return redirect("user_list")
    return render(request, "accounts/user_form.html", {"form": form, "title": "Crear cuenta"})


@role_required("admin")
def user_update(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    form = UserUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("user_list")
    return render(request, "accounts/user_form.html", {"form": form, "title": "Editar cuenta", "user_obj": user})


@role_required("admin")
def user_reset_password(request, user_id):
    if request.method != "POST":
        return HttpResponse(status=405)
    user = get_object_or_404(User, pk=user_id)
    generated = secrets.token_urlsafe(18)
    user.set_password(generated)
    user.must_change_password = True
    user.failed_login_count = 0
    user.last_failed_login_at = None
    user.save(update_fields=["password", "must_change_password", "failed_login_count", "last_failed_login_at"])
    # The generated value is returned only in this response and is not logged
    # or persisted in clear text.  The admin UI must show it once and discard it.
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"username": user.username, "temporary_password": generated})
    return render(request, "accounts/password_reset_result.html", {"user_obj": user, "temporary_password": generated})
