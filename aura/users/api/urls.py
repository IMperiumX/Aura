from django.urls import path

from . import authentication

app_name = "auth"

urlpatterns = [
    path("register/", authentication.RegisterView.as_view(), name="register"),
    path("login/", authentication.LoginView.as_view(), name="login"),
    path("logout/", authentication.LogoutView.as_view(), name="logout"),
    path("profile/", authentication.UserProfileView.as_view(), name="profile"),
]
