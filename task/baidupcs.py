from os import makedirs
import re
from collections import deque
from pathlib import Path, PurePosixPath


SHARED_URL_PREFIX = "https://pan.baidu.com/s/"


class BaiduPCS:
    def __init__(self, bduss, cookies):
        self.bduss = bduss
        self.cookies = cookies
        self.api = None

    def list_shared_link_files(self, link, password=""):
        pass

    def save_shared_link(self, remote_dir, link, password=None):
        save_shared(self.api, link, remote_dir, password=password)

    def download_dir(self, remote_dir, local_dir, sample_size=0):
        pass

    def download_file(self, path):
        pass

    def leech(self, remote_dir, local_dir, sample_size=0):
        if not store_path.exists():
            makedirs(store_path, exists_ok=True)

        self.download_dir(remote_dir, local_dir, sample_size=head_size)


def _unify_shared_url(url: str) -> str:
    """Unify input shared url"""

    # For Standard url
    temp = r"pan\.baidu\.com/s/(.+?)(\?|$)"
    m = re.search(temp, url)
    if m:
        return SHARED_URL_PREFIX + m.group(1)

    # For surl url
    temp = r"baidu\.com.+?\?surl=(.+?)(\?|$)"
    m = re.search(temp, url)
    if m:
        return SHARED_URL_PREFIX + "1" + m.group(1)

    raise ValueError(f"The shared url is not a valid url. {url}")

def remotepath_exists(
    api: BaiduPCSApi, name: str, rd: str, _cache={}
) -> bool:
    names = _cache.get(rd)
    if not names:
        names = set([PurePosixPath(sp.path).name for sp in api.list(rd)])
        _cache[rd] = names
    return name in names

def save_shared(
    api,
    shared_url,
    remotedir,
    password=None,
    show_vcode=False,
):
    assert remotedir.startswith("/"), "`remotedir` must be an absolute path"

    shared_url = _unify_shared_url(shared_url)

    # Vertify with password
    if password:
        api.access_shared(shared_url, password, show_vcode=show_vcode)

    shared_paths = deque(api.shared_paths(shared_url))

    # Record the remotedir of each shared_path
    _remotedirs = {}
    for sp in shared_paths:
        _remotedirs[sp] = remotedir

    _dir_exists: Set[str] = set()

    while shared_paths:
        shared_path = shared_paths.popleft()
        rd = _remotedirs[shared_path]

        # Make sure remote dir exists
        if rd not in _dir_exists:
            if not api.exists(rd):
                api.makedir(rd)
            _dir_exists.add(rd)

        # Ignore existed file
        if shared_path.is_file and remotepath_exists(
            api, PurePosixPath(shared_path.path).name, rd
        ):
            print(f"[yellow]WARNING[/]: {shared_path.path} has be in {rd}")
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
            api.transfer_shared_paths(
                rd, [shared_path.fs_id], uk, share_id, bdstoken, shared_url
            )
            print(f"save: {shared_path.path} to {rd}")
            continue
        except BaiduPCSError as err:
            if err.error_code == 12:  # 12: "文件已经存在"
                print(
                    f"[yellow]WARNING[/]: error_code: {err.error_code}, {shared_path.path} has be in {rd}"
                )
            elif err.error_code == -32:  # -32: "剩余空间不足，无法转存",
                raise err
            elif err.error_code in (
                -33,  # -33: "一次支持操作999个，减点试试吧"
                4,  # 4: "share transfer pcs error"
                130,  # "转存文件数超限"
            ):
                print(
                    f"[yellow]WARNING[/]: error_code: {err.error_code}, {shared_path.path} "
                    "has more items and need to transfer one by one"
                )
            else:
                raise err

        if shared_path.is_dir:
            # Take all sub paths
            sub_paths = list_all_sub_paths(
                api, shared_path.path, uk, share_id, bdstoken
            )
            rd = (Path(rd) / os.path.basename(shared_path.path)).as_posix()
            for sp in sub_paths:
                _remotedirs[sp] = rd
            shared_paths.extendleft(sub_paths[::-1])
