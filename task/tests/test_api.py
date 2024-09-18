from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Task
from ..serializers import TaskSerializer
from ..utils import list_files


def touch_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    open(path, "w").write("")


def touch_task_files(task: Task):
    for f in task.load_files():
        if f["is_file"]:
            touch_file(path=task.data_path / f["path"])
            touch_file(path=task.sample_data_path / f["path"])


class TaskViewSetTestCase(APITestCase):
    def setUp(self):
        self.task = Task.objects.create(
            shared_link="https://pan.baidu.com/s/123abc?pwd=def",
            shared_id="123abc",
            shared_password="def",
        )
        self.remote_files = [
            {
                "path": "张楚",
                "is_dir": True,
                "is_file": False,
                "size": 0,
                "md5": None,
            },
            {
                "path": "张楚/孤独的人是可耻的.mp3",
                "is_dir": False,
                "is_file": True,
                "size": 9518361,
                "md5": "6d5bea8001e9db88f8cd8145aaf8cce4",
            },
            {
                "path": "张楚/蚂蚁蚂蚁.mp3",
                "is_dir": False,
                "is_file": True,
                "size": 1234567,
                "md5": "1eec826501e9db88f8cd8145aaf8cce4",
            },
        ]
        self.task.set_files(self.remote_files)
        self.task.save()

    def test_create_task(self):
        url = reverse("task-list")
        data = {
            "shared_link": "https://pan.baidu.com/s/badbeef?pwd=bee",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 2)
        data = response.json()
        assert data["full_download_now"] is False
        assert data["current_progressing_stage"] == "waiting_assign"
        assert data["is_downloading"] is False
        assert set(data.keys()) == {
            "callback",
            "captcha_required",
            "captcha_url",
            "captcha",
            "created_at",
            "current_progressing_stage",
            "done",
            "failed",
            "file_listed_at",
            "finished_at",
            "full_download_now",
            "full_downloaded_at",
            "id",
            "is_downloading",
            "largest_file_size",
            "largest_file",
            "message",
            "path",
            "recoverable",
            "retry_times",
            "sample_downloaded_at",
            "sample_path",
            "shared_id",
            "shared_link",
            "shared_password",
            "started_at",
            "status",
            "total_files",
            "total_size",
            "transfer_completed_at",
        }

    def test_create_task_full_download_now(self):
        url = reverse("task-list")
        data = {
            "shared_link": "https://pan.baidu.com/s/badbeef?pwd=bee",
            "full_download_now": True,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 2)
        assert response.json()["full_download_now"] is True

    def test_retrieve_task(self):
        url = reverse("task-detail", args=[self.task.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, TaskSerializer(self.task).data)

    def test_destroy_task(self):
        url = reverse("task-detail", args=[self.task.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Task.objects.count(), 0)

    def test_list_tasks(self):
        url = reverse("task-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_files_action(self):
        url = reverse("task-files", args=[self.task.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)

    def test_captcha_action(self):
        url = reverse("task-captcha", args=[self.task.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    @patch("task.views.get_baidupcs_client")
    def test_captcha_code_action(self, mock_get_baidupcs_client):
        self.task.status = self.task.Status.STARTED
        self.task.captcha_required = True
        self.task.save()
        url = reverse("task-captcha-code", args=[self.task.id])
        data = {"code": "1234"}
        mock_get_baidupcs_client.return_value = Mock()
        mock_get_baidupcs_client.return_value.list_files = MagicMock(return_value=[])

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], 1)
        task = Task.objects.get(pk=self.task.id)
        self.assertEqual(task.captcha_code, "1234")
        self.assertEqual(task.captcha_required, False)
        self.assertEqual(task.status, task.Status.TRANSFERRED)

    def test_full_download_now_action(self):
        self.assertEqual(self.task.full_download_now, False)
        url = reverse("task-full-download-now", args=[self.task.id])
        data = {"full_download_now": True}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], 1)
        task = Task.objects.get(pk=self.task.id)
        self.assertEqual(task.full_download_now, True)

    def test_restart(self):
        self.task.status = self.task.Status.STARTED
        self.task.failed = True
        self.task.message = "error"
        self.task.save()
        url = reverse("task-restart", args=[self.task.id])
        data = {}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], self.task.Status.INITED.value)
        task = Task.objects.get(pk=self.task.id)
        self.assertEqual(task.status, self.task.Status.INITED)
        self.assertEqual(task.failed, False)
        self.assertEqual(task.message, "")

    def test_restart_downloading(self):
        self.task.status = self.task.Status.FINISHED
        self.task.failed = True
        self.task.message = "error"
        self.task.save()
        url = reverse("task-restart-downloading", args=[self.task.id])
        data = {}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], self.task.Status.TRANSFERRED.value)
        task = Task.objects.get(pk=self.task.id)
        self.assertEqual(task.status, self.task.Status.TRANSFERRED)
        self.assertEqual(task.failed, False)
        self.assertEqual(task.message, "")

    def test_resume(self):
        task = self.task
        task.status = task.Status.SAMPLING_DOWNLOADED
        task.started_at = task.created_at
        task.transfer_completed_at = task.created_at
        task.sample_downloaded_at = task.created_at
        task.failed = True
        task.message = "error"
        task.save()
        url = reverse("task-resume", args=[task.id])
        data = {}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == Task.Status.TRANSFERRED.value
        task = Task.objects.get(pk=task.id)
        assert task.status == Task.Status.TRANSFERRED
        assert task.failed is False
        assert task.message == ""

    def test_resume_not_failed_task_do_nothing(self):
        task = self.task
        task.status = task.Status.SAMPLING_DOWNLOADED
        task.started_at = task.created_at
        task.transfer_completed_at = task.created_at
        task.sample_downloaded_at = task.created_at
        task.failed = False
        task.message = ""
        task.save()
        url = reverse("task-resume", args=[task.id])
        data = {}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == Task.Status.SAMPLING_DOWNLOADED.value
        task = Task.objects.get(pk=task.id)
        assert task.status == Task.Status.SAMPLING_DOWNLOADED
        assert task.failed is False
        assert task.message == ""

    def test_files(self):
        response = self.client.get(
            reverse("task-files", args=[self.task.id]),
            {},
            format="json",
        )

        assert response.json() == self.remote_files
        assert self.task.total_files == 2
        assert self.task.total_size == 10752928
        assert self.task.largest_file == "张楚/孤独的人是可耻的.mp3"
        assert self.task.largest_file_size == 9518361

    def test_local_files(self):
        response = self.client.get(
            reverse("task-local-files", args=[self.task.id]),
            {},
            format="json",
        )

        assert response.json() == []

    @patch("task.views.get_baidupcs_client")
    def test_delete_remote_files(self, mock_get_baidupcs_client):
        mock_get_baidupcs_client.return_value = Mock()

        id = self.task.id
        response = self.client.delete(reverse("task-files", args=[id]))

        assert response.json() == {str(id): "remote files deleted"}

    def test_delete_local_files(self):
        id = self.task.id
        touch_file(path=self.task.data_path / "test.txt")
        assert list_files(settings.DATA_DIR) != []

        response = self.client.delete(reverse("task-local-files", args=[id]))

        assert response.json() == {str(id): "local files deleted"}
        assert list_files(settings.DATA_DIR) == []

    @patch("task.views.get_baidupcs_client")
    def test_erase(self, mock_get_baidupcs_client):
        mock_get_baidupcs_client.return_value = Mock()

        id = self.task.id
        response = self.client.delete(reverse("task-erase", args=[id]))

        assert response.json() == {str(id): "task deleted"}
        assert len(Task.objects.filter(pk=id)) == 0

    def test_purge(self):
        touch_task_files(self.task)
        self.task.delete()
        assert sorted(list_files(settings.DATA_DIR)) == [
            "123abc.def.sample/张楚/孤独的人是可耻的.mp3",
            "123abc.def.sample/张楚/蚂蚁蚂蚁.mp3",
            "123abc.def/张楚/孤独的人是可耻的.mp3",
            "123abc.def/张楚/蚂蚁蚂蚁.mp3",
        ]

        response = self.client.post(reverse("task-purge"))

        assert response.json() == {"done": True}
        assert sorted(list_files(settings.DATA_DIR)) == [
            "baidupcsleecher_trash/123abc.def.sample/张楚/孤独的人是可耻的.mp3",
            "baidupcsleecher_trash/123abc.def.sample/张楚/蚂蚁蚂蚁.mp3",
            "baidupcsleecher_trash/123abc.def/张楚/孤独的人是可耻的.mp3",
            "baidupcsleecher_trash/123abc.def/张楚/蚂蚁蚂蚁.mp3",
        ]

    def test_purge_all(self):
        touch_task_files(self.task)
        self.task.delete()
        assert list_files(settings.DATA_DIR) != []

        response = self.client.post(
            reverse("task-purge"),
            data={"move_to_trash": False},
            format="json",
        )

        assert response.json() == {"done": True}
        assert list_files(settings.DATA_DIR) == []

    def test_purge_nothing(self):
        touch_task_files(self.task)
        files = sorted(list_files(settings.DATA_DIR))
        assert files == [
            "123abc.def.sample/张楚/孤独的人是可耻的.mp3",
            "123abc.def.sample/张楚/蚂蚁蚂蚁.mp3",
            "123abc.def/张楚/孤独的人是可耻的.mp3",
            "123abc.def/张楚/蚂蚁蚂蚁.mp3",
        ]

        response = self.client.post(reverse("task-purge"))

        assert response.json() == {"done": True}
        assert sorted(list_files(settings.DATA_DIR)) == files
