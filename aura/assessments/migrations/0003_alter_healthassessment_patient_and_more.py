# Generated by Django 4.2.13 on 2024-07-07 03:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_coach_patient_profile_therapist_and_more"),
        ("assessments", "0002_alter_healthassessment_created_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="healthassessment",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="health_assessments",
                to="users.patient",
            ),
        ),
        migrations.AlterField(
            model_name="healthriskprediction",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="health_risk_predictions",
                to="users.patient",
                verbose_name="User",
            ),
        ),
    ]
