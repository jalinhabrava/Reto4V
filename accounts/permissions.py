from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden, JsonResponse


def role_required(*roles):
    """Require authentication and one of the application roles.

    This decorator is intentionally usable by both HTML views and JSON
    endpoints.  JSON callers get a status response rather than an HTML login
    page, while browser navigation follows Django's normal login flow.
    """

    allowed = set(roles)

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if (
                    request.path.startswith("/api/")
                    or request.headers.get("Accept") == "application/json"
                ):
                    return JsonResponse({"detail": "Autenticación requerida."}, status=401)
                return redirect_to_login(request.get_full_path())
            if (
                getattr(request.user, "is_superuser", False)
                or getattr(request.user, "role", None) in allowed
            ):
                return view(request, *args, **kwargs)
            if (
                request.path.startswith("/api/")
                or request.headers.get("Accept") == "application/json"
            ):
                return JsonResponse(
                    {"detail": "No tienes permiso para esta operación."}, status=403
                )
            return HttpResponseForbidden("No tienes permiso para esta operación.")

        return wrapped

    return decorator


def is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == "admin"))


def is_teacher(user):
    return bool(
        user and user.is_authenticated and (user.is_superuser or user.role in {"admin", "teacher"})
    )
