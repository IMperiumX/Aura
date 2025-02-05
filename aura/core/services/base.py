from __future__ import annotations

import threading
from abc import ABC
from abc import abstractmethod
from typing import Self


class ServiceError(Exception):
    def __init__(
        self,
        service_name: str,
        method_name: str | None,
        message: str,
    ) -> None:
        name = f"{service_name}.{method_name}" if method_name else service_name
        super().__init__(f"{name}: {message}")


class ServiceSetupError(ServiceError):
    """Indicates an error in declaring the properties of services."""


class Service(ABC):
    def __init_subclass__(cls) -> None:
        # These class attributes are required on any RpcService subclass that has
        # at least one method decorated by `@rpc_method`. (They can be left off
        # if and when we make an intermediate abstract class.)
        if not isinstance(getattr(cls, "key", None), str):
            raise ServiceSetupError(
                cls.__name__,
                None,
                "`key` class attribute (str) is required",
            )

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


class DelegatingService:
    def __init__(
        self,
        base_service_cls,
        constructor,
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
