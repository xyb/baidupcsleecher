from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Task
from ..serializers import TaskSerializer


class TaskViewSetTestCase(APITestCase):
    def setUp(self):
        self.task = Task.objects.create(
            shared_link="https://pan.baidu.com/s/123abc?pwd=def",
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
        assert response.json()["full_download_now"] is False

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
        response = self.client.delete(reverse("task-local-files", args=[id]))

        assert response.json() == {str(id): "local files deleted"}

    @patch("task.views.get_baidupcs_client")
    def test_erase(self, mock_get_baidupcs_client):
        mock_get_baidupcs_client.return_value = Mock()

        id = self.task.id
        response = self.client.delete(reverse("task-erase", args=[id]))

        assert response.json() == {str(id): "task deleted"}
