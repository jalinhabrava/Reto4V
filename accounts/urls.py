from django.urls import path

from .views import user_create, user_list, user_reset_password, user_update

urlpatterns = [
    path("users/", user_list, name="user_list"),
    path("users/new/", user_create, name="user_create"),
    path("users/<int:user_id>/edit/", user_update, name="user_update"),
    path("users/<int:user_id>/reset-password/", user_reset_password, name="user_reset_password"),
]
