from django.urls import resolve
from django.urls import reverse

from aura.users.models import User


def test_user_detail(user: User):
    assert reverse("api:user-detail", kwargs={"pk": user.pk}) == f"/api/0/users/{user.pk}/"
    assert resolve(f"/api/0/users/{user.pk}/").view_name == "api:user-detail"


def test_user_list():
    assert reverse("api:user-list") == "/api/0/users/"
    assert resolve("/api/0/users/").view_name == "api:user-list"


def test_user_me():
    assert reverse("api:user-me") == "/api/0/users/me/"
    assert resolve("/api/0/users/me/").view_name == "api:user-me"
