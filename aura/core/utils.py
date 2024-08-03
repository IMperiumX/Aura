from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


def default_create_token(token_model, user, serializer):
    token, _ = token_model.objects.get_or_create(user=user)
    return token


def jwt_encode(user):
    refresh = TokenObtainPairSerializer.get_token(user)
    return refresh.access_token, refresh
