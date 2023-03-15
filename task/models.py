from os import makedirs

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
    callback = models.CharField(max_length=1024, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True, editable=False)
    finished_at = models.DateTimeField(blank=True, null=True, editable=False)
    transfer_completed_at = models.DateTimeField(blank=True, null=True, editable=False)
    file_listed_at = models.DateTimeField(blank=True, null=True, editable=False)
    sample_downloaded_at = models.DateTimeField(blank=True, null=True, editable=False)
    full_downloaded_at = models.DateTimeField(blank=True, null=True, editable=False)
    failed = models.BooleanField(default=False, editable=False)
    message = models.CharField(max_length=1000, editable=False)
    files = models.TextField(editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["shared_link"]),
            models.Index(fields=["status"]),
        ]

    @property
    def path(self):
        return f"{self.created_at.isoformat()[:19]}_{self.id}"

    @property
    def sample_path(self):
        return f"{self.path}.sample"

    @property
    def data_path(self):
        return settings.DATA_DIR / self.path

    def ensure_data_path(self):
        if not self.data_path.exists():
            makedirs(self.data_path, exists_ok=True)

    @property
    def remote_path(self):
        return self.path
