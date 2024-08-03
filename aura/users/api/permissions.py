from rest_framework.permissions import SAFE_METHODS
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff


class IsTherapist(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.therapist_profile


class IsPatient(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.patient_profile


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
