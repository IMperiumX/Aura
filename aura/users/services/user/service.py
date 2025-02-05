from abc import abstractmethod

from core.services.base import Service
from typing_extensions import TypedDict


class UserFilterArgs(TypedDict, total=False):
    user_ids: list[int]
    """List of user ids to search with"""

    is_active: bool
    """Whether the user needs to be active"""

    emails: list[str]
    """list of emails to match with"""

    email_verified: bool
    """Whether emails have to be verified or not"""

    query: str
    """Filter by email or name"""

    authenticator_types: list[int] | None
    """The type of MFA authenticator you want to query by"""


class UserService(Service):
    key = "user"

    @classmethod
    def get_local_implementation(cls):
        from aura.users.services.user.impl import DatabaseBackedUserService

        return DatabaseBackedUserService()

    @abstractmethod
    def get_many(self, *, filter: UserFilterArgs):
        pass

    def get_user(self, user_id: int):
        """
        Get a single user by id

        The result of this method is cached.

        :param user_id: The user to fetch
        """
        return get_user(user_id)


def get_user(user_id: int):
    users = user_service.get_many(filter={"user_ids": [user_id]})
    if len(users) > 0:
        return users[0]
    return None


user_service = UserService.create_delegation()
