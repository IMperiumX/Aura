from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import CoachProfile
from .models import PatientProfile
from .models import TherapistProfile
from .models import User
from .models import UserProfile

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


class UserProfileInline(admin.StackedInline):
    """ """

    model = UserProfile
    can_delete = False
    verbose_name_plural = "User Profiles"


class PatientProfileInline(admin.StackedInline):
    """ """

    model = PatientProfile
    can_delete = False
    verbose_name_plural = "Patients"


class CoachProfileInline(admin.StackedInline):
    """ """

    model = CoachProfile
    can_delete = False
    verbose_name_plural = "Coaches"


class TherapistProfileInline(admin.StackedInline):
    """ """

    model = TherapistProfile
    can_delete = False
    verbose_name_plural = "Therapists"


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    """ """

    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (
            None,
            {
                "fields": ("email", "password"),
            },
        ),
        (
            _("Personal info"),
            {
                "fields": ("name",),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "fields": ("last_login", "date_joined"),
            },
        ),
    )
    list_display = ["email", "name", "is_superuser"]
    raw_id_fields = ["groups", "user_permissions"]
    search_fields = ("email", "name")
    ordering = ["id"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    filter_horizontal = (
        "groups",
        "user_permissions",
    )

    def get_inline_instances(self, request, obj=None):
        """

        :param request: param obj:  (Default value = None)
        :param obj: Default value = None)

        """
        if not obj:
            return []
        inline_instances = super().get_inline_instances(request, obj)

        if hasattr(obj, "userprofile"):
            inline_instances.append(UserProfileInline(self.model, self.admin_site))
        if hasattr(obj, "patientprofile"):
            inline_instances.append(PatientProfileInline(self.model, self.admin_site))
        elif hasattr(obj, "therapistprofile"):
            inline_instances.append(TherapistProfileInline(self.model, self.admin_site))
        elif hasattr(obj, "coachprofile"):
            inline_instances.append(CoachProfileInline(self.model, self.admin_site))
        return inline_instances


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    """ """

    list_display = (
        "id",
        "avatar_url",
        "bio",
        "date_of_birth",
        "created_at",
        "weight",
        "height",
        "gender",
        "health_data",
        "preferences",
        "user",
        "medical_history",
        "current_medications",
    )
    list_filter = ("date_of_birth", "created_at", "user")
    date_hierarchy = "created_at"


@admin.register(TherapistProfile)
class TherapistProfileAdmin(admin.ModelAdmin):
    """ """

    list_display = (
        "id",
        "avatar_url",
        "bio",
        "date_of_birth",
        "created_at",
        "gender",
        "user",
        "license_number",
        "specialties",
        "years_of_experience",
        "availability",
    )
    list_filter = ("date_of_birth", "created_at", "user")
    date_hierarchy = "created_at"


@admin.register(CoachProfile)
class CoachProfileAdmin(admin.ModelAdmin):
    """ """

    list_display = (
        "id",
        "avatar_url",
        "bio",
        "date_of_birth",
        "created_at",
        "weight",
        "height",
        "gender",
        "user",
        "certification",
        "areas_of_expertise",
        "coaching_philosophy",
        "availability",
    )
    list_filter = ("date_of_birth", "created_at", "user")
    date_hierarchy = "created_at"


@admin.register(UserProfile)
class UserProfile(admin.ModelAdmin):
    """ """

    list_display = (
        "id",
        "avatar_url",
        "bio",
        "date_of_birth",
        "created_at",
    )

    list_filter = ("date_of_birth", "created_at")

    date_hierarchy = "created_at"
