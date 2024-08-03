

class SimpleJWTCookieScheme(SimpleJWTScheme):
    """
    sourece: sentry.apidocs.extensions.TokenAuthExtension
    Extension that adds what scopes are needed to access an endpoint to the
    OpenAPI Schema.
    """

    target_class = "aura.core.authentication.JWTCookieAuthentication"
    optional = True
    name = ["jwtHeaderAuth", "jwtCookieAuth"]  # type: ignore

