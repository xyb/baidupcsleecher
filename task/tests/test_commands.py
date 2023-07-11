from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from task.management.commands.runresume import Command as ResumeCommand
from task.models import Task


class ResumeCommandTest(TestCase):
    def setUp(self):
        self.task = Task.objects.create(shared_id="foo", shared_password="foo")
        self.task.status = Task.Status.SAMPLING_DOWNLOADED
        self.task.started_at = self.task.created_at
        self.task.transfer_completed_at = self.task.created_at
        self.task.sample_downloaded_at = self.task.created_at
        self.task.failed = True
        self.task.message = "BaiduPCS._request"
        self.task.save()

    def test_resume(self):
        assert self.task.retry_times == 0

        ResumeCommand().resume_once()

        task = Task.objects.get(pk=self.task.id)
        assert task.status == Task.Status.TRANSFERRED
        assert not task.failed
        assert task.retry_times == 1

    def test_resume_not_recoverable_task(self):
        self.task.message = "error_code: 105,"
        self.task.save()
        assert self.task.retry_times == 0

        ResumeCommand().resume_once()

        task = Task.objects.get(pk=self.task.id)
        assert task.retry_times == 0
        assert task.failed
        assert task.status == Task.Status.SAMPLING_DOWNLOADED

    def test_resume_too_many_times(self):
        self.task.retry_times = settings.RETRY_TIMES_LIMIT + 1
        self.task.save()
        assert self.task.retry_times == settings.RETRY_TIMES_LIMIT + 1
        assert self.task.get_resume_method_name() == "restart_downloading"

        ResumeCommand().resume_once()

        task = Task.objects.get(pk=self.task.id)
        assert task.retry_times == settings.RETRY_TIMES_LIMIT + 1
        assert task.get_resume_method_name() == "restart_downloading"
        assert task.failed
        assert task.status == Task.Status.SAMPLING_DOWNLOADED

    def test_run_command(self):
        assert self.task.retry_times == 0

        call_command("runresume", "--once")

        task = Task.objects.get(pk=self.task.id)
        assert task.status == Task.Status.TRANSFERRED
        assert not task.failed
        assert task.retry_times == 1
