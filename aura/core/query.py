from functools import reduce
from typing import Any

from django.db.models import Q


def in_iexact(column: str, values: Any) -> Q:
    """Operator to test if any of the given values are (case-insensitive)
    matching to values in the given column."""
    from operator import or_

    query = f"{column}__iexact"
    # if values is empty, have a default value for the reduce call that will essentially resolve a column in []
    query_in = f"{column}__in"

    return reduce(or_, [Q(**{query: v}) for v in values], Q(**{query_in: []}))
