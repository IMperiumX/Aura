# Generated by Django 4.2.13 on 2024-07-05 05:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TherapySession",
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
                    "session_type",
                    models.CharField(
                        choices=[
                            ("chat", "Chat"),
                            ("video", "Video"),
                            ("audio", "Audio"),
                        ],
                        max_length=5,
                        verbose_name="Session Type",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                            ("completed", "Completed"),
                        ],
                        default="pending",
                        max_length=10,
                        verbose_name="Status",
                    ),
                ),
                ("scheduled_at", models.DateTimeField(verbose_name="Scheduled At")),
                (
                    "started_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Started At"
                    ),
                ),
                (
                    "ended_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Ended At"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="therapy_sessions_as_patient",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Patient",
                    ),
                ),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="therapy_sessions_as_therapist",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Therapist",
                    ),
                ),
            ],
            options={
                "verbose_name": "Therapy Session",
                "verbose_name_plural": "Therapy Sessions",
                "ordering": ["scheduled_at"],
            },
        ),
        migrations.CreateModel(
            name="ChatbotInteraction",
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
                ("message", models.TextField(verbose_name="Message")),
                ("response", models.TextField(verbose_name="Response")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chatbot_interactions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Chatbot Interaction",
                "verbose_name_plural": "Chatbot Interactions",
                "ordering": ["created_at"],
            },
        ),
    ]
