# Generated by Django 5.1.1 on 2025-02-05 07:57

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_user_last_active"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="username",
        ),
    ]
