class RestAuthLoginView(OpenApiViewExtension):
    target_class = "dj_rest_auth.views.LoginView"

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(responses=self.get_token_serializer_class())
            def post(self, request, *args, **kwargs):
                pass  # pragma: no cover

        return Fixed

    def get_token_serializer_class(self):
        from aura.users.api.serializers import JWTSerializer, TokenSerializer

        use_jwt = settings.USE_JWT

        if use_jwt:
            return JWTSerializer
        else:
            return TokenSerializer


class RestAuthJWTSerializer(OpenApiSerializerExtension):
    target_class = "aura.users.api.serializers.JWTSerializer"

    def map_serializer(self, auto_schema, direction):
        class Fixed(self.target_class):
            from aura.users.api.serializers import UserDetailsSerializer

            user = UserDetailsSerializer()

        return auto_schema._map_serializer(Fixed, direction)


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
    name = ["jwtHeaderAuth", "jwtCookieAuth"]  # type: ignore

