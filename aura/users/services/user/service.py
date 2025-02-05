from __future__ import annotations

import threading
import typing
from abc import ABC
from abc import abstractmethod
from typing import Self

from typing_extensions import TypedDict

if typing.TYPE_CHECKING:
    from aura.users.models import User


class UserFilterArgs(TypedDict, total=False):
    user_ids: list[int]
    """List of user ids to search with"""

    is_active: bool
    """Whether the user needs to be active"""

    organization_id: int
    """Organization to check membership in"""

    emails: list[str]
    """list of emails to match with"""

    email_verified: bool
    """Whether emails have to be verified or not"""

    query: str
    """Filter by email or name"""

    authenticator_types: list[int] | None
    """The type of MFA authenticator you want to query by"""


class DelegatingService:
    def __init__(
        self,
        base_service_cls,
        constructor,
        signatures,
    ) -> None:
        self._constructor = constructor
        self._singleton = {}
        self._lock = threading.RLock()
        self._base_service_cls = base_service_cls

    def __getattr__(self, item: str):
        key = self._base_service_cls.key

        try:
            # fast path: object already built
            impl = self._singleton[key]
        except KeyError:
            # slow path: only lock when building the object
            with self._lock:
                # another thread may have won the race to build the object
                try:
                    impl = self._singleton[key]
                except KeyError:
                    impl = self._singleton[key] = self._constructor()

        return getattr(impl, item)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._base_service_cls.__name__})"


class Service(ABC):
    @classmethod
    @abstractmethod
    def get_local_implementation(cls) -> Service:
        """Return a service object that runs locally.

        The returned service object is (generally) the database-backed instance that
        is called when we either receive a remote call from outside, or want to call
        it within the same silo.

        A base service class generally should override this class method, making a
        forward reference to its own database-backed subclass.
        """

        raise NotImplementedError

    @classmethod
    def create_delegation(cls, use_test_client: bool | None = None) -> Self:
        """Instantiate a base service class for the current mode."""
        constructor = cls.get_local_implementation()
        service = DelegatingService(cls, constructor)
        # this returns a proxy which simulates the given class
        return service  # noqa: RET504


class UserService(Service):
    key = "user"

    @classmethod
    def get_local_implementation(cls):
        from aura.users.services.user.impl import DatabaseBackedUserService

        return DatabaseBackedUserService()

    @abstractmethod
    def get_many(self, *, filter: UserFilterArgs) -> list[User]:
        pass

    def get_user(self, user_id: int) -> User | None:
        """
        Get a single user by id

        The result of this method is cached.

        :param user_id: The user to fetch
        """
        return get_user(user_id)


def get_user(user_id: int) -> User | None:
    users = user_service.get_many(filter={"user_ids": [user_id]})
    if len(users) > 0:
        return users[0]
    return None


user_service = UserService.create_delegation()
