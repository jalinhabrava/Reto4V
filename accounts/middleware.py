from django.http import JsonResponse
from django.shortcuts import redirect


class ForcePasswordChangeMiddleware:
    """Keep temporary credentials away from every application view/API."""

    ALLOWED_PATHS = {"/password-change/", "/logout/", "/health/"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and user.must_change_password
            and request.path not in self.ALLOWED_PATHS
            and not request.path.startswith("/static/")
        ):
            if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
                return JsonResponse(
                    {
                        "detail": "Debes cambiar la contraseña temporal antes de continuar.",
                        "code": "password_change_required",
                    },
                    status=403,
                )
            return redirect("password_change")
        return self.get_response(request)
