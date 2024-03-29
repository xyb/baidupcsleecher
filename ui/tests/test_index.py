from django.test import Client
from django.test import TestCase
from django.urls import reverse

from task.models import Task


class BaseTestCase(TestCase):
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


class TaskUITestCase(BaseTestCase):
    def test_task_list(self):
        url = reverse("index")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"badbeef" in response.content)
        self.assertTrue(b"bee" in response.content)
        self.assertTrue(b"Next Page" not in response.content)

    def test_list_failed_task(self):
        response = self.client.get(reverse("index"))
        assert b"bg-red" not in response.content
        task = Task.objects.get(id=1)
        task.transfer_completed_at = task.created_at
        task.sample_downloaded_at = task.created_at
        task.full_downloaded_at = None
        task.status = task.Status.FINISHED
        task.failed = True
        task.save()

        response = self.client.get(reverse("index"))

        assert response.status_code == 200
        assert b"bg-red" in response.content

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

    def test_new_task(self):
        assert len(Task.objects.all()) == 2
        response = self.client.get(reverse("index"))
        assert b"hello" not in response.content
        assert b"wrld" not in response.content

        response = self.client.post(
            reverse("new_task"),
            {
                "shared_link": "https://pan.baidu.com/s/hello",
                "shared_password": "wrld",
            },
        )

        self.assertEqual(response.status_code, 302)
        assert len(Task.objects.all()) == 3
        response = self.client.get(reverse("index"))
        assert b"hello" in response.content
        assert b"wrld" in response.content

    def test_new_task_failed(self):
        response = self.client.post(
            reverse("new_task"),
            {
                "shared_link": "wrongurl",
            },
        )

        self.assertEqual(response.status_code, 200)
        assert len(Task.objects.all()) == 2
        response = self.client.get(reverse("index"))
        assert b"wrongurl" not in response.content

    def test_nothing(self):
        response = self.client.get(reverse("nothing"))

        assert response.status_code == 200
        assert response.content == b""


class HTMXTestCase(BaseTestCase):
    def test_task_list(self):
        url = reverse("task_list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"badbeef" in response.content)
        self.assertTrue(b"bee" in response.content)
        self.assertTrue(b"feedcafe" in response.content)
        self.assertTrue(b"c0de" in response.content)

    def test_next_page(self):
        url = reverse("task_list")

        response = self.client.get(url, {"per_page": 1, "page": 1})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"feedcafe" in response.content)
        self.assertTrue(b"c0de" in response.content)
        self.assertTrue(b"Next Page" in response.content)
        self.assertTrue(b"Last Page" in response.content)
        self.assertTrue(b"1 / 2 Pages" in response.content)

    def test_prev_page(self):
        url = reverse("task_list")

        response = self.client.get(url, {"per_page": 1, "page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"badbeef" in response.content)
        self.assertTrue(b"bee" in response.content)
        self.assertTrue(b"Prev Page" in response.content)
        self.assertTrue(b"First Page" in response.content)
        self.assertTrue(b"2 / 2 Pages" in response.content)

    def test_new_task(self):
        assert len(Task.objects.all()) == 2
        response = self.client.get(reverse("index"))
        assert b"hello" not in response.content
        assert b"wrld" not in response.content

        response = self.client.post(
            reverse("new_task"),
            {
                "shared_link": "https://pan.baidu.com/s/hello",
                "shared_password": "wrld",
            },
            headers={"HX-Request": "true"},
        )

        assert "HX-Trigger" in response.headers
        assert "taskListChanged" in response.headers["HX-Trigger"]
        assert response.status_code == 204
        assert len(Task.objects.all()) == 3
        response = self.client.get(reverse("index"))
        assert b"hello" in response.content
        assert b"wrld" in response.content

    def test_new_task_failed(self):
        response = self.client.post(
            reverse("new_task"),
            data={
                "shared_link": "wrongurl",
            },
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 422
        assert len(Task.objects.all()) == 2
        response = self.client.get(reverse("index"))
        assert b"wrongurl" not in response.content
