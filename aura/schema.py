from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class JWTCookieAuthExtensionScheme(OpenApiAuthenticationExtension):
    """
    sourece: sentry.apidocs.extensions.TokenAuthExtension
    Extension that adds what scopes are needed to access an endpoint to the
    OpenAPI Schema.
    """

    target_class = "aura.core.jwt_auth.JWTCookieAuthentication"
    name = "jwt_cookie_auth"

    def get_security_definition(
        self,
        auto_schema: AutoSchema,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        return build_bearer_security_scheme_object(
            header_name="AUTHORIZATION",
            token_prefix="Bearer",  # NOQA: S106
            bearer_format="JWT",
        )
