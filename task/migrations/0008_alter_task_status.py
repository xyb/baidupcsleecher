# Generated by Django 4.1.7 on 2023-03-22 16:24
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("task", "0007_task_full_download_now"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="status",
            field=models.CharField(
                choices=[
                    ("Inited", "Inited"),
                    ("Started", "Started"),
                    ("Transferred", "Transferred"),
                    ("SampleDLed", "Sampling Downloaded"),
                    ("Finished", "Finished"),
                ],
                default="Inited",
                editable=False,
                max_length=12,
            ),
        ),
    ]
