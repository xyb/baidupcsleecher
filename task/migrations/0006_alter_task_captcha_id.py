# Generated by Django 4.1.7 on 2023-03-22 03:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("task", "0005_task_captcha_id_task_captcha_url_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="captcha_id",
            field=models.CharField(default="", editable=False, max_length=200),
        ),
    ]