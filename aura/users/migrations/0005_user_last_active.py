# Generated by Django 5.1.1 on 2025-02-05 05:54

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_alter_userip_country_code_alter_userip_region_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="last_active",
            field=models.DateTimeField(
                default=django.utils.timezone.now, null=True, verbose_name="last active"
            ),
        ),
    ]
