"""
User-related signals for analytics event recording.
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.signals import user_logged_out
from django.contrib.auth.signals import user_login_failed
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from aura import analytics

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def track_user_creation(sender, instance, created, **kwargs):
    """Track user creation events."""
    if created:
        try:
            analytics.record(
                "user.created",
                instance=instance,
                id=instance.id,
                username=instance.username,
                email=instance.email or "",
            )
        except Exception as e:
            logger.warning(f"Failed to record user creation event: {e}")


@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """Track successful user login events."""
    try:
        # Get client IP
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR", "")

        analytics.record(
            "user.login",
            instance=user,
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent", "")[:500],
            login_method="password",  # Default to password, can be extended
            success=True,
        )
    except Exception as e:
        logger.warning(f"Failed to record user login event: {e}")


@receiver(user_logged_out)
def track_user_logout(sender, request, user, **kwargs):
    """Track user logout events."""
    try:
        if user and user.is_authenticated:
            # Calculate session duration if possible
            session_start = request.session.get("_auth_user_login_time")
            session_duration = None
            if session_start:
                try:
                    login_time = timezone.datetime.fromisoformat(session_start)
                    duration = timezone.now() - login_time
                    session_duration = int(duration.total_seconds() / 60)  # Minutes
                except (ValueError, TypeError):
                    pass

            analytics.record(
                "user.logout",
                instance=user,
                user_id=user.id,
                session_duration_minutes=session_duration,
                logout_type="manual",
            )
    except Exception as e:
        logger.warning(f"Failed to record user logout event: {e}")


@receiver(user_login_failed)
def track_login_failure(sender, credentials, request, **kwargs):
    """Track failed login attempts."""
    try:
        # Get client IP
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR", "")

        username = credentials.get("username", "") if credentials else ""

        analytics.record(
            "auth.failed",
            username=username,
            ip_address=ip_address,
            failure_reason="invalid_credentials",
            user_agent=request.headers.get("user-agent", "")[:500],
        )
    except Exception as e:
        logger.warning(f"Failed to record login failure event: {e}")


@receiver(pre_save, sender=User)
def track_user_profile_changes(sender, instance, **kwargs):
    """Track when user profile fields are updated."""
    if instance.pk:  # Only for existing users
        try:
            old_instance = User.objects.get(pk=instance.pk)
            changed_fields = []

            # Check for changes in key fields
            fields_to_check = [
                "username",
                "email",
                "first_name",
                "last_name",
                "is_active",
                "is_staff",
            ]
            for field in fields_to_check:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changed_fields.append(field)

            if changed_fields:
                # Store changed fields for post_save signal
                instance._profile_changed_fields = changed_fields

        except User.DoesNotExist:
            pass
        except Exception as e:
            logger.warning(f"Failed to track user profile changes: {e}")


@receiver(post_save, sender=User)
def record_user_profile_update(sender, instance, created, **kwargs):
    """Record user profile update event after save."""
    if not created and hasattr(instance, "_profile_changed_fields"):
        try:
            import json

            # Get role and clinic info if available
            role = None
            clinic_id = None
            if hasattr(instance, "profile"):
                role = getattr(instance.profile, "role", None)
                clinic = getattr(instance.profile, "clinic", None)
                clinic_id = clinic.id if clinic else None

            analytics.record(
                "user.profile_updated",
                instance=instance,
                user_id=instance.id,
                updated_fields=json.dumps(instance._profile_changed_fields),
                role=role,
                clinic_id=clinic_id,
            )

            # Clean up temporary attribute
            delattr(instance, "_profile_changed_fields")

        except Exception as e:
            logger.warning(f"Failed to record user profile update event: {e}")

        except Exception as e:
            logger.warning(f"Failed to record user profile update event: {e}")
