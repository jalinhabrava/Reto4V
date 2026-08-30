from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AulaWebUserAdmin(UserAdmin):
    list_display = ("username", "display_name", "role", "is_active", "last_login")
    list_filter = ("role", "is_active", "must_change_password")
    fieldsets = UserAdmin.fieldsets + (
        ("AulaWeb", {"fields": ("display_name", "role", "must_change_password")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (("AulaWeb", {"fields": ("display_name", "role")}),)
