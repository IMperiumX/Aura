# Generated by Django 5.0.6 on 2024-08-02 17:01

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0007_rename_user_review_reviewer"),
    ]

    operations = [
        migrations.RenameField(
            model_name="review",
            old_name="review",
            new_name="content",
        ),
    ]
