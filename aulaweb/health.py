from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_view(request):
    """Minimal liveness/readiness endpoint without user or database details."""

    try:
        connection.ensure_connection()
        database_ok = connection.is_usable()
    except Exception:
        database_ok = False
    return JsonResponse(
        {
            "status": "ok" if database_ok else "degraded",
            "database": "ok" if database_ok else "unavailable",
        },
        status=200 if database_ok else 503,
    )
