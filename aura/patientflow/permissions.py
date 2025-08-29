from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import permissions

User = get_user_model()


class IsAuthenticated(permissions.BasePermission):
    """Basic authentication check."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)


class HasUserProfile(permissions.BasePermission):
    """User must have a UserProfile."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "profile"),
        )


class IsClinicStaff(permissions.BasePermission):
    """User must be associated with a clinic."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if not hasattr(request.user, "profile"):
            return False

        return bool(request.user.profile.clinic)


class IsAdminUser(permissions.BasePermission):
    """User must have admin role."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if not hasattr(request.user, "profile"):
            return False

        return request.user.profile.role == "admin" or request.user.is_superuser


class IsFrontDeskOrAbove(permissions.BasePermission):
    """User must be front desk staff or above (nurse, provider, admin)."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if not hasattr(request.user, "profile"):
            return False

        allowed_roles = ["front_desk", "nurse", "provider", "admin"]
        return request.user.profile.role in allowed_roles or request.user.is_superuser


class IsNurseOrAbove(permissions.BasePermission):
    """User must be nurse or above (provider, admin)."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if not hasattr(request.user, "profile"):
            return False

        allowed_roles = ["nurse", "provider", "admin"]
        return request.user.profile.role in allowed_roles or request.user.is_superuser


class IsProviderOrAbove(permissions.BasePermission):
    """User must be provider or above (admin)."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if not hasattr(request.user, "profile"):
            return False

        allowed_roles = ["provider", "admin"]
        return request.user.profile.role in allowed_roles or request.user.is_superuser


class ClinicPermissionMixin:
    """Mixin for clinic-based object permissions."""

    def get_user_clinic(self, user) -> Any:
        """Get the clinic associated with the user."""
        if not user.is_authenticated:
            return None

        if not hasattr(user, "profile"):
            return None

        return user.profile.clinic

    def is_same_clinic(self, user, obj) -> bool:
        """Check if user and object belong to the same clinic."""
        user_clinic = self.get_user_clinic(user)
        if not user_clinic:
            return False

        # Handle different object types
        if hasattr(obj, "clinic"):
            return obj.clinic == user_clinic
        elif hasattr(obj, "appointment") and hasattr(obj.appointment, "clinic"):
            return obj.appointment.clinic == user_clinic
        elif hasattr(obj, "patient") and hasattr(obj.patient, "clinic"):
            return obj.patient.clinic == user_clinic

        return False


class ClinicPatientPermission(permissions.BasePermission, ClinicPermissionMixin):
    """Permission for patient-related operations."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "profile")
            and request.user.profile.clinic,
        )

    def has_object_permission(self, request, view, obj) -> bool:
        # Admins can access everything
        if request.user.is_superuser or (
            hasattr(request.user, "profile") and request.user.profile.role == "admin"
        ):
            return True

        # Check clinic association
        return self.is_same_clinic(request.user, obj)


class ClinicAppointmentPermission(permissions.BasePermission, ClinicPermissionMixin):
    """Permission for appointment-related operations."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if not hasattr(request.user, "profile"):
            return False

        # Different roles have different access levels
        user_role = request.user.profile.role

        if request.method in permissions.SAFE_METHODS:
            # Read access for all clinic staff
            return user_role in ["front_desk", "nurse", "provider", "admin"]
        elif view.action == "update_status":
            # Status updates allowed for all clinic staff
            return user_role in ["front_desk", "nurse", "provider", "admin"]
        elif view.action in ["create", "update", "partial_update"]:
            # Create/update appointments - front desk and above
            return user_role in ["front_desk", "nurse", "provider", "admin"]
        elif view.action == "destroy":
            # Delete appointments - admin only
            return user_role == "admin"

        return False

    def has_object_permission(self, request, view, obj) -> bool:
        # Admins can access everything
        if request.user.is_superuser or (
            hasattr(request.user, "profile") and request.user.profile.role == "admin"
        ):
            return True

        # Check clinic association
        if not self.is_same_clinic(request.user, obj):
            return False

        # Providers can only modify their own appointments for certain actions
        if (
            hasattr(request.user, "profile")
            and request.user.profile.role == "provider"
            and view.action in ["update", "partial_update"]
            and obj.provider != request.user
        ):
            return False

        return True


class ClinicStatusPermission(permissions.BasePermission, ClinicPermissionMixin):
    """Permission for status-related operations."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if not hasattr(request.user, "profile"):
            return False

        user_role = request.user.profile.role

        if request.method in permissions.SAFE_METHODS:
            # Read access for all clinic staff
            return user_role in ["front_desk", "nurse", "provider", "admin"]
        else:
            # Write access - admin and providers can manage statuses
            return user_role in ["provider", "admin"]

    def has_object_permission(self, request, view, obj) -> bool:
        # Admins can access everything
        if request.user.is_superuser or (
            hasattr(request.user, "profile") and request.user.profile.role == "admin"
        ):
            return True

        # Check clinic association
        return self.is_same_clinic(request.user, obj)


class NotificationPermission(permissions.BasePermission):
    """Permission for notification operations."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        # Users can only access their own notifications
        if obj.recipient == request.user:
            return True

        # Admins can access all notifications
        if request.user.is_superuser or (
            hasattr(request.user, "profile") and request.user.profile.role == "admin"
        ):
            return True

        return False


class FlowEventPermission(permissions.BasePermission, ClinicPermissionMixin):
    """Permission for flow event operations."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if not hasattr(request.user, "profile"):
            return False

        # All clinic staff can view flow events
        user_role = request.user.profile.role
        return user_role in ["front_desk", "nurse", "provider", "admin"]

    def has_object_permission(self, request, view, obj) -> bool:
        # Admins can access everything
        if request.user.is_superuser or (
            hasattr(request.user, "profile") and request.user.profile.role == "admin"
        ):
            return True

        # Check clinic association
        return self.is_same_clinic(request.user, obj)


class ClinicPermission(permissions.BasePermission):
    """Permission for clinic operations."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if request.method in permissions.SAFE_METHODS:
            # Read access for authenticated users
            return True
        else:
            # Write access - superuser only
            return request.user.is_superuser

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            # Users can view their own clinic and admins can view all
            if hasattr(request.user, "profile") and (
                request.user.profile.clinic == obj
                or request.user.profile.role == "admin"
            ):
                return True
            return request.user.is_superuser
        else:
            # Write access - superuser only
            return request.user.is_superuser


# Composite permissions for common use cases
class PatientFlowStaffPermission(permissions.BasePermission):
    """Combined permission for patient flow staff (any clinic role)."""

    def has_permission(self, request, view) -> bool:
        return (
            IsAuthenticated().has_permission(request, view)
            and HasUserProfile().has_permission(request, view)
            and IsClinicStaff().has_permission(request, view)
        )


class PatientFlowManagerPermission(permissions.BasePermission):
    """Combined permission for patient flow managers (nurse/provider/admin)."""

    def has_permission(self, request, view) -> bool:
        return (
            IsAuthenticated().has_permission(request, view)
            and HasUserProfile().has_permission(request, view)
            and IsNurseOrAbove().has_permission(request, view)
        )
