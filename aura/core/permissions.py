from rest_framework.permissions import SAFE_METHODS
from rest_framework.permissions import BasePermission


class IsPatientOwnerOrReadOnly(BasePermission):
    """
    Custom permission to allow only patient owners to edit their own profiles.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the profile
        # and only if the user is a patient
        return obj.user == request.user and request.user.user_type == "patient"


class IsTherapistOwnerOrReadOnly(BasePermission):
    """
    Custom permission to allow only therapist owners to edit their own profiles.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the profile
        # and only if the user is a therapist
        return obj.user == request.user and request.user.user_type == "therapist"


class IsSessionParticipant(BasePermission):
    """
    Custom permission to allow only session participants to access session data.
    """

    def has_object_permission(self, request, view, obj):
        # Only allow access to users who are participants in the session
        return request.user in [obj.patient, obj.therapist]


class IsPatient(BasePermission):
    """
    Custom permission to allow only patients.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.user_type == "patient"


class IsTherapist(BasePermission):
    """
    Custom permission to allow only therapists.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.user_type == "therapist"


class IsVerifiedUser(BasePermission):
    """
    Custom permission to allow only verified users.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_verified
