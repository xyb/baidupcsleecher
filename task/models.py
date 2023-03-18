from json import dumps
from os import makedirs
from pathlib import Path

from django.conf import settings
from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        INITED = "Inited"
        STARTED = "Started"
        TRANSFERED = "Transfered"
        SAMPLING_DOWNLOADED = "SampleDLed"
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
    finished_at = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
    )
    transfer_completed_at = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
    )
    file_listed_at = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
    )
    sample_downloaded_at = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
    )
    full_downloaded_at = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
    )
    failed = models.BooleanField(default=False, editable=False)
    captcha_required = models.BooleanField(default=False, editable=False)
    captcha_code = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        editable=False,
    )
    message = models.CharField(max_length=1000, editable=False)
    files = models.TextField(editable=False)
    captcha = models.BinaryField(editable=False, default=b'')

    class Meta:
        indexes = [
            models.Index(fields=["shared_link"]),
            models.Index(fields=["status"]),
        ]

    @property
    def path(self):
        time = self.created_at.isoformat()[:19]
        time = time.replace('-', '').replace(':', '')
        return f"{time}_{self.id}"

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
        return str(Path(settings.REMOTE_LEECHER_DIR) / self.path)

    def set_files(self, files):
        remote_base_dir = str(Path(settings.REMOTE_LEECHER_DIR) / self.path)
        file_list = []
        for file in files:
            path = file['path']
            if path.startswith(remote_base_dir):
                # strip remote base dir
                sub_path = file['path'][len(remote_base_dir):].lstrip('/')
                file['path'] = sub_path
            file_list.append(file)
        self.files = dumps(file_list)

    @classmethod
    def filter_inited(cls):
        return cls.objects.filter(status=cls.Status.INITED)

    @classmethod
    def filter_transferd(cls):
        return cls.objects.filter(status=cls.Status.TRANSFERED)

    @classmethod
    def filter_sampling_downloaded(cls):
        return cls.objects.filter(status=cls.Status.SAMPLING_DOWNLOADED)
