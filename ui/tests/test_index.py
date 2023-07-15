from django.test import Client
from django.test import TestCase
from django.urls import reverse

from task.models import Task


class TaskUITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        url = reverse("task-list")
        data = {
            "shared_link": "https://pan.baidu.com/s/badbeef?pwd=bee",
        }
        self.client.post(url, data, format="json")
        self.client.post(
            url,
            {"shared_link": "https://pan.baidu.com/s/feedcafe?pwd=c0de"},
            format="json",
        )
        task = Task.objects.get(id=1)
        task.transfer_completed_at = task.created_at
        task.sample_downloaded_at = task.created_at
        task.full_downloaded_at = task.created_at
        task.status = task.Status.FINISHED
        task.save()

    def test_task_list(self):
        url = reverse("index")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"badbeef" in response.content)
        self.assertTrue(b"bee" in response.content)
        self.assertTrue(b"Next Page" not in response.content)

    def test_next_page(self):
        url = reverse("index")

        response = self.client.get(url, {"per_page": 1, "page": 1})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"feedcafe" in response.content)
        self.assertTrue(b"c0de" in response.content)
        self.assertTrue(b"Next Page" in response.content)
        self.assertTrue(b"Last Page" in response.content)
        self.assertTrue(b"1 / 2 Pages" in response.content)

    def test_prev_page(self):
        url = reverse("index")

        response = self.client.get(url, {"per_page": 1, "page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"badbeef" in response.content)
        self.assertTrue(b"bee" in response.content)
        self.assertTrue(b"Prev Page" in response.content)
        self.assertTrue(b"First Page" in response.content)
        self.assertTrue(b"2 / 2 Pages" in response.content)
