import logging
from collections import deque
from os import makedirs
from os.path import basename
from os.path import getsize
from pathlib import Path
from pathlib import PurePosixPath
from time import sleep

import requests
from baidupcs_py.baidupcs import BaiduPCSApi
from baidupcs_py.baidupcs import BaiduPCSError
from baidupcs_py.baidupcs import PCS_UA
from django.conf import settings

from .utils import cookies2dict
from .utils import unify_shared_link

logger = logging.getLogger("baibupcs")


class CaptchaRequired(ValueError):
    pass


def get_baidupcs_client():
    return BaiduPCS(
        settings.PAN_BAIDU_BDUSS,
        cookies2dict(settings.PAN_BAIDU_COOKIES),
    )


class BaiduPCS:
    def __init__(self, bduss, cookies, api=None):
        self.bduss = bduss
        self.cookies = cookies
        self.api = api if api else BaiduPCSApi(bduss=bduss, cookies=cookies)

    def list_files(self, remote_dir, retry=3, fail_silent=False):
        while True:
            try:
                files = self.api.list(remote_dir, recursive=True)
                break
            except BaiduPCSError as err:
                if err.error_code == 31066 and retry > 0:
                    logging.error(f"list {remote_dir} failed, retry {retry}: {err}")
                    retry -= 1
                    sleep(0.5)
                    continue
                if fail_silent:
                    return []
                raise err

        result = []
        for file in files:
            result.append(
                dict(
                    path=file.path,
                    is_dir=file.is_dir,
                    is_file=file.is_file,
                    size=file.size,
                    md5=file.md5,
                    # ctime=file.ctime,
                    # mtime=file.mtime,
                ),
            )
        return result

    def save_shared_link(
        self,
        remote_dir,
        link,
        password=None,
        callback_save_captcha=None,
        captcha_id: str = "",
        captcha_code: str = "",
    ):
        save_shared(
            self,
            link,
            remote_dir,
            password=password,
            callback_save_captcha=callback_save_captcha,
            captcha_id=captcha_id,
            captcha_code=captcha_code,
        )

    def download_dir(self, remote_dir, local_dir, sample_size=0):
        for file in self.list_files(remote_dir):
            if not file["is_file"]:
                continue
            remote_path = str(Path(remote_dir) / file["path"])
            source_sub_path = remote_path[len(remote_dir) + 1 :]
            local_dir_ = (Path(local_dir) / source_sub_path).parent
            file_size = file["size"]
            self.download_file(remote_path, local_dir_, file_size, sample_size)

    def download_file(self, remote_path, local_dir, file_size, sample_size=0):
        local_path = Path(local_dir) / basename(remote_path)
        logger.info(f"  {remote_path} -> {local_path}")

        if not local_path.parent.exists():
            local_path.parent.mkdir(parents=True)

        if local_path.exists():
            if (sample_size and sample_size == getsize(local_path)) or (
                not sample_size and file_size == getsize(local_path)
            ):
                logger.info(f"{local_path} is ready existed.")
                return

        url = self.api.download_link(remote_path)
        if not url:
            logger.info(remote_path)
            return

        headers = {
            "Cookie": f"BDUSS={self.cookies['BDUSS']};",
            "User-Agent": PCS_UA,
            # TODO 'Range': 'bytes=%d-' % resume_byte_pos,
        }

        resp = requests.get(url, headers=headers, stream=True)
        total = 0
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=10240):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
                if sample_size > 0 and total >= sample_size:
                    return total
        return total

    def leech(self, remote_dir, local_dir, sample_size=0):
        if not local_dir.exists():
            makedirs(local_dir, exist_ok=True)

        self.download_dir(remote_dir, local_dir, sample_size=sample_size)


def remotepath_exists(api, name: str, rd: str, _cache={}) -> bool:
    names = _cache.get(rd)
    if not names:
        names = {PurePosixPath(sp.path).name for sp in api.list(rd)}
        _cache[rd] = names
    return name in names


def save_shared(
    pcs,
    shared_url,
    remotedir,
    password=None,
    callback_save_captcha=None,
    captcha_id: str = "",
    captcha_code: str = "",
):
    assert remotedir.startswith("/"), "`remotedir` must be an absolute path"

    shared_url = unify_shared_link(shared_url)

    if password:
        access_shared(
            pcs,
            shared_url,
            password,
            callback_save_captcha,
            captcha_id,
            captcha_code,
        )

    shared_paths = deque(pcs.api.shared_paths(shared_url))

    # Record the remotedir of each shared_path
    _remotedirs = {}
    for sp in shared_paths:
        _remotedirs[sp] = remotedir

    _dir_exists = set()

    while shared_paths:
        shared_path = shared_paths.popleft()
        rd = _remotedirs[shared_path]

        # Make sure remote dir exists
        if rd not in _dir_exists:
            if not pcs.api.exists(rd):
                pcs.api.makedir(rd)
            _dir_exists.add(rd)

        # Ignore existed file
        if shared_path.is_file and remotepath_exists(
            pcs.api,
            PurePosixPath(shared_path.path).name,
            rd,
        ):
            logger.warning(f"WARNING: {shared_path.path} has be in {rd}")
            continue
        uk, share_id, bdstoken = (
            shared_path.uk,
            shared_path.share_id,
            shared_path.bdstoken,
        )
        assert uk
        assert share_id
        assert bdstoken

        try:
            pcs.api.transfer_shared_paths(
                rd,
                [shared_path.fs_id],
                uk,
                share_id,
                bdstoken,
                shared_url,
            )
            logger.info(f"save: {shared_path.path} to {rd}")
            continue
        except BaiduPCSError as err:
            if err.error_code == 12:  # 12: "文件已经存在"
                logger.warning(
                    f"WARNING: error_code: {err.error_code}, "
                    "{shared_path.path} has be in {rd}",
                )
            elif err.error_code == -32:  # -32: "剩余空间不足，无法转存",
                raise err
            elif err.error_code in (
                -33,  # -33: "一次支持操作999个，减点试试吧"
                4,  # 4: "share transfer pcs error"
                130,  # "转存文件数超限"
            ):
                logger.warning(
                    f"WARNING: error_code: {err.error_code},"
                    " {shared_path.path} "
                    "has more items and need to transfer one by one",
                )
            else:
                raise err

        if shared_path.is_dir:
            # Take all sub paths
            sub_paths = list_all_sub_paths(
                pcs.api,
                shared_path.path,
                uk,
                share_id,
                bdstoken,
            )
            rd = (Path(rd) / basename(shared_path.path)).as_posix()
            for sp in sub_paths:
                _remotedirs[sp] = rd
            shared_paths.extendleft(sub_paths[::-1])


def list_all_sub_paths(
    api,
    sharedpath: str,
    uk: int,
    share_id: int,
    bdstoken: str,
):
    sub_paths = []
    page = 1
    size = 100
    while True:
        sps = api.list_shared_paths(
            sharedpath,
            uk,
            share_id,
            bdstoken,
            page=page,
            size=size,
        )
        sub_paths += sps
        if len(sps) < 100:
            break
        page += 1
    return sub_paths


def access_shared(
    pcs,
    shared_url: str,
    password: str,
    callback_save_captcha=None,
    captcha_id: str = "",
    captcha_code: str = "",
):
    try:
        pcs.api._baidupcs.access_shared(shared_url, password, captcha_id, captcha_code)
    except BaiduPCSError as err:
        if err.error_code not in (-9, -62):
            raise err
        if err.error_code == -62:  # -62: '可能需要输入验证码'
            logger.warning("captcha needed!")
        if err.error_code == -9:
            logger.error("captcha is incorrect!")

        captcha_id, captcha_img_url = pcs.api.getcaptcha(shared_url)
        logger.debug(f"captcha: {captcha_id}, url {captcha_img_url}")
        content = pcs.api.get_vcode_img(captcha_img_url, shared_url)
        callback_save_captcha(captcha_id, captcha_img_url, content)
        raise CaptchaRequired()
