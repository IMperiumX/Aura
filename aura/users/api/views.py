import logging

from dj_rest_auth.registration import views as dj_views
from django.conf import settings as api_settings
from django.db.utils import IntegrityError
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.viewsets import ModelViewSet

from aura.core.utils import jwt_encode
from aura.users.api.serializers import LoginSerializer
from aura.users.api.serializers import PatientSerializer
from aura.users.api.serializers import ReviewSerializer
from aura.users.api.serializers import UserSerializer
from aura.users.mixins import LoginMixin
from aura.users.models import Patient
from aura.users.models import User

logger = logging.getLogger(__name__)


class UserViewSet(
    LoginMixin,
    RetrieveModelMixin,
    ListModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def get_queryset(self, *args, **kwargs):
        assert isinstance(self.request.user.id, int)
        return self.queryset.filter(id=self.request.user.id)

    def get_throttles(self):
        if self.action == "login":
            self.throttle_scope = "aura_auth"
        return super().get_throttles()

    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    @action(detail=True, methods=["post"])
    def add_review(self, request, pk=None):
        user = self.get_object()
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(reviewer=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        serializer_class=LoginSerializer,
    )
    def login(self, request):
        """
        Authenticates the user and generates the necessary tokens or session login.
            1. JWT
            2. Session login
            3. Token

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponse: The HTTP response object.

        Raises:
            ValidationError: If the serializer data is invalid.

        """
        self.request = request
        self.serializer = self.get_serializer(data=self.request.data)
        self.serializer.is_valid(raise_exception=True)

        self.user = self.serializer.validated_data["user"]
        token_model = Token

        if api_settings.USE_JWT:
            self.access_token, self.refresh_token = jwt_encode(self.user)
        if api_settings.SESSION_LOGIN:
            self.process_login()
        elif token_model:
            from aura.core.utils import default_create_token

            self.token = default_create_token(
                token_model,
                self.user,
                self.serializer,
            )

        return self.get_response()


class RegisterView(dj_views.RegisterView):
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"error": "User already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            return Response(
                {"error": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("An error occurred")
            return Response(
                {"error": "An error occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PatientViewSet(ModelViewSet):
    serializer_class = PatientSerializer
    queryset = Patient.objects.all()
    lookup_field = "pk"

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        from aura import audit_log
        from aura.audit_log.utils import create_audit_entry
        from aura.mentalhealth.models import Disorder

        user_data = serializer.validated_data.pop("user", None)
        serializer.validated_data["user"] = User.objects.create_user(**user_data)

        disorders = serializer.validated_data.pop("disorders", None)

        serializer.save()
        patient: Patient = serializer.instance
        for disorder_data in disorders:
            disorder, _ = Disorder.objects.get_or_create(**disorder_data)
            patient.disorders.add(disorder)

        create_audit_entry(
            request=self.request,
            target_object=patient.id,
            event=audit_log.get_event_id("PATIENT_CREATE"),
            data=patient.get_audit_log_data(),
        )
