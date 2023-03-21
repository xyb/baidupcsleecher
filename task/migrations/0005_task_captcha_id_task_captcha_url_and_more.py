# Generated by Django 4.1.7 on 2023-03-21 03:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("task", "0004_task_shared_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="captcha_id",
            field=models.CharField(default="", editable=False, max_length=100),
        ),
        migrations.AddField(
            model_name="task",
            name="captcha_url",
            field=models.CharField(default="", editable=False, max_length=200),
        ),
        migrations.AlterField(
            model_name="task",
            name="captcha_code",
            field=models.CharField(default="", editable=False, max_length=12),
        ),
        migrations.AlterField(
            model_name="task",
            name="shared_id",
            field=models.CharField(default="", editable=False, max_length=50),
        ),
    ]
