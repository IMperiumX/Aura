# Generated by Django 5.0.6 on 2024-07-26 23:20

import pgvector.django.indexes
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        (
            "taggit",
            "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx",
        ),
        ("users", "0004_physician_review_delete_patientprofile_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="therapist",
            index=pgvector.django.indexes.HnswIndex(
                ef_construction=64,
                fields=["embedding"],
                m=16,
                name="th_27072024_embedding_index",
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]
