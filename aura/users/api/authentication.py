from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Clean Architecture imports
from aura.core.application.services.authentication_service import AuthenticationService
from aura.core.infrastructure.repositories.django_user_repository import DjangoUserRepository

from .serializers import UserRegistrationSerializer


@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post")
class RegisterView(APIView):
    """
    Register a new user using Clean Architecture

    POST /api/0/auth/register/
    """

    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Clean Architecture components
        user_repository = DjangoUserRepository()
        self._auth_service = AuthenticationService(user_repository)

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Use the authentication service (Clean Architecture)
            response = self._auth_service.register_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                user_type=serializer.validated_data["user_type"],
                first_name=serializer.validated_data.get("first_name"),
                last_name=serializer.validated_data.get("last_name"),
            )

            if response.success:
                # Send verification email here (implement based on your email setup)
                return Response(
                    {
                        "data": {
                            "user_id": str(response.user.id),
                            "email": response.user.email,
                            "user_type": response.user.user_type,
                            "verification_required": True,
                            "verification_email_sent": True,
                            "message": "Please check your email to verify your account",
                        },
                        "meta": {
                            "timestamp": timezone.now().isoformat(),
                            "request_id": str(__import__("uuid").uuid4()),
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {
                    "error": {
                        "code": "REGISTRATION_ERROR",
                        "message": response.error_message,
                        "details": {},
                    },
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {"field_errors": serializer.errors},
                },
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post")
class LoginView(APIView):
    """
    Authenticate user and return Knox token using Clean Architecture

    POST /api/0/auth/login/
    """

    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Clean Architecture components
        user_repository = DjangoUserRepository()
        self._auth_service = AuthenticationService(user_repository)

    def post(self, request):
        # Use the authentication service (Clean Architecture)
        response = self._auth_service.login_user(
            email=request.data.get("email", ""), password=request.data.get("password", "")
        )

        if response.success:
            return Response(
                {
                    "data": {
                        "token": response.token,
                        "user": self._auth_service.get_user_profile(response.user),
                        "expires": response.token_expiry,
                    },
                    "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "error": {
                    "code": "AUTHENTICATION_ERROR",
                    "message": response.error_message,
                    "details": {},
                },
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )


class LogoutView(APIView):
    """
    Logout user by deleting the Knox token using Clean Architecture

    POST /api/0/auth/logout/
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Clean Architecture components
        user_repository = DjangoUserRepository()
        self._auth_service = AuthenticationService(user_repository)

    def post(self, request):
        # Use the authentication service (Clean Architecture)
        response = self._auth_service.logout_user(request.user)

        # Delete Knox token
        request._auth.delete()

        return Response(
            {
                "data": {"message": "Successfully logged out"},
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_200_OK,
        )


class UserProfileView(APIView):
    """
    Get current user profile using Clean Architecture

    GET /api/0/auth/profile/
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Clean Architecture components
        user_repository = DjangoUserRepository()
        self._auth_service = AuthenticationService(user_repository)

    def get(self, request):
        # Use the authentication service (Clean Architecture)
        user_data = self._auth_service.get_user_profile(request.user)

        return Response(
            {
                "data": user_data,
                "meta": {"timestamp": timezone.now().isoformat(), "request_id": str(__import__("uuid").uuid4())},
            },
            status=status.HTTP_200_OK,
        )
