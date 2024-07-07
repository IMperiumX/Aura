# Generated by Django 4.2.13 on 2024-07-06 13:21
import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    """ """

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_password_expired",
            field=models.BooleanField(
                default=False,
                help_text=
                "If set to true then the user needs to change the password on next sign in.",
                verbose_name="password expired",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_password_change",
            field=models.DateTimeField(
                help_text="The date the password was changed last.",
                null=True,
                verbose_name="date of last password change",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=75,
                                    unique=True,
                                    verbose_name="email address"),
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "avatar_url",
                    models.CharField(max_length=120,
                                     verbose_name="avatar url"),
                ),
                ("bio", models.TextField(blank=True,
                                         verbose_name="Biography")),
                ("date_of_birth", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "gender",
                    models.CharField(choices=[("m", " Male"), ("f", "Female")],
                                     max_length=1),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "User Profiles",
            },
        ),
        migrations.CreateModel(
            name="TherapistProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "avatar_url",
                    models.CharField(max_length=120,
                                     verbose_name="avatar url"),
                ),
                ("bio", models.TextField(blank=True,
                                         verbose_name="Biography")),
                ("date_of_birth", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "gender",
                    models.CharField(choices=[("m", " Male"), ("f", "Female")],
                                     max_length=1),
                ),
                ("license_number", models.CharField(max_length=50)),
                ("specialties", models.CharField(max_length=255)),
                (
                    "years_of_experience",
                    models.PositiveIntegerField(
                        verbose_name="Years of Experience"),
                ),
                (
                    "availability",
                    models.JSONField(blank=True,
                                     null=True,
                                     verbose_name="Availability Schedule"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Therapists",
            },
        ),
        migrations.CreateModel(
            name="PatientProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "avatar_url",
                    models.CharField(max_length=120,
                                     verbose_name="avatar url"),
                ),
                ("bio", models.TextField(blank=True,
                                         verbose_name="Biography")),
                ("date_of_birth", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "gender",
                    models.CharField(choices=[("m", " Male"), ("f", "Female")],
                                     max_length=1),
                ),
                ("medical_record_number", models.CharField(max_length=20)),
                ("insurance_provider", models.CharField(max_length=100)),
                ("insurance_policy_number", models.CharField(max_length=20)),
                ("emergency_contact_name", models.CharField(max_length=100)),
                ("emergency_contact_phone", models.CharField(max_length=20)),
                ("allergies", models.TextField()),
                ("medical_conditions", models.TextField()),
                ("medical_history", models.JSONField(blank=True, null=True)),
                ("current_medications", models.JSONField(blank=True,
                                                         null=True)),
                ("health_data", models.JSONField(blank=True, null=True)),
                ("preferences", models.JSONField(blank=True, null=True)),
                (
                    "weight",
                    models.FloatField(blank=True,
                                      null=True,
                                      verbose_name="Weight (kg)"),
                ),
                (
                    "height",
                    models.FloatField(blank=True,
                                      null=True,
                                      verbose_name="Height (cm)"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Patients",
            },
        ),
        migrations.CreateModel(
            name="CoachProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "avatar_url",
                    models.CharField(max_length=120,
                                     verbose_name="avatar url"),
                ),
                ("bio", models.TextField(blank=True,
                                         verbose_name="Biography")),
                ("date_of_birth", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "gender",
                    models.CharField(choices=[("m", " Male"), ("f", "Female")],
                                     max_length=1),
                ),
                ("certification", models.CharField(max_length=100)),
                ("areas_of_expertise", models.CharField(max_length=25)),
                ("coaching_philosophy", models.TextField(blank=True)),
                (
                    "availability",
                    models.JSONField(blank=True,
                                     null=True,
                                     verbose_name="Availability Schedule"),
                ),
                (
                    "rating",
                    models.DecimalField(decimal_places=2,
                                        max_digits=3,
                                        verbose_name="Rating"),
                ),
                ("specialization", models.CharField(max_length=100)),
                (
                    "weight",
                    models.FloatField(blank=True,
                                      null=True,
                                      verbose_name="Weight (kg)"),
                ),
                (
                    "height",
                    models.FloatField(blank=True,
                                      null=True,
                                      verbose_name="Height (cm)"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Coaches",
                "order_with_respect_to": "rating",
            },
        ),
    ]
