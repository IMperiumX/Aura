from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import Coach
from .models import Patient
from .models import Therapist
from .models import User

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


class PatientInline(admin.StackedInline):
    """ """

    model = Patient
    fk_name = "user"
    verbose_name_plural = "Patients"
    can_delete = False
    show_change_link = True
    classes = ["collapse"]


class CoachInline(admin.StackedInline):
    """ """

    model = Coach
    fk_name = "user"
    verbose_name_plural = "Coaches"
    can_delete = False
    show_change_link = True
    classes = ["collapse"]


class TherapistInline(admin.StackedInline):
    """ """

    model = Therapist
    fk_name = "user"
    verbose_name_plural = "Therapists"
    can_delete = False
    show_change_link = True
    classes = ["collapse"]


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

        if hasattr(obj, "coach_profile"):
            inline_instances.append(CoachInline(self.model, self.admin_site))
        if hasattr(obj, "patient_profile"):
            inline_instances.append(PatientInline(self.model, self.admin_site))
        if hasattr(obj, "therapist_profile"):
            inline_instances.append(TherapistInline(self.model, self.admin_site))
        return inline_instances


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "created_by",
        "updated_by",
        "avatar_url",
        "bio",
        "date_of_birth",
        "height",
    )
    list_filter = (
        "created",
        "modified",
        "created_by",
        "updated_by",
        "date_of_birth",
        "user",
    )
    readonly_fields = ["embedding", "created_by", "updated_by"]
    filter_horizontal = ["disorders"]


@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "specialty_list",
        "created_by",
        "updated_by",
        "avatar_url",
        "bio",
        "date_of_birth",
        "gender",
        "user",
        "license_number",
        "years_of_experience",
        "availability",
    )
    list_filter = (
        "created",
        "modified",
        "created_by",
        "updated_by",
        "date_of_birth",
        "user",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("specialties")

    def specialty_list(self, obj):
        return ", ".join(o.name for o in obj.specialties.all())


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "created_by",
        "updated_by",
        "avatar_url",
        "bio",
        "date_of_birth",
        "gender",
        "user",
        "certification",
        "areas_of_expertise",
        "coaching_philosophy",
        "availability",
        "rating",
        "specialization",
        "weight",
        "height",
        "_order",
    )
    list_filter = (
        "created",
        "modified",
        "created_by",
        "updated_by",
        "date_of_birth",
        "user",
    )
