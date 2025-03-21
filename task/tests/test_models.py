from django.test import TestCase

from ..models import Task


class TaskTestCase(TestCase):
    def setUp(self):
        self.task = Task.objects.create(shared_id="foo", shared_password="foo")

    def test_stages1(self):
        self.task.status = self.task.Status.INITED

        assert list(self.task.get_stages()) == [
            ("waiting_assign", "doing"),
            ("transferring", "todo"),
            ("downloading_samplings", "todo"),
            ("waiting_permit_download", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_stage() == "waiting_assign"
        assert not self.task.done

    def test_stages2(self):
        self.task.status = self.task.Status.STARTED

        assert list(self.task.get_stages()) == [
            ("waiting_assign", "done"),
            ("transferring", "doing"),
            ("downloading_samplings", "todo"),
            ("waiting_permit_download", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_stage() == "transferring"
        assert not self.task.done

    def test_stages3(self):
        self.task.status = self.task.Status.TRANSFERRED

        assert list(self.task.get_stages()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "doing"),
            ("waiting_permit_download", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_stage() == "downloading_samplings"
        assert not self.task.done

    def test_stages4(self):
        self.task.status = self.task.Status.SAMPLING_DOWNLOADED
        self.task.full_download_now = True
        assert list(self.task.get_stages()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "done"),
            ("waiting_permit_download", "done"),
            ("downloading_files", "doing"),
        ]
        assert self.task.get_current_stage() == "downloading_files"
        assert not self.task.done

    def test_stages5(self):
        self.task.status = self.task.Status.FINISHED
        self.task.full_downloaded_at = self.task.created_at
        self.task.full_download_now = True

        assert list(self.task.get_stages()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "done"),
            ("waiting_permit_download", "done"),
            ("downloading_files", "done"),
        ]
        assert self.task.get_current_stage() is None
        assert self.task.done

    def test_done(self):
        self.task.full_downloaded_at = self.task.created_at

        assert not self.task.done

        self.task.status = self.task.Status.FINISHED

        assert self.task.done

    def test_stages1_failed(self):
        self.task.status = self.task.Status.INITED
        self.task.failed = True

        assert list(self.task.get_stages()) == [
            ("waiting_assign", "failed"),
            ("transferring", "todo"),
            ("downloading_samplings", "todo"),
            ("waiting_permit_download", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_stage() == "waiting_assign"
        assert not self.task.done
        assert self.task.get_resume_method_name() == "restart"

    def test_stages2_failed(self):
        self.task.status = self.task.Status.STARTED
        self.task.started_at = self.task.created_at
        self.task.failed = True

        assert list(self.task.get_stages()) == [
            ("waiting_assign", "done"),
            ("transferring", "failed"),
            ("downloading_samplings", "todo"),
            ("waiting_permit_download", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_stage() == "transferring"
        assert not self.task.done
        assert self.task.get_resume_method_name() == "restart"

    def test_stages3_failed(self):
        self.task.status = self.task.Status.TRANSFERRED
        self.task.started_at = self.task.created_at
        self.task.transfer_completed_at = self.task.created_at
        self.task.failed = True

        assert list(self.task.get_stages()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "failed"),
            ("waiting_permit_download", "todo"),
            ("downloading_files", "todo"),
        ]
        assert self.task.get_current_stage() == "downloading_samplings"
        assert not self.task.done
        assert self.task.get_resume_method_name() == "restart_downloading"

    def test_stages4_failed(self):
        self.task.status = self.task.Status.SAMPLING_DOWNLOADED
        self.task.started_at = self.task.created_at
        self.task.transfer_completed_at = self.task.created_at
        self.task.sample_downloaded_at = self.task.created_at
        self.task.full_download_now = True
        self.task.failed = True

        assert list(self.task.get_stages()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "done"),
            ("waiting_permit_download", "done"),
            ("downloading_files", "failed"),
        ]
        assert self.task.get_current_stage() == "downloading_files"
        assert not self.task.done
        assert self.task.get_resume_method_name() == "restart_downloading"

    def test_stages5_failed_but_yes_it_should_not_happend(self):
        self.task.status = self.task.Status.SAMPLING_DOWNLOADED
        self.task.started_at = self.task.created_at
        self.task.transfer_completed_at = self.task.created_at
        self.task.sample_downloaded_at = self.task.created_at
        self.task.full_downloaded_at = self.task.created_at
        self.task.full_download_now = True
        self.task.failed = True

        assert list(self.task.get_stages()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "done"),
            ("waiting_permit_download", "done"),
            ("downloading_files", "done"),
        ]
        assert self.task.get_current_stage() is None
        assert not self.task.done
        assert self.task.get_resume_method_name() is None

    def test_filter_failed_but_nothing(self):
        assert list(Task.filter_failed()) == []

    def test_filter_failed(self):
        self.task.failed = True
        self.task.save()

        assert list(Task.filter_failed()) == [self.task]

    def test_resume_failed_transfer(self):
        task = self.task
        task.status = task.Status.STARTED
        task.started_at = task.created_at
        task.failed = True
        task.save()

        Task.schedule_resume_failed()

        task = Task.objects.get(pk=task.id)
        assert list(task.get_stages()) == [
            ("waiting_assign", "doing"),
            ("transferring", "todo"),
            ("downloading_samplings", "todo"),
            ("waiting_permit_download", "todo"),
            ("downloading_files", "todo"),
        ]

    def test_resume_failed_download(self):
        task = self.task
        task.status = task.Status.TRANSFERRED
        task.started_at = task.created_at
        task.transfer_completed_at = task.created_at
        task.failed = True
        task.save()

        Task.schedule_resume_failed()

        task = Task.objects.get(pk=task.id)
        assert list(task.get_stages()) == [
            ("waiting_assign", "done"),
            ("transferring", "done"),
            ("downloading_samplings", "doing"),
            ("waiting_permit_download", "todo"),
            ("downloading_files", "todo"),
        ]

    def test_recoverable(self):
        assert not self.task.recoverable

        self.task.failed = True
        self.task.message = "BaiduPCS._request"
        assert self.task.recoverable

        self.task.message = "error_code: 105,"
        assert not self.task.recoverable

        self.task.message = "unknown error"
        assert not self.task.recoverable
