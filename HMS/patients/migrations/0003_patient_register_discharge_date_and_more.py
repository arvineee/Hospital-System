# Generated by Django 5.2 on 2025-04-28 13:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0002_patient_register_prescribed_drug"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient_register",
            name="discharge_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="patient_register",
            name="is_discharged",
            field=models.BooleanField(default=False),
        ),
    ]
