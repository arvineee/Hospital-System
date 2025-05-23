# Generated by Django 5.2 on 2025-04-20 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Patient_register",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("age", models.IntegerField()),
                ("contact", models.IntegerField(null=True)),
                ("adm_date", models.DateField(auto_now_add=True)),
                ("sex", models.CharField(max_length=10)),
            ],
        ),
    ]
