from django.conf import settings
from django.utils.translation import gettext_lazy as _
from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from drf_spectacular.contrib.rest_framework_simplejwt import (
    TokenRefreshSerializerExtension,
)
from drf_spectacular.drainage import warn
from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema


class RestAuthLoginView(OpenApiViewExtension):
    target_class = "dj_rest_auth.views.LoginView"

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(responses=self.get_token_serializer_class())
            def post(self, request, *args, **kwargs):
                pass  # pragma: no cover

        return Fixed

    def get_token_serializer_class(self):
        from aura.users.api.serializers import JWTSerializer
        from aura.users.api.serializers import TokenSerializer

        use_jwt = settings.USE_JWT

        if use_jwt:
            return JWTSerializer
        return TokenSerializer


class RestAuthJWTSerializer(OpenApiSerializerExtension):
    target_class = "aura.users.api.serializers.JWTSerializer"

    def map_serializer(self, auto_schema, direction):
        class Fixed(self.target_class):
            from aura.users.api.serializers import UserDetailsSerializer

            user = UserDetailsSerializer()

        return auto_schema._map_serializer(Fixed, direction)  # noqa: SLF001


class CookieTokenRefreshSerializerExtension(TokenRefreshSerializerExtension):
    target_class = "aura.core.authentication.CookieTokenRefreshSerializer"
    optional = True

    def get_name(self):
        return "TokenRefresh"


class SimpleJWTCookieScheme(SimpleJWTScheme):
    """
    sourece: sentry.apidocs.extensions.TokenAuthExtension
    Extension that adds what scopes are needed to access an endpoint to the
    OpenAPI Schema.
    """

    target_class = "aura.core.authentication.JWTCookieAuthentication"
    optional = True
    name = ["jwtHeaderAuth", "jwtCookieAuth"]

    def get_security_requirement(self, auto_schema):
        return [{name: []} for name in self.name]

    def get_security_definition(self, auto_schema: AutoSchema):
        from django.conf import settings

        cookie_name = settings.JWT_AUTH_COOKIE
        if not cookie_name:
            cookie_name = "jwt-auth"
            warn(
                f'"JWT_AUTH_COOKIE" setting required for JWTCookieAuthentication. '
                f"defaulting to {cookie_name}",
            )

        jwt_token_definition = super().get_security_definition(auto_schema) | {
            "description": _("JWT Token from the header (no prefix)"),
        }
        return [
            jwt_token_definition,  # JWT from header
            {
                "type": "apiKey",
                "in": "cookie",
                "name": cookie_name,
            },
        ]
