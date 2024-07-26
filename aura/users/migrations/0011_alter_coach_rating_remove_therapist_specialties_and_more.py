# Generated by Django 4.2.13 on 2024-07-25 20:00

from decimal import Decimal
from django.db import migrations, models
import taggit.managers


class Migration(migrations.Migration):
    dependencies = [
        (
            "taggit",
            "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx",
        ),
        ("users", "0010_alter_patient_emergency_contact_phone_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="coach",
            name="rating",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                max_digits=3,
                verbose_name="Rating",
            ),
        ),
        migrations.RemoveField(
            model_name="therapist",
            name="specialties",
        ),
        migrations.AddField(
            model_name="therapist",
            name="specialties",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="taggit.TaggedItem",
                to="taggit.Tag",
                verbose_name="Tags",
            ),
        ),
    ]
