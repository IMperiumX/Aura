import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import transaction
from django.utils import timezone
from django_auth_ldap.backend import LDAPBackend

logger = logging.getLogger("requests")

User = get_user_model()


class AuraAuthBackend(ModelBackend, LDAPBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # First, try to authenticate with LDAP
        logger.debug("[AuraAuthBackend] Authenticating with LDAP")
        ldap_user = LDAPBackend().authenticate(
            request,
            username=username,
            password=password,
        )

        if ldap_user:
            return self.get_or_create_user(ldap_user, "ldap")
        logger.debug("[AuraAuthBackend] LDAP authentication: User not found ")

        # If LDAP auth fails, fall back to the database
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        logger.debug("[AuraAuthBackend] Authenticating with username and password")
        return ModelBackend().authenticate(
            request,
            username=username,
            password=password,
        )

    @transaction.atomic
    def get_or_create_user(self, ldap_user, auth_provider):
        user, created = User.objects.get_or_create(
            username=ldap_user.username,
            defaults={
                "email": ldap_user.attrs.get("mail", [None])[0],
                "first_name": ldap_user.attrs.get("givenName", [None])[0],
                "last_name": ldap_user.attrs.get("sn", [None])[0],
            },
        )

        if created:
            # Set a random password for the local user account
            user.set_unusable_password()
            user.save()

            # Create profile based on LDAP groups or attributes
            self.create_user_profile(user, ldap_user)

        # Update the auth provider
        user.auth_provider = auth_provider
        user.save()

        return user

    def create_user_profile(self, user, ldap_user):
        from users.models import Patient
        from users.models import Therapist

        # Check LDAP groups or attributes to determine user type
        ldap_groups = self.get_group_permissions(ldap_user)

        if "therapists" in ldap_groups:
            Therapist.objects.create(
                user=user,
                license_number=ldap_user.attrs.get("employeeNumber", [""])[0],
                specialties=ldap_user.attrs.get("departmentNumber", [""])[0],
                years_of_experience=int(ldap_user.attrs.get("employeeType", [0])[0]),
            )
        else:
            Patient.objects.create(
                user=user,
                date_of_birth=ldap_user.attrs.get("birthDate", [None])[0],
            )

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @transaction.atomic
    def configure_user(self, request, ldap_user, **kwargs):
        from users.models import Patient
        from users.models import Therapist

        """
        Configures a user after authentication and returns the updated User object.
        This method is called every time a user logs in through LDAP.
        """
        user = super().configure_user(ldap_user)

        # Update basic user information
        user.first_name = ldap_user.attrs.get("givenName", [user.first_name])[0]
        user.last_name = ldap_user.attrs.get("sn", [user.last_name])[0]
        user.email = ldap_user.attrs.get("mail", [user.email])[0]
        user.last_login = timezone.now()

        # Determine user type based on LDAP group membership
        ldap_groups = self.get_group_permissions(ldap_user)
        is_therapist = "therapist" in ldap_groups
        is_patient = "patient" in ldap_groups

        # Handle potential conflicts (user in both groups)
        if is_therapist and is_patient:
            # Log this conflict and default to patient
            msg = f"User {user} is in both therapist and patient groups.\
                    Defaulting to patient."
            logger.debug(msg)
            is_therapist = False

        # Update or create Therapist profile
        if is_therapist:
            therapist_profile, created = Therapist.objects.get_or_create(
                user=user,
            )
            therapist_profile.license_number = ldap_user.attrs.get(
                "employeeNumber",
                [""],
            )[0]
            therapist_profile.years_of_experience = int(
                ldap_user.attrs.get("employeeType", [0])[0],
            )

            therapist_profile.save()

            # Set user permissions for therapist
            user.is_staff = True
            user.groups.add(self.django_auth_ldap_group_to_django_group("therapists"))

        # Update or create Patient profile
        elif is_patient:
            patient_profile, created = Patient.objects.get_or_create(user=user)
            patient_profile.date_of_birth = ldap_user.attrs.get("birthDate", [None])[0]
            patient_profile.emergency_contact = ldap_user.attrs.get(
                "emergencyContact",
                [""],
            )[0]
            patient_profile.save()

            # Set user permissions for patient
            user.is_staff = False
            user.groups.add(self.django_auth_ldap_group_to_django_group("patients"))

        # Handle cases where user is neither therapist nor patient
        else:
            # Log this case and possibly set a default profile or raise an exception
            msg = f"Warning: User {user.username} is neither a therapist nor a patient."
            logger(msg)
            # set a default profile
            return None

        user.save()
        return user

    def django_auth_ldap_group_to_django_group(self, ldap_group_name):
        # This method should convert LDAP group names to Django group objects
        from django.contrib.auth.models import Group

        return Group.objects.get_or_create(name=ldap_group_name)[0]
