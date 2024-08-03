# Generated by Django 5.0.6 on 2024-08-03 18:40

import django.utils.timezone
import model_utils.fields
import recurrence.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
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
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                ("message", models.TextField(verbose_name="Message")),
                ("response", models.TextField(verbose_name="Response")),
                ("conversation_log", models.TextField()),
                (
                    "interaction_date",
                    models.DateTimeField(default=django.utils.timezone.now, null=True),
                ),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
            ],
            options={
                "verbose_name": "Chatbot Interaction",
                "verbose_name_plural": "Chatbot Interactions",
                "ordering": ["created"],
            },
        ),
        migrations.CreateModel(
            name="Disorder",
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
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("mental", "Mental"),
                            ("physical", "Physical"),
                            ("genetic", "Genetic"),
                            ("emotional", "Emotional"),
                            ("functional", "Functional"),
                            ("mood", "Mood"),
                            ("anxiety", "Anxiety"),
                            ("personality", "Personality"),
                            ("psychotic", "Psychotic"),
                        ],
                        max_length=20,
                        verbose_name="Type",
                    ),
                ),
                ("causes", models.TextField(blank=True)),
                ("symptoms", models.TextField(blank=True)),
                ("diagnosis", models.TextField(blank=True)),
                ("treatment", models.TextField(blank=True)),
                ("prevention", models.TextField(blank=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="TherapyApproach",
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
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField()),
            ],
            options={
                "verbose_name": "Therapy Approach",
                "verbose_name_plural": "Therapy Approaches",
            },
        ),
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
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
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
                ("summary", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
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
                    "target_audience",
                    models.CharField(
                        choices=[
                            ("individual", "Individual"),
                            ("couples", "Couples"),
                            ("teens", "Teens"),
                            ("medication", "Medication"),
                            ("veterans", "Veterans"),
                        ],
                        max_length=10,
                        verbose_name="Session Type",
                    ),
                ),
                ("recurrences", recurrence.fields.RecurrenceField()),
            ],
            options={
                "verbose_name": "Therapy Session",
                "verbose_name_plural": "Therapy Sessions",
                "ordering": ["scheduled_at"],
            },
        ),
    ]
