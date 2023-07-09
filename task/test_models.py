from django.test import TestCase

from .models import Task


class TaskTestCase(TestCase):
    def setUp(self):
        self.task = Task.objects.create(shared_id="foo", shared_password="foo")

    def test_steps1(self):
        self.task.status = self.task.Status.INITED

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "doing"),
            ("transferring", "todo"),
            ("downloading_samplings", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_step() == "waiting_assign"

    def test_steps2(self):
        self.task.status = self.task.Status.STARTED

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "done"),
            ("transferring", "doing"),
            ("downloading_samplings", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_step() == "transferring"

    def test_steps3(self):
        self.task.status = self.task.Status.TRANSFERRED

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "doing"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_step() == "downloading_samplings"

    def test_steps4(self):
        self.task.status = self.task.Status.SAMPLING_DOWNLOADED

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "done"),
            ("downloading_files", "doing"),
        ]
        assert self.task.get_current_step() == "downloading_files"

    def test_steps5(self):
        self.task.status = self.task.Status.FINISHED

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "done"),
            ("downloading_files", "done"),
        ]
        assert self.task.get_current_step() is None

    def test_steps1_failed(self):
        self.task.status = self.task.Status.INITED
        self.task.failed = True

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "failed"),
            ("transferring", "todo"),
            ("downloading_samplings", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_step() == "waiting_assign"

    def test_steps2_failed(self):
        self.task.status = self.task.Status.STARTED
        self.task.started_at = self.task.created_at
        self.task.failed = True

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "done"),
            ("transferring", "failed"),
            ("downloading_samplings", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_step() == "transferring"

    def test_steps3_failed(self):
        self.task.status = self.task.Status.TRANSFERRED
        self.task.started_at = self.task.created_at
        self.task.transfer_completed_at = self.task.created_at
        self.task.failed = True

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "failed"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_step() == "downloading_samplings"

    def test_steps1_failed(self):
        self.task.status = self.task.Status.INITED
        self.task.failed = True

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "failed"),
            ("transferring", "todo"),
            ("downloading_samplings", "todo"),
            ("downloading_files", "todo"),
        ]

    def test_steps4_failed(self):
        self.task.status = self.task.Status.TRANSFERRED
        self.task.started_at = self.task.created_at
        self.task.transfer_completed_at = self.task.created_at
        self.task.sample_downloaded_at = self.task.created_at
        self.task.failed = True

        assert list(self.task.get_steps()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "done"),
            ("downloading_files", "failed"),
        ]
        assert self.task.get_current_step() == "downloading_files"
