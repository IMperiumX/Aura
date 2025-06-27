from threading import local

from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

_thread_locals = local()


def get_request() -> HttpRequest | None:
    """
    Retrieve the current request object from thread-local storage.

    This function is a utility to safely access the request object from
    parts of the codebase that don't have direct access to it, such as
    logging filters or Celery tasks initiated from a request.

    Returns:
        The current HttpRequest object, or None if it's not available.
    """
    return getattr(_thread_locals, "request", None)


class RequestMiddleware(MiddlewareMixin):
    """
    A middleware that stores the current request object in thread-local storage.

    This makes the request object accessible globally via the `get_request`
    function, which is useful for components that operate outside the
    standard view request-response cycle.
    """

    def process_request(self, request: HttpRequest):
        """
        Stores the request object in thread-local storage.
        """
        _thread_locals.request = request

    def process_response(self, request: HttpRequest, response):
        """
        Cleans up the request object from thread-local storage.
        """
        if hasattr(_thread_locals, "request"):
            del _thread_locals.request
        return response

    def process_exception(self, request: HttpRequest, exception):
        """
        Ensures cleanup even when an exception occurs in the view.
        """
        if hasattr(_thread_locals, "request"):
            del _thread_locals.request
