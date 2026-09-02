import secrets

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, F, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    LocalAuthenticationForm,
    LocalSetPasswordForm,
    UserCreateForm,
    UserUpdateForm,
    available_cohorts,
)
from .models import CATALOG_SERVICE_USERNAME, User
from .permissions import role_required

TRACKS = (
    {
        "value": "web",
        "label": "Web · SMR",
        "eyebrow": "Aplicaciones web",
        "description": "HTML, CSS y JavaScript para el módulo de Aplicaciones web.",
    },
    {
        "value": "bash",
        "label": "Bash · ASIR",
        "eyebrow": "Scripting y seguridad",
        "description": "Scripting, copias de seguridad y automatización como apoyo a Seguridad.",
    },
    {
        "value": "python",
        "label": "Python · DAM",
        "eyebrow": "SGE y Odoo",
        "description": "Fundamentos de Python hasta lectura y escritura de archivos para SGE.",
    },
)


def _active_enrollment(user):
    enrollments = getattr(user, "active_enrollment_records", None)
    if enrollments is None:
        enrollments = list(
            user.enrollments.filter(active=True)
            .select_related("cohort", "cohort__academic_year")[:1]
        )
    return enrollments[0] if enrollments else None


def _cohort_payload(user):
    enrollment = _active_enrollment(user)
    if not enrollment:
        return None
    cohort = enrollment.cohort
    return {
        "id": str(cohort.pk),
        "name": cohort.name,
        "track": cohort.track,
        "track_label": cohort.get_track_display(),
        "academic_year": cohort.academic_year.name,
        "active": cohort.active and cohort.academic_year.active,
    }


def _user_payload(user):
    return {
        "id": user.pk,
        "username": user.username,
        "display_name": user.display_name,
        "role": User.Role.ADMIN if user.is_superuser else user.role,
        "is_active": user.is_active,
        "cohort": _cohort_payload(user),
    }


def _admin_users_queryset():
    from learning.models import Enrollment

    active_enrollment = Enrollment.objects.filter(active=True).select_related(
        "cohort", "cohort__academic_year"
    )
    return (
        User.objects.exclude(username=CATALOG_SERVICE_USERNAME)
        .only("id", "username", "display_name", "role", "is_active", "is_superuser")
        .prefetch_related(Prefetch("enrollments", queryset=active_enrollment, to_attr="active_enrollment_records"))
    )


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
    users = _admin_users_queryset()
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"users": [_user_payload(user) for user in users]})
    return render(request, "accounts/user_list.html", {"users": users})


@role_required("admin")
def user_create(request):
    initial = {}
    requested_track = (request.GET.get("track") or "").strip()
    if not request.POST and requested_track in {track["value"] for track in TRACKS}:
        suggested = (
            available_cohorts()
            .filter(track=requested_track)
            .order_by("name", "academic_year__name")
            .first()
        )
        if suggested:
            initial["cohort"] = suggested.pk
    form = UserCreateForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            message = (
                f"Cuenta {user.username} creada con su itinerario."
                if user.role == User.Role.STUDENT
                else f"Cuenta {user.username} creada."
            )
            messages.success(request, message)
            return redirect("user_list")
    return render(request, "accounts/user_form.html", {"form": form, "title": "Crear cuenta"})


@role_required("admin")
def user_update(request, user_id):
    user = get_object_or_404(_admin_users_queryset(), pk=user_id)
    form = UserUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"Cuenta {user.username} actualizada.")
            return redirect("user_list")
    return render(request, "accounts/user_form.html", {"form": form, "title": "Editar cuenta", "user_obj": user})


@role_required("admin")
def user_reset_password(request, user_id):
    if request.method != "POST":
        return HttpResponse(status=405)
    user = get_object_or_404(
        User.objects.exclude(username=CATALOG_SERVICE_USERNAME),
        pk=user_id,
    )
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


@role_required("admin")
def classrooms_overview(request):
    """Show the active local classrooms and their preloaded challenge access."""

    from learning.models import Assignment, Cohort

    cohorts = list(
        Cohort.objects.filter(active=True, academic_year__active=True)
        .exclude(track__isnull=True)
        .exclude(track="")
        .select_related("academic_year")
        .annotate(
            student_count=Count(
                "enrollments",
                filter=Q(
                    enrollments__active=True,
                    enrollments__student__role=User.Role.STUDENT,
                    enrollments__student__is_active=True,
                ),
                distinct=True,
            ),
            challenge_count=Count(
                "assignment_links__assignment",
                filter=Q(
                    assignment_links__assignment__status=Assignment.Status.PUBLISHED,
                    assignment_links__assignment__activity_version__language=F("track"),
                ),
                distinct=True,
            ),
        )
    )
    cohorts_by_track = {track["value"]: [] for track in TRACKS}
    for cohort in cohorts:
        cohorts_by_track.setdefault(cohort.track, []).append(cohort)

    itineraries = []
    for track in TRACKS:
        track_cohorts = cohorts_by_track[track["value"]]
        itineraries.append(
            {
                **track,
                "cohorts": track_cohorts,
                "cohort_count": len(track_cohorts),
                "student_count": sum(cohort.student_count for cohort in track_cohorts),
                # A catalogue assignment is normally shared by all cohorts in
                # an itinerary.  Showing the maximum keeps the card useful
                # when more than one class is running the same track.
                "challenge_count": max(
                    (cohort.challenge_count for cohort in track_cohorts),
                    default=0,
                ),
            }
        )

    context = {
        "itineraries": itineraries,
        "total_students": sum(item["student_count"] for item in itineraries),
        "total_cohorts": sum(item["cohort_count"] for item in itineraries),
        "total_challenges": sum(item["challenge_count"] for item in itineraries),
    }
    if request.headers.get("Accept") == "application/json":
        return JsonResponse(
            {
                "itineraries": [
                    {
                        "value": item["value"],
                        "label": item["label"],
                        "description": item["description"],
                        "cohort_count": item["cohort_count"],
                        "student_count": item["student_count"],
                        "challenge_count": item["challenge_count"],
                        "cohorts": [
                            {
                                "id": str(cohort.pk),
                                "name": cohort.name,
                                "academic_year": cohort.academic_year.name,
                                "student_count": cohort.student_count,
                                "challenge_count": cohort.challenge_count,
                            }
                            for cohort in item["cohorts"]
                        ],
                    }
                    for item in itineraries
                ],
                "total_students": context["total_students"],
                "total_cohorts": context["total_cohorts"],
                "total_challenges": context["total_challenges"],
            }
        )
    return render(request, "accounts/classrooms_overview.html", context)
