# Generated by Django 5.1.1 on 2024-09-12 06:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0002_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="response",
            old_name="answer",
            new_name="content",
        ),
        migrations.AlterUniqueTogether(
            name="response",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="question",
            name="assessment_type",
        ),
        migrations.AddField(
            model_name="question",
            name="assessment",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="questions",
                to="assessments.assessment",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="response",
            name="allow_multiple",
            field=models.BooleanField(default=False),
        ),
        migrations.RemoveField(
            model_name="response",
            name="assessment",
        ),
        migrations.RemoveField(
            model_name="response",
            name="is_valid",
        ),
    ]
