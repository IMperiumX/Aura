from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

from aura.analytics.attribute import Attribute


def get_data(
    attributes: Sequence[Attribute],
    items: dict[str, Any],
) -> Mapping[str, Any | None]:
    data = {}
    for attr in attributes:
        nv = items.pop(attr.name, None)
        if attr.required and nv is None:
            msg = f"{attr.name} is required (cannot be None)"
            raise ValueError(msg)
        data[attr.name] = attr.extract(nv)

    if items:
        msg = "Unknown attributes: {}".format(", ".join(items.keys()))
        raise ValueError(msg)

    return data
