import tempfile
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from baidupcs_py.baidupcs import BaiduPCSApi
from baidupcs_py.baidupcs.errors import BaiduPCSError
from baidupcs_py.baidupcs.inner import PcsSharedPath

from task.baidupcs import access_shared
from task.baidupcs import BaiduPCSClient
from task.baidupcs import BaiduPCSErrorCodeCaptchaNeeded
from task.baidupcs import CaptchaRequired
from task.baidupcs import get_baidupcs_client
from task.baidupcs import save_shared


@patch("task.baidupcs.BaiduPCSClient")
@patch("task.baidupcs.settings")
@patch("task.baidupcs.cookies2dict")
def test_get_baidupcs_client(mock_cookies2dict, mock_settings, mock_BaiduPCS):
    mock_settings.PAN_BAIDU_BDUSS = "test_bduss"
    mock_settings.PAN_BAIDU_COOKIES = "test_cookies"
    mock_cookies2dict.return_value = {"test_cookies"}

    get_baidupcs_client()

    mock_BaiduPCS.assert_called_once_with("test_bduss", {"test_cookies"})


class TestBaiduPCS(unittest.TestCase):
    def setUp(self):
        self.bduss = "test_bduss"
        self.cookies = {"BDUSS": "test_cookie"}
        with patch("task.baidupcs.BaiduPCSApi") as mock_api:
            mock_api.return_value.list.return_value = [
                MagicMock(
                    path="/test/file1",
                    is_dir=False,
                    is_file=True,
                    size=1024,
                    md5="123456",
                ),
                MagicMock(
                    path="/test/dir1",
                    is_dir=True,
                    is_file=False,
                    size=0,
                    md5="",
                ),
                MagicMock(
                    path="/test/dir1/file2",
                    is_dir=False,
                    is_file=True,
                    size=2048,
                    md5="789012",
                ),
            ]
            self.client = BaiduPCSClient(self.bduss, self.cookies)
        self.client.api.access_shared = MagicMock()

    def test_list_files(self):
        result = self.client.list_files("/test")

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["path"], "/test/file1")
        self.assertEqual(result[0]["is_dir"], False)
        self.assertEqual(result[0]["is_file"], True)
        self.assertEqual(result[0]["size"], 1024)
        self.assertEqual(result[0]["md5"], "123456")
        self.assertEqual(result[1]["path"], "/test/dir1")
        self.assertEqual(result[1]["is_dir"], True)
        self.assertEqual(result[1]["is_file"], False)
        self.assertEqual(result[1]["size"], 0)
        self.assertEqual(result[1]["md5"], "")
        self.assertEqual(result[2]["path"], "/test/dir1/file2")
        self.assertEqual(result[2]["is_dir"], False)
        self.assertEqual(result[2]["is_file"], True)
        self.assertEqual(result[2]["size"], 2048)
        self.assertEqual(result[2]["md5"], "789012")


class TestSaveShared(unittest.TestCase):
    def setUp(self):
        self.bduss = "test_bduss"
        self.cookies = {"BDUSS": "test_cookie"}
        self.api = MagicMock(spec=BaiduPCSApi)
        self.api._baidupcs = MagicMock()
        self.client = BaiduPCSClient(
            self.bduss,
            self.cookies,
            api=self.api,
        )

    def test_save_shared(self):
        shared_url = "https://pan.baidu.com/s/1test"
        remotedir = "/test_remote_dir"
        password = "pwd"
        self.client.api.shared_paths.return_value = [
            PcsSharedPath(
                fs_id=1,
                path="/sharelink1-2/1",
                size=0,
                is_dir=True,
                is_file=False,
                md5="",
                local_ctime=1678787063,
                local_mtime=1678787063,
                server_ctime=1678787063,
                server_mtime=1678787064,
                uk=123,
                share_id=4,
                bdstoken="ffee",
            ),
            PcsSharedPath(
                fs_id=3,
                path="/leecher/a.wav",
                size=1024,
                is_dir=False,
                is_file=True,
                md5="beef",
                local_ctime=1678787063,
                local_mtime=1678787063,
                server_ctime=1678787063,
                server_mtime=1678787064,
                uk=123,
                share_id=4,
                bdstoken="ffee",
            ),
        ]
        self.client.api.exists.return_value = False
        self.client.api.makedir.return_value = None
        self.client.api.transfer_shared_paths.side_effect = BaiduPCSError(
            "Error message",
            12,
        )
        self.client.api.list_shared_paths.return_value = []

        save_shared(self.client, shared_url, remotedir, password)

        self.client.api.shared_paths.assert_called_with(shared_url)
        self.client.api.exists.assert_called_with(remotedir)
        self.client.api.transfer_shared_paths.assert_called()

    def test_save_shared_expired(self):
        shared_url = "https://pan.baidu.com/s/expired"
        self.client.api.exists.return_value = False
        self.client.api.makedir.return_value = None
        self.client.api.shared_paths.side_effect = BaiduPCSError(
            "error_code: 117, message: {'csrf': '', ... 'expiredType': -1, ... }",
            117,
        )

        with pytest.raises(BaiduPCSError) as exc:
            save_shared(self.client, shared_url, "/dir", "psw")

        assert "error_code: 117" in str(exc)
        assert "message: 该分享已过期" in str(exc)

    def test_token_leaked(self):
        shared_url = "https://pan.baidu.com/s/failed"
        self.client.api.exists.return_value = False
        self.client.api.makedir.return_value = None
        self.client.api.shared_paths.side_effect = BaiduPCSError(
            "error_code: 0, message: {'csrf': '', 'XDUSS': ... }",
            117,
        )

        with pytest.raises(BaiduPCSError) as exc:
            save_shared(self.client, shared_url, "/dir", "psw")

        assert "csrf" not in str(exc)
        assert "XDUSS" not in str(exc)

    def test_need_captcah(self):
        shared_url = "https://pan.baidu.com/s/1test"
        password = "pwd"
        self.client.api._baidupcs.access_shared.side_effect = BaiduPCSError(
            "可能需要输入验证码",
            BaiduPCSErrorCodeCaptchaNeeded,
        )
        self.client.api.getcaptcha.return_value = ("captchaid", "http://c.jpg")
        self.client.api.get_vcode_img.return_value = "binarycontent"
        callback = MagicMock()

        with pytest.raises(CaptchaRequired):
            access_shared(self.client, shared_url, password, callback)

        callback.assert_called_with("captchaid", "http://c.jpg", "binarycontent")


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.bduss = "test_bduss"
        self.cookies = {"BDUSS": "test_cookie"}
        self.api = MagicMock(spec=BaiduPCSApi)
        self.api._baidupcs = MagicMock()
        self.client = BaiduPCSClient(
            self.bduss,
            self.cookies,
            api=self.api,
        )

    @patch(
        "task.baidupcs.BaiduPCSClient.list_files",
        return_value=[
            {
                "path": "dir1",
                "is_dir": True,
                "is_file": False,
                "size": 0,
                "md5": None,
            },
            {
                "path": "dir1/text.txt",
                "is_dir": False,
                "is_file": True,
                "size": 1024,
                "md5": "badbeef",
            },
        ],
    )
    @patch("task.baidupcs.download_url", return_value=100)
    def test_download(self, mock_download, mock_list):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.client.download_dir("/", tmpdir, 100)

        assert mock_download.called
        assert mock_download.call_count == 1
        assert mock_download.call_args.args[0].name == "text.txt"
