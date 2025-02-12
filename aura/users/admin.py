from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import admin as auth_admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import Coach
from .models import Patient
from .models import Therapist
from .models import User
from .userip import UserIP

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
        )
        export_order = fields


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin, ImportExportModelAdmin):
    resource_class = UserResource
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name",)}),
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
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["email", "name", "is_superuser", "date_joined", "get_profile_type"]
    list_filter = ["is_superuser", "is_active", "groups"]
    search_fields = ["name", "email"]
    ordering = ["-date_joined"]
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = ["date_joined", "last_login"]

    @admin.display(
        description="Profile Type",
    )
    def get_profile_type(self, obj):
        if hasattr(obj, "patient_profile"):
            return format_html('<span style="color: green;">Patient</span>')
        if hasattr(obj, "therapist_profile"):
            return format_html('<span style="color: blue;">Therapist</span>')
        if hasattr(obj, "coach_profile"):
            return format_html('<span style="color: purple;">Coach</span>')
        return format_html('<span style="color: red;">No Profile</span>')

    actions = ["make_active", "make_inactive"]

    @admin.action(description="Mark selected users as active")
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"{updated} users were successfully marked as active.",
            messages.SUCCESS,
        )

    @admin.action(description="Mark selected users as inactive")
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{updated} users were successfully marked as inactive.",
            messages.SUCCESS,
        )


class PatientInline(admin.StackedInline):
    model = Patient
    fk_name = "user"
    verbose_name_plural = "Patient Profile"
    can_delete = False
    show_change_link = True
    classes = ["collapse"]
    extra = 0


class CoachInline(admin.StackedInline):
    model = Coach
    fk_name = "user"
    verbose_name_plural = "Coach Profile"
    can_delete = False
    show_change_link = True
    classes = ["collapse"]
    extra = 0


class TherapistInline(admin.StackedInline):
    model = Therapist
    fk_name = "user"
    verbose_name_plural = "Therapist Profile"
    can_delete = False
    show_change_link = True
    classes = ["collapse"]
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "date_of_birth",
        "gender",
        "medical_record_number",
        "insurance_provider",
        "created",
        "modified",
    )
    list_filter = ("gender", "insurance_provider", "created", "modified")
    search_fields = ("user__email", "user__name", "medical_record_number")
    readonly_fields = ["embedding", "created_by", "updated_by", "created", "modified"]
    filter_horizontal = ["disorders"]
    raw_id_fields = ("user",)

    fieldsets = (
        (None, {"fields": ("user", "avatar_url", "bio", "date_of_birth", "gender")}),
        (
            "Medical Information",
            {
                "fields": (
                    "medical_record_number",
                    "insurance_provider",
                    "insurance_policy_number",
                    "disorders",
                ),
            },
        ),
        (
            "Emergency Contact",
            {"fields": ("emergency_contact_name", "emergency_contact_phone")},
        ),
        (
            "Health Data",
            {
                "fields": (
                    "allergies",
                    "medical_conditions",
                    "medical_history",
                    "current_medications",
                    "health_data",
                ),
            },
        ),
        ("Physical Attributes", {"fields": ("weight", "height")}),
        (
            "System Fields",
            {
                "fields": (
                    "embedding",
                    "created_by",
                    "updated_by",
                    "created",
                    "modified",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "license_number",
        "years_of_experience",
        "specialty_list",
        "created",
        "modified",
    )
    list_filter = ("years_of_experience", "created", "modified")
    search_fields = ("user__email", "user__name", "license_number")
    readonly_fields = ["embedding", "created", "modified"]
    raw_id_fields = ("user",)

    fieldsets = (
        (None, {"fields": ("user", "avatar_url", "bio", "date_of_birth", "gender")}),
        (
            "Professional Information",
            {
                "fields": (
                    "license_number",
                    "years_of_experience",
                    "specialties",
                    "availability",
                ),
            },
        ),
        (
            "System Fields",
            {"fields": ("embedding", "created", "modified"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("specialties")
            .select_related("user")
        )

    @admin.display(
        description="Specialties",
    )
    def specialty_list(self, obj):
        return ", ".join(o.name for o in obj.specialties.all())


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "certification",
        "rating",
        "specialization",
        "created",
        "modified",
    )
    list_filter = ("certification", "rating", "created", "modified")
    search_fields = ("user__email", "user__name", "certification")
    readonly_fields = ["created", "modified"]
    raw_id_fields = ("user",)

    fieldsets = (
        (None, {"fields": ("user", "avatar_url", "bio", "date_of_birth", "gender")}),
        (
            "Professional Information",
            {
                "fields": (
                    "certification",
                    "areas_of_expertise",
                    "coaching_philosophy",
                    "availability",
                ),
            },
        ),
        ("Performance", {"fields": ("rating", "specialization")}),
        ("Physical Attributes", {"fields": ("weight", "height")}),
        (
            "System Fields",
            {"fields": ("created", "modified"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(UserIP)
class UserIPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "ip_address",
        "country_code",
        "region_code",
        "first_seen",
        "last_seen",
    )
    list_filter = ("user", "first_seen", "last_seen")
