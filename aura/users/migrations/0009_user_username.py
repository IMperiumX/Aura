# Generated by Django 5.0.6 on 2024-08-02 18:23

import django.contrib.auth.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0008_rename_review_review_content"),
    ]
    operations = [
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(
                default=None,
                error_messages={"unique": "A user with that username already exists."},
                help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                max_length=150,
                unique=True,
                validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                verbose_name="username",
                null=True
            ),
            preserve_default=False,
        ),
    ]