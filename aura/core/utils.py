from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


def default_create_token(token_model, user, serializer):
    token, _ = token_model.objects.get_or_create(user=user)
    return token


def jwt_encode(user):
    refresh = TokenObtainPairSerializer.get_token(user)
    return refresh.access_token, refresh


def get_upload_path(instance, filename):
    """
    Return the upload path for the file.
    """
    return f"uploads/{instance.__class__.__name__}/{instance.pk}/{filename}"
