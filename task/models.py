import shutil
from json import dumps
from json import loads
from os import makedirs
from os import walk
from os.path import exists
from os.path import getsize
from os.path import join
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple

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

    shared_id = models.CharField(max_length=50, default="", blank=True)
    shared_link = models.CharField(
        max_length=100,
        help_text="Link, with or without password",
    )
    shared_password = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text="Password, if not included in the shared link",
    )
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
    full_download_now = models.BooleanField(default=False, editable=True)
    failed = models.BooleanField(default=False, editable=False)
    message = models.CharField(max_length=1000, editable=False)
    retry_times = models.IntegerField(default=0, editable=False)
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

    def __repr__(self) -> str:
        return f"<Task id={self.id}, {self.shared_id} with {self.total_files} files>"

    def __str__(self) -> str:
        return repr(self)

    @property
    def path(self) -> str:
        return f"{self.shared_id}.{self.shared_password}"

    @property
    def sample_path(self) -> str:
        return f"{self.path}.sample"

    @property
    def data_path(self) -> Path:
        return settings.DATA_DIR / self.path

    @property
    def sample_data_path(self) -> Path:
        return settings.DATA_DIR / self.sample_path

    def ensure_data_path(self) -> None:
        if not self.data_path.exists():
            makedirs(self.data_path, exists_ok=True)

    @property
    def remote_path(self) -> str:
        return str(Path(settings.REMOTE_LEECHER_DIR) / self.path)

    def set_files(self, files: List[Dict[str, Any]]) -> None:
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

    def load_files(self) -> List[Dict[str, Any]]:
        return loads(self.files or "[]") or []

    def list_remote_files(self, files_only: bool = True) -> List[Dict[str, Any]]:
        if not self.files:
            return []
        files = loads(self.files)
        if files_only:
            files = [i for i in files if i.get("is_file")]
        return files

    @property
    def remote_files(self) -> List[Dict[str, Any]]:
        return self.list_remote_files(files_only=True)

    def list_local_files(
        self,
        samples_only: bool = False,
    ) -> Generator[Dict[str, Any], None, None]:
        if samples_only:
            data_path = self.sample_data_path
        else:
            data_path = self.data_path
        for root, dirs, files in walk(data_path):
            for file in files:
                filepath = join(root, file)
                sub_path = filepath[len(str(data_path)) + 1 :]
                yield {"file": sub_path, "size": getsize(filepath)}

    @property
    def local_files(self) -> List[Dict[str, Any]]:
        return list(self.list_local_files())

    @property
    def local_sample_files(self) -> List[Dict[str, Any]]:
        return list(self.list_local_files(samples_only=True))

    @property
    def total_files(self) -> int:
        return len([f for f in self.load_files() if f["is_file"]])

    @property
    def local_size(self) -> int:
        return sum([f["size"] for f in self.local_files])

    @property
    def total_size(self) -> int:
        return sum([f["size"] for f in self.load_files()])

    def get_largest_file(self) -> Optional[Tuple[int, str]]:
        files = self.load_files()
        if files:
            return max([(f["size"], f["path"]) for f in files])
        return None

    @property
    def largest_file(self) -> Optional[str]:
        largest = self.get_largest_file()
        if largest:
            size, path = largest
            return path
        return None

    @property
    def largest_file_size(self) -> Optional[int]:
        largest = self.get_largest_file()
        if largest:
            size, path = largest
            return size
        return None

    @classmethod
    def filter_ready_to_transfer(cls) -> models.QuerySet:
        inited = Q(status=cls.Status.INITED)
        tasks = cls.objects.filter(inited)
        return tasks

    @classmethod
    def filter_transferd(cls) -> models.QuerySet:
        return cls.objects.filter(status=cls.Status.TRANSFERRED)

    @classmethod
    def filter_sampling_downloaded(cls) -> models.QuerySet:
        return cls.objects.filter(
            status=cls.Status.SAMPLING_DOWNLOADED,
            full_download_now=True,
        )

    @classmethod
    def filter_failed(cls) -> models.QuerySet:
        return cls.objects.filter(failed=True)

    @property
    def is_waiting_for_captcha_code(self) -> bool:
        return self.status == self.Status.STARTED and self.captcha_required

    def _reset_status(self, status: Optional[Status] = None) -> Status:
        if status:
            self.status = status
        self.failed = False
        self.message = ""
        self.inc_retry_times()
        self.save()
        return self.status

    def restart(self) -> Status:
        return self._reset_status(self.Status.INITED)

    def restart_downloading(self) -> Status:
        return self._reset_status(self.Status.TRANSFERRED)

    def get_stages(self) -> Generator[Tuple[str, str], None, None]:
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
                ("waiting_permit_download", [None, None]),
                ("downloading_files", [status.SAMPLING_DOWNLOADED, status.FINISHED]),
            ]:
                if name == "waiting_permit_download":
                    if self.full_download_now:
                        yield name, "done"
                    else:
                        yield name, "todo"
                    continue

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
                ("waiting_permit_download", [None, None]),
                (
                    "downloading_files",
                    [
                        self.sample_downloaded_at,
                        self.full_downloaded_at,
                    ],
                ),
            ]:
                if name == "waiting_permit_download":
                    if self.full_download_now:
                        yield name, "done"
                    else:
                        yield name, "todo"
                    continue

                if time_completed:
                    yield name, "done"
                elif time_prev:
                    yield name, "failed"
                else:
                    yield name, "todo"

    def get_current_stage(self) -> Optional[str]:
        for name, done in self.get_stages():
            if done in ["todo", "doing", "failed"]:
                return name
        return None

    @property
    def current_progressing_stage(self) -> Optional[str]:
        return self.get_current_stage()

    @property
    def is_downloading(self) -> bool:
        return self.current_progressing_stage in [
            "downloading_files",
            "downloading_samplings",
        ]

    def get_resume_method_name(self) -> Optional[str]:
        resume_methods = {
            "waiting_assign": "restart",
            "transferring": "restart",
            "downloading_samplings": "restart_downloading",
            "waiting_permit_download": None,
            "downloading_files": "restart_downloading",
        }
        stage_name = self.get_current_stage()
        if stage_name:
            return resume_methods[stage_name]
        return None

    def inc_retry_times(self) -> int:
        self.retry_times += 1
        self.save()
        return self.retry_times

    def schedule_resume(self) -> None:
        if not self.failed:
            return
        method_name = self.get_resume_method_name()
        if method_name:
            method = getattr(self, method_name)
            method()
        else:
            self._reset_status()

    @classmethod
    def schedule_resume_failed(cls) -> None:
        for task in cls.filter_failed():
            task.schedule_resume()

    @property
    def done(self) -> bool:
        if self.failed:
            return False
        if not self.full_downloaded_at:
            return False
        if self.status != self.Status.FINISHED:
            return False
        return True

    @property
    def recoverable(self) -> bool:
        if not self.failed:
            return False

        e = self.message
        if (
            e == "Remote end closed connection without response"
            or e == "<urlopen error [Errno 104] Connection reset by peer>"
            or e == "BaiduPCS._request"
            or "error_code: -65," in e
            or "操作过于频繁，请您稍后重试" in e
            or "urlopen error [Errno 104] Connection reset by peer" in e
            or "urlopen error [Errno 99] Cannot assign requested address" in e
            or "ConnectionResetError(104, 'Connection reset" in e
        ):
            return True

        if (
            "error_code: 105," in e
            or "啊哦，链接错误没找到文件，请打开正确的分享链接" in e
            or "error_code: 31066," in e
            or "message: 文件不存在" in e
            or "error_code: 2," in e
            or "message: 参数错误" in e
            or "error_code: -7," in e
            or "message: 该分享已删除或已取消" in e
            or "error_code: -12," in e
            or "message: 访问密码错误" in e
            or "error_code: 117," in e
            or "message: 该分享已过期" in e
        ):
            return False

        # assume task is not recoverable by default to avoid flood requests
        return False

    def delete_files(self) -> None:
        if exists(self.sample_path):
            shutil.rmtree(self.sample_path)
        if exists(self.data_path):
            shutil.rmtree(self.data_path)

    def erase(self) -> None:
        self.delete_files()
        self.delete()

    @property
    def sample_downloaded_files(self) -> int:
        return len(list(self.list_local_files()))

    @property
    def sample_download_percent(self) -> float:
        if self.total_files == 0:
            return 0.0
        return 100.0 * self.sample_downloaded_files / self.total_files

    @property
    def downloaded_size(self) -> int:
        return self.local_size

    @property
    def download_percent(self) -> float:
        if self.total_files == 0:
            return 0.0
        return 100.0 * self.downloaded_size / self.total_size
