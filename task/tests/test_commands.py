from unittest import mock

from baidupcs_py.baidupcs import api
from baidupcs_py.baidupcs import BaiduPCSApi
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from django.test import TestCase
from requests import Session

from task.management.commands.runresume import Command as ResumeCommand
from task.models import Task


def mocked_requests(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    print(f"--> requests: {args}, {kwargs}")
    if args[0] == "http://tieba.baidu.com/c/s/login":
        return MockResponse(
            {
                "user": {
                    "id": "265",
                    "name": "xyb",
                    "BDUSS": "foo",
                    "portrait": "",
                },
                "error_code": "0",
            },
            200,
        )

    return MockResponse(None, 404)


class TransferCommandTest(TestCase):
    def setUp(self):
        self.task = Task.objects.create(shared_id="foo", shared_password="foo")

    @mock.patch("task.baidupcs.save_shared", return_value=None)
    @mock.patch.object(api.BaiduPCS, "access_shared", return_value={})
    @mock.patch.object(BaiduPCSApi, "list", return_value={})
    @mock.patch(
        "task.utils.parse_shared_link",
        return_value={"id": "foo", "password": "foo"},
    )
    @mock.patch.object(Session, "request", side_effect=mocked_requests)
    @mock.patch("requests.get", side_effect=mocked_requests)
    @mock.patch("requests.post", side_effect=mocked_requests)
    @override_settings(PAN_BAIDU_BDUSS="xyb")
    @override_settings(PAN_BAIDU_COOKIES="BAIDUID=x; BDUSS=y; STOKEN=b")
    def test_transfer(
        self,
        mock_post,
        mock_get,
        mock_sget,
        mock_parse,
        mock_list,
        mock_access,
        mock_save,
    ):
        print(settings.PAN_BAIDU_COOKIES)
        call_command("runtransfer", "--once")

        task = Task.objects.get(pk=self.task.id)
        assert task.status == Task.Status.TRANSFERRED


class SamplingDownloaderCommandTest(TestCase):
    def setUp(self):
        self.task = Task.objects.create(shared_id="foo", shared_password="foo")
        self.task.status = Task.Status.TRANSFERRED
        self.task.started_at = self.task.created_at
        self.task.transfer_completed_at = self.task.created_at
        self.task.save()

    @mock.patch("task.baidupcs.save_shared", return_value=None)
    @mock.patch.object(api.BaiduPCS, "access_shared", return_value={})
    @mock.patch.object(BaiduPCSApi, "list", return_value={})
    @mock.patch(
        "task.utils.parse_shared_link",
        return_value={"id": "foo", "password": "foo"},
    )
    @mock.patch.object(Session, "request", side_effect=mocked_requests)
    @mock.patch("requests.get", side_effect=mocked_requests)
    @mock.patch("requests.post", side_effect=mocked_requests)
    @override_settings(PAN_BAIDU_BDUSS="xyb")
    @override_settings(PAN_BAIDU_COOKIES="BAIDUID=x; BDUSS=y; STOKEN=b")
    def test_downloader(
        self,
        mock_post,
        mock_get,
        mock_sget,
        mock_parse,
        mock_list,
        mock_access,
        mock_save,
    ):
        call_command("runsamplingdownloader", "--once")

        task = Task.objects.get(pk=self.task.id)
        assert task.status == Task.Status.SAMPLING_DOWNLOADED


class LeecherCommandTest(TestCase):
    def setUp(self):
        self.task = Task.objects.create(shared_id="foo", shared_password="foo")
        self.task.status = Task.Status.SAMPLING_DOWNLOADED
        self.task.started_at = self.task.created_at
        self.task.transfer_completed_at = self.task.created_at
        self.task.sample_downloaded_at = self.task.created_at
        self.task.full_download_now = True
        self.task.save()

    @mock.patch("task.baidupcs.save_shared", return_value=None)
    @mock.patch.object(api.BaiduPCS, "access_shared", return_value={})
    @mock.patch.object(BaiduPCSApi, "list", return_value={})
    @mock.patch(
        "task.utils.parse_shared_link",
        return_value={"id": "foo", "password": "foo"},
    )
    @mock.patch.object(Session, "request", side_effect=mocked_requests)
    @mock.patch("requests.get", side_effect=mocked_requests)
    @mock.patch("requests.post", side_effect=mocked_requests)
    @override_settings(PAN_BAIDU_BDUSS="xyb")
    @override_settings(PAN_BAIDU_COOKIES="BAIDUID=x; BDUSS=y; STOKEN=b")
    def test_leecher(
        self,
        mock_post,
        mock_get,
        mock_sget,
        mock_parse,
        mock_list,
        mock_access,
        mock_save,
    ):
        call_command("runleecher", "--once")

        task = Task.objects.get(pk=self.task.id)
        assert task.status == Task.Status.FINISHED


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
