from django.conf import settings as api_settings
from django.contrib.auth import login as django_login
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import status
from rest_framework.response import Response

sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters(
        "password",
        "old_password",
        "new_password1",
        "new_password2",
    ),
)


class LoginMixin:
    """
    Check the credentials and return the REST Token
    if the credentials are valid and authenticated.
    Calls Django Auth login method to register User ID
    in Django session framework

    Accept the following POST parameters: username, password
    Return the REST Framework Token Object's key.
    """

    user = None
    access_token = None
    token = None

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def process_login(self):
        django_login(self.request, self.user)

    def get_response_serializer(self):
        from aura.users.api.serializers import JWTSerializerWithExpiration
        from aura.users.api.serializers import JWTSerializer
        from aura.users.api.serializers import TokenSerializer

        if api_settings.USE_JWT:
            if api_settings.JWT_AUTH_RETURN_EXPIRATION:
                response_serializer = JWTSerializerWithExpiration
            else:
                response_serializer = JWTSerializer

        else:
            response_serializer = TokenSerializer
        return response_serializer

    def get_response(self):
        serializer_class = self.get_response_serializer()

        if api_settings.USE_JWT:
            from rest_framework_simplejwt.settings import api_settings as jwt_settings
            from django.conf import settings
            access_token_expiration = (
                timezone.now() + jwt_settings.ACCESS_TOKEN_LIFETIME
            )
            refresh_token_expiration = (
                timezone.now() + jwt_settings.REFRESH_TOKEN_LIFETIME
            )
            return_expiration_times = settings.JWT_AUTH_RETURN_EXPIRATION
            auth_httponly = settings.JWT_AUTH_HTTPONLY

            data = {
                "user": self.user,
                "access": self.access_token,
            }

            if not auth_httponly:
                data["refresh"] = self.refresh_token
            else:
                # Wasnt sure if the serializer needed this
                data["refresh"] = ""

            if return_expiration_times:
                data["access_expiration"] = access_token_expiration
                data["refresh_expiration"] = refresh_token_expiration

            serializer = serializer_class(
                instance=data,
                context=self.get_serializer_context(),
            )
        elif self.token:
            serializer = serializer_class(
                instance=self.token,
                context=self.get_serializer_context(),
            )
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)

        response = Response(serializer.data, status=status.HTTP_200_OK)
        if api_settings.USE_JWT:
            from aura.core.authentication import set_jwt_cookies

            set_jwt_cookies(response, self.access_token, self.refresh_token)
        return response
