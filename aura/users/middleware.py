from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.http import HttpResponseRedirect


class LDAPSSOMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is not authenticated and SSO header is present
        if not request.user.is_authenticated and "x-sso-username" in request.headers:
            username = request.headers["x-sso-username"]
            user = authenticate(request, username=username, password=None)
            if user:
                login(request, user)
                # Redirect to a success page or home page
                return HttpResponseRedirect("/")

        return self.get_response(request)