from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CATALOG_SERVICE_USERNAME, User


@admin.register(User)
class ProgrammyUserAdmin(UserAdmin):
    """Keep account mutations in the local Programmy4V admin panel.

    The Django admin remains useful as an audit view for administrators, but
    its generic User form cannot synchronise the student's active Enrollment.
    Disabling the mutation endpoints here prevents a direct ``/admin/`` POST
    from creating an account that has no itinerary or from changing a role
    without clearing its enrollment.  The user list and password-reset
    workflow under ``/admin-ui/users/`` use the application services instead.
    """

    list_display = ("username", "display_name", "role", "is_active", "last_login")
    list_filter = ("role", "is_active", "must_change_password")
    fieldsets = UserAdmin.fieldsets + (
        ("Programmy4V", {"fields": ("display_name", "role", "must_change_password")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (("Programmy4V", {"fields": ("display_name", "role")}),)

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(username=CATALOG_SERVICE_USERNAME)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)
