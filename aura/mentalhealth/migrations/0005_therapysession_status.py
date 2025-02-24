# Generated by Django 5.1.1 on 2025-02-11 12:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mentalhealth', '0004_alter_disorder_causes_alter_disorder_symptoms'),
    ]

    operations = [
        migrations.AddField(
            model_name='therapysession',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='pending', max_length=20, verbose_name='Status'),
        ),
    ]
