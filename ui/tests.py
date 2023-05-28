from django.test import Client
from django.test import TestCase
from django.urls import reverse


class TaskUITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        url = reverse("task-list")
        data = {
            "shared_link": "https://pan.baidu.com/s/badbeef?pwd=bee",
        }
        self.client.post(url, data, format="json")

    def test_task_list(self):
        url = reverse("index")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"badbeef" in response.content)
        self.assertTrue(b"bee" in response.content)
