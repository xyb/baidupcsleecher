# Generated by Django 4.1.7 on 2023-07-11 05:56
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("task", "0009_task_retry_times"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="full_download_now",
            field=models.BooleanField(default=False),
        ),
    ]
