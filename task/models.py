from django.conf import settings
from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        INITED = "Inited"
        STARTED = "Started"
        FINISHED = "Finished"

    shared_link = models.CharField(max_length=100)
    shared_password = models.CharField(max_length=4, blank=True, null=True)
    status = models.CharField(
        max_length=10,
        editable=False,
        choices=Status.choices,
        default=Status.INITED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True, editable=False)
    finished_at = models.DateTimeField(blank=True, null=True, editable=False)
    failed = models.BooleanField(default=False, editable=False)
    message = models.CharField(max_length=1000, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["shared_link"]),
        ]

    def get_data_path(self):
        return settings.DATA_DIR / str(self.id)
