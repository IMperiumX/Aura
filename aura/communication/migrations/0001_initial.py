# Generated by Django 5.0.6 on 2024-08-28 19:01

import datetime
import django.db.models.deletion
import django.utils.timezone
import django_cryptography.fields
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FileContent",
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
                ("hash", models.CharField(max_length=64, unique=True)),
                ("content", models.FileField(upload_to="file_contents/")),
            ],
        ),
        migrations.CreateModel(
            name="Message",
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
                    "text",
                    django_cryptography.fields.encrypt(
                        models.TextField(verbose_name="text")
                    ),
                ),
                (
                    "read_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="read at"),
                ),
                (
                    "message_type",
                    models.CharField(
                        choices=[
                            (None, "(Unknown)"),
                            ("text", "Text"),
                            ("system", "System"),
                            ("file", "File"),
                        ],
                        default="text",
                        max_length=50,
                        verbose_name="message type",
                    ),
                ),
                (
                    "data_retention_period",
                    models.DurationField(
                        default=datetime.timedelta(days=365),
                        verbose_name="data retention period",
                    ),
                ),
            ],
            options={
                "verbose_name": "message",
                "verbose_name_plural": "messages",
            },
        ),
        migrations.CreateModel(
            name="Thread",
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
                    "subject",
                    models.CharField(
                        blank=True, default="", max_length=100, verbose_name="subject"
                    ),
                ),
                (
                    "is_group",
                    models.BooleanField(default=False, verbose_name="is group"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="is active"),
                ),
            ],
            options={
                "verbose_name": "thread",
                "verbose_name_plural": "threads",
            },
        ),
        migrations.CreateModel(
            name="Attachment",
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
                ("name", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=100)),
                ("size", models.PositiveIntegerField()),
                ("version_number", models.PositiveIntegerField(default=1)),
                (
                    "previous_version",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="next_version",
                        to="communication.attachment",
                    ),
                ),
                (
                    "file_content",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="communication.filecontent",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Folder",
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
                ("name", models.CharField(max_length=255, verbose_name="name")),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="children",
                        to="communication.folder",
                        verbose_name="parent",
                    ),
                ),
            ],
            options={
                "verbose_name": "folder",
                "verbose_name_plural": "folders",
            },
        ),
    ]
