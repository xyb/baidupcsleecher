import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from task.baidupcs import BaiduPCS
from task.baidupcs import get_baidupcs_client


@patch("task.baidupcs.BaiduPCS")
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
            self.pcs = BaiduPCS(self.bduss, self.cookies)
        self.pcs.api.access_shared = MagicMock()

    def test_list_files(self):
        result = self.pcs.list_files("/test")

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


class TestSaveSharedLink(unittest.TestCase):
    def test_save_shared_link(self):
        self.bduss = "test_bduss"
        self.cookies = {"BDUSS": "test_cookie"}
        with patch("task.baidupcs.BaiduPCSApi") as mock_api:
            mock_api.return_value.access_shared.return_value = None
            self.pcs = BaiduPCS(self.bduss, self.cookies)
            remote_dir = "/test"
            link = "https://pan.baidu.com/s/1dFf3XJf"
            password = "123456"
            callback_save_captcha = MagicMock()
            captcha_id = "captcha_id"
            captcha_code = "captcha_code"

            self.pcs.save_shared_link(
                remote_dir,
                link,
                password=password,
                callback_save_captcha=callback_save_captcha,
                captcha_id=captcha_id,
                captcha_code=captcha_code,
            )


if __name__ == "__main__":
    unittest.main()
