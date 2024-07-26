from django.conf import settings as api_settings
from django.utils.module_loading import import_string


def default_create_token(token_model, user, serializer):
    token, _ = token_model.objects.get_or_create(user=user)
    return token


def jwt_encode(user):
    JWTTokenClaimsSerializer = import_string(api_settings.JWT_TOKEN_CLAIMS_SERIALIZER)

    refresh = JWTTokenClaimsSerializer.get_token(user)
    return refresh.access_token, refresh
