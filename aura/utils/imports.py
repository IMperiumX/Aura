from typing import Any


class ModuleProxyCache(dict[str, object]):
    def __missing__(self, key: str) -> object:
        if "." not in key:
            return __import__(key)

        module_name, class_name = key.rsplit(".", 1)

        module = __import__(module_name, {}, {}, [class_name])
        handler = getattr(module, class_name)

        # We cache a NoneType for missing imports to avoid repeated lookups
        self[key] = handler

        return handler


_cache = ModuleProxyCache()


def import_string(path: str) -> Any:
    """
    Path must be module.path.ClassName

    >>> cls = import_string('aura.models.Group')
    """
    result = _cache[path]
    return result
