from rest_framework.permissions import SAFE_METHODS
from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return obj.patient == request.user
        return obj.patient == request.user or request.user == obj.therapist


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff


class IsTherapist(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.therapist


class IsPatient(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.patient


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
