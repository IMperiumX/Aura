# Generated by Django 5.0.6 on 2024-08-03 18:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("mentalhealth", "0001_initial"),
        ("users", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="chatbotinteraction",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chatbot_interactions",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User",
            ),
        ),
        migrations.AddField(
            model_name="therapysession",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="therapy_sessions_as_patient",
                to="users.patient",
                verbose_name="Patient",
            ),
        ),
        migrations.AddField(
            model_name="therapysession",
            name="therapist",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="therapy_sessions_as_therapist",
                to="users.therapist",
                verbose_name="Therapist",
            ),
        ),
    ]