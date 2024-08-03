import hashlib
import secrets
from typing import Any, ClassVar

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils.encoding import force_str
from rest_framework.authentication import BasicAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from aura.users.models import User
from rest_framework.authtoken.models import Token as ApiToken

AURA_AUTH_TOKEN_PREFIX = "aura_"


class TokenStrLookupRequiredError(Exception):
    """
    Used in combination with `apitoken.use-and-update-hash-rate` option.

    If raised, calling code should peform API token lookups based on its
    plaintext value and not its hashed value.
    """


class QuietBasicAuthentication(BasicAuthentication):
    def authenticate_header(self, request: Request) -> str:
        return 'xBasic realm="%s"' % self.www_authenticate_realm

    def transform_auth(
        self,
        user: int | User | None | AnonymousUser,
        request_auth: Any,
    ) -> tuple[User | AnonymousUser, ApiToken | None]:
        if isinstance(user, int):
            user = User.objects.filter(user_id=user).last()
        elif isinstance(user, User):
            user = User.objects.filter(user_id=user.id).last()
        if user is None:
            user = AnonymousUser()

        auth_token = ApiToken.from_token(request_auth)

        return (user, auth_token)


class StandardAuthentication(QuietBasicAuthentication):
    token_name: ClassVar[bytes]

    def accepts_auth(self, auth: list[bytes]) -> bool:
        return bool(auth) and auth[0].lower() == self.token_name

    def authenticate_token(self, request: Request, token_str: str) -> tuple[Any, Any]:
        raise NotImplementedError

    def authenticate(self, request: Request):
        auth = get_authorization_header(request).split()

        if not self.accepts_auth(auth):
            return None

        if len(auth) == 1:
            msg = "Invalid token header. No credentials provided."
            raise AuthenticationFailed(msg)
        if len(auth) > 2:
            msg = "Invalid token header. Token string should not contain spaces."
            raise AuthenticationFailed(msg)

        return self.authenticate_token(request, force_str(auth[1]))


class UserAuthTokenAuthentication(StandardAuthentication):
    token_name = b"bearer"

    def _find_or_update_token_by_hash(self, token_str: str) -> ApiToken:
        """
        Find token by hash or update token's hash value if only found via plaintext.

        1. Hash provided plaintext token.
        2. Perform lookup based on hashed value.
        3. If found, return the token.
        4. If not found, search for the token based on its plaintext value.
        5. If found, update the token's hashed value and return the token.
        6. If not found via hash or plaintext value, raise AuthenticationFailed

        Returns `ApiToken`
        """

        hashed_token = hashlib.sha256(token_str.encode()).hexdigest()

        rate = settings.API_TOKEN_USE_AND_UPDATE_HASH_RATE
        random_rate = secrets.randbelow(100) / 100
        use_hashed_token = rate > random_rate

        try:
            # Try to find the token by its hashed value first
            if use_hashed_token:
                return ApiToken.objects.select_related("user", "application").get(
                    hashed_token=hashed_token,
                )
            raise TokenStrLookupRequiredError
        except (ApiToken.DoesNotExist, TokenStrLookupRequiredError):
            try:
                # If we can't find it by hash, use the plaintext string
                api_token = ApiToken.objects.select_related("user", "application").get(
                    token=token_str,
                )
            except ApiToken.DoesNotExist:
                # If the token does not exist by plaintext either,
                # it is not a valid token
                msg = "Invalid token"
                raise AuthenticationFailed(msg) from None
            else:
                if use_hashed_token:
                    # Update it with the hashed value if found by plaintext
                    api_token.hashed_token = hashed_token
                    api_token.save(update_fields=["hashed_token"])

                return api_token

    def accepts_auth(self, auth: list[bytes]) -> bool:
        if not super().accepts_auth(auth):
            return False

        # Technically, this will not match if auth length is not 2
        # However, we want to run into `authenticate()` in this case, as this throws a more helpful error message
        if len(auth) != 2:
            return True

        token_str = force_str(auth[1])
        return not token_str.startswith(AURA_AUTH_TOKEN_PREFIX)

    def authenticate_token(self, request: Request, token_str: str) -> tuple[Any, Any]:
        user: AnonymousUser | None = AnonymousUser()

        token: ApiToken | None = ApiToken.from_request(request, token_str)

        application_is_inactive = False

        if not token:
            token = self._find_or_update_token_by_hash(token_str)
            user = token.user
            application_is_inactive = (
                token.application is not None and not token.application.is_active
            )

        if not token:
            raise AuthenticationFailed("Invalid token")

        if token.is_expired():
            raise AuthenticationFailed("Token expired")

        if user and hasattr(user, "is_active") and not user.is_active:
            raise AuthenticationFailed("User inactive or deleted")

        if application_is_inactive:
            raise AuthenticationFailed("UserApplication inactive or deleted")

        return self.transform_auth(
            user,
            token,
        )
