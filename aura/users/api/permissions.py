from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return obj.patient == request.user or request.user.is_staff
        return (
            obj.patient == request.user
            or request.user == obj.therapist
            or request.user.is_staff
        )


class IsTherapistOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.therapist or request.user.is_staff


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff
