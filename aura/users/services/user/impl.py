import logging

from django.db.models import Q
from django.db.models import QuerySet

from aura.core.query import in_iexact
from aura.users.models import User
from aura.users.services.user.service import UserFilterArgs
from aura.users.services.user.service import UserService

logger = logging.getLogger("user")


class DatabaseBackedUserService(UserService):
    def get_many(self, *, filter: UserFilterArgs) -> list[User]:
        return self._FQ.get_many(filter)

    class _UserFilterQuery:
        def get_many(self, filter, select_related: bool = True) -> QuerySet[User]:
            query = self.base_query(select_related=select_related)
            return self.apply_filters(query, filter)

        def base_query(self, select_related: bool = True) -> QuerySet[User]:
            if not select_related:
                return User.objects.all()
            return User.objects.select_related()  # XXX: Add select_related fields

        def apply_filters(
            self,
            query: QuerySet[User],
            filters: UserFilterArgs,
        ) -> QuerySet[User]:
            """
            Apply filters to a query.

            :param query: The query to apply the filter to
            :param filters: The filter to apply
            """
            if "user_ids" in filters:
                query = query.filter(id__in=filters["user_ids"])
            if "is_active" in filters:
                query = query.filter(is_active=filters["is_active"])
            if "email_verified" in filters:
                query = query.filter(emails__is_verified=filters["email_verified"])
            if "emails" in filters:
                query = query.filter(in_iexact("emails__email", filters["emails"]))
            if "query" in filters:
                query = query.filter(
                    Q(emails__email__icontains=filters["query"])
                    | Q(name__icontains=filters["query"]),
                )

            return query

    _FQ = _UserFilterQuery()
