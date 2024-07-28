# Generated by Django 5.0.6 on 2024-07-26 23:19

import pgvector.django.indexes
import pgvector.django.vector
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0005_auto_20240711_1835"),
        ("users", "0003_coach_patient_profile_therapist_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="healthassessment",
            name="embedding",
            field=pgvector.django.vector.VectorField(dimensions=384, null=True),
        ),
        migrations.AlterField(
            model_name="healthassessment",
            name="assessment_type",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("cardiovascular", "Cardiovascular"),
                    ("diabetes", "Diabetes"),
                    ("mental_health", "Mental Health"),
                    ("anxiety", "Anxiety"),
                    ("depression", "Depression"),
                    ("bipolar_disorder", "Bipolar Disorder"),
                    ("ocd", "OCD"),
                    ("ptsd", "PTSD"),
                    ("post_partum_depression", "Post-partum Depression"),
                    ("panic_disorder", "Panic Disorder"),
                ],
                help_text="Type of health assessment conducted",
                max_length=50,
                verbose_name="Assessment Type",
            ),
        ),
        migrations.AddIndex(
            model_name="healthassessment",
            index=pgvector.django.indexes.HnswIndex(
                ef_construction=64,
                fields=["embedding"],
                m=16,
                name="ha_27072024_embedding_index",
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]
