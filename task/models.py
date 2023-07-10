from json import dumps
from os import makedirs
from os import walk
from os.path import getsize
from os.path import join
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models import Q


class Task(models.Model):
    class Status(models.TextChoices):
        INITED = "Inited"
        STARTED = "Started"
        TRANSFERRED = "Transferred"
        SAMPLING_DOWNLOADED = "SampleDLed"
        FINISHED = "Finished"

    shared_id = models.CharField(max_length=50, default="", editable=False)
    shared_link = models.CharField(max_length=100)
    shared_password = models.CharField(max_length=4, blank=True, null=True)
    status = models.CharField(
        max_length=12,
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
    full_download_now = models.BooleanField(default=False, editable=False)
    failed = models.BooleanField(default=False, editable=False)
    message = models.CharField(max_length=1000, editable=False)
    files = models.TextField(editable=False)
    captcha = models.BinaryField(editable=False, default=b"")
    captcha_required = models.BooleanField(default=False, editable=False)
    captcha_code = models.CharField(
        max_length=12,
        default="",
        editable=False,
    )
    captcha_id = models.CharField(
        max_length=200,
        default="",
        editable=False,
    )
    captcha_url = models.CharField(
        max_length=200,
        default="",
        editable=False,
    )

    class Meta:
        indexes = [
            models.Index(fields=["shared_link"]),
            models.Index(fields=["status"]),
        ]

    @property
    def path(self):
        return f"{self.shared_id}.{self.shared_password}"

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
            path = file["path"]
            if path.startswith(remote_base_dir):
                # strip remote base dir
                sub_path = file["path"][len(remote_base_dir) :].lstrip("/")
                file["path"] = sub_path
            file_list.append(file)
        self.files = dumps(file_list)

    def list_local_files(self):
        data_path = self.data_path
        for root, dirs, files in walk(data_path):
            for file in files:
                filepath = join(root, file)
                sub_path = filepath[len(str(data_path)) + 1 :]
                yield {"file": sub_path, "size": getsize(filepath)}

    @classmethod
    def filter_ready_to_transfer(cls):
        inited = Q(status=cls.Status.INITED)
        tasks = cls.objects.filter(inited)
        return tasks

    @classmethod
    def filter_transferd(cls):
        return cls.objects.filter(status=cls.Status.TRANSFERRED)

    @classmethod
    def filter_sampling_downloaded(cls):
        return cls.objects.filter(
            status=cls.Status.SAMPLING_DOWNLOADED,
            full_download_now=True,
        )

    @classmethod
    def filter_failed(cls):
        return cls.objects.filter(failed=True)

    @property
    def is_waiting_for_captcha_code(self):
        return self.status == self.Status.STARTED and self.captcha_required

    def restart(self):
        self.status = self.Status.INITED
        self.failed = False
        self.message = ""
        self.save()

    def restart_downloading(self):
        self.status = self.Status.TRANSFERRED
        self.failed = False
        self.message = ""
        self.save()

    def get_steps(self):
        found_current = False
        status = self.Status
        if not self.failed:
            for name, (start_status, end_status) in [
                ("waiting_assign", [status.INITED, status.STARTED]),
                ("transferring", [status.STARTED, status.TRANSFERRED]),
                (
                    "downloading_samplings",
                    [status.TRANSFERRED, status.SAMPLING_DOWNLOADED],
                ),
                ("downloading_files", [status.SAMPLING_DOWNLOADED, status.FINISHED]),
            ]:
                if self.status == start_status:
                    found_current = True
                    yield name, "doing"
                elif found_current:
                    yield name, "todo"
                else:
                    yield name, "done"
        else:
            for name, (time_prev, time_completed) in [
                ("waiting_assign", [self.created_at, self.started_at]),
                ("transferring", [self.started_at, self.transfer_completed_at]),
                (
                    "downloading_samplings",
                    [
                        self.transfer_completed_at,
                        self.sample_downloaded_at,
                    ],
                ),
                (
                    "downloading_files",
                    [
                        self.sample_downloaded_at,
                        self.full_downloaded_at,
                    ],
                ),
            ]:
                if time_completed:
                    yield name, "done"
                elif time_prev:
                    yield name, "failed"
                else:
                    yield name, "todo"

    def get_current_step(self):
        for name, done in self.get_steps():
            if done in ["doing", "failed"]:
                return name

    def get_resume_method_name(self):
        resume_methods = {
            "waiting_assign": "restart",
            "transferring": "restart",
            "downloading_samplings": "restart_downloading",
            "downloading_files": "restart_downloading",
        }
        step_name = self.get_current_step()
        return resume_methods[step_name]

    def resume(self):
        method = getattr(self, self.get_resume_method_name())
        method()

    @classmethod
    def schedule_resume_failed(cls):
        for task in cls.filter_failed():
            task.resume()
