# Generated by Django 4.1.7 on 2023-03-16 09:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('task', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='captcha',
            field=models.BinaryField(default=b''),
        ),
        migrations.AddField(
            model_name='task',
            name='captcha_code',
            field=models.CharField(blank=True, editable=False, max_length=12, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='captcha_required',
            field=models.BooleanField(default=False, editable=False),
        ),
    ]