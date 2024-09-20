import logging
import os
import re
import traceback
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Dict
from typing import Generator
from typing import List
from typing import Tuple
from urllib.parse import parse_qs
from urllib.parse import urlparse

import requests

SHARED_URL_PREFIX = "https://pan.baidu.com/s/"

logger = logging.getLogger(__name__)


def handle_exception(exc: Exception) -> str:
    message = f"{exc}"
    logger.error(message)
    tb = traceback.format_exc()
    logger.error(tb)
    return message


def cookies2dict(cookie_string: str) -> Dict[str, str]:
    """
    >>> cookies2dict('name=xyb; project=leecher')
    {'name': 'xyb', 'project': 'leecher'}
    >>> cookies2dict('')
    {}
    """
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    return {k: v.value for k, v in cookie.items()}


def get_url_query(url: str, query_name: str) -> str:
    """
    >>> get_url_query('http://test.com/?abc=def', 'abc')
    'def'
    >>> get_url_query('http://test.com/?abc=def', 'def')
    """
    parsed_url = urlparse(url)
    qs = parse_qs(parsed_url.query)
    if query_name in qs:
        return qs[query_name][0]


def parse_shared_link(url: str) -> str:
    """
    >>> parse_shared_link('https://pan.baidu.com/s/123abc?pwd=def')
    {'id': '123abc', 'password': 'def'}
    >>> parse_shared_link('https://pan.baidu.com/s/123abc')
    {'id': '123abc', 'password': ''}
    >>> parse_shared_link('https://pan.baidu.com/share/init?surl=_123abc')
    {'id': '1_123abc', 'password': ''}
    >>> parse_shared_link('https://test.com/xyb')
    Traceback (most recent call last):
      ...
    ValueError: The shared url is invalid: https://test.com/xyb
    """

    pwd = get_url_query(url, "pwd") or ""

    # For Standard url
    temp = r"pan\.baidu\.com/s/(.+?)(\?|$)"
    m = re.search(temp, url)
    if m:
        return dict(id=m.group(1), password=pwd)

    # For surl url
    temp = r"baidu\.com.+?\?surl=(.+?)(\?|$)"
    m = re.search(temp, url)
    if m:
        return dict(id="1" + m.group(1), password=pwd)

    raise ValueError(f"The shared url is invalid: {url}")


def unify_shared_link(url: str) -> str:
    result = parse_shared_link(url)
    return SHARED_URL_PREFIX + result["id"]


def download_url(
    local_path: str,
    url: str,
    headers: Dict[str, str],
    limit: int = 0,
) -> int:
    resp = requests.get(url, headers=headers, stream=True)
    total = 0
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=10240):
            if chunk:
                f.write(chunk)
                total += len(chunk)
            if limit > 0 and total >= limit:
                return total
    return total


def match_regex(string: str, regex: str) -> bool:
    """
    Check if a string matches a given regular expression.

    Args:
        string (str): The input string.
        regex (str): The regular expression pattern.

    Returns:
        bool: True if the string matches the regular expression, False otherwise.

    Examples:
        >>> match_regex("hello.txt", ".*txt|.*mp3")
        True
        >>> match_regex("hello.html", ".*txt|.*mp3")
        False
    """
    pattern = re.compile(regex)
    return bool(re.match(pattern, string))


def walk_dir(path: Path) -> Generator[Tuple[Path, List[os.DirEntry]], None, None]:
    """
    Recursively walks through a directory and yields tuples containing
    the current path and a list of directory entries.

    Args:
        path (Path): The path to the directory.

    Returns:
        List[Tuple[Path, List[os.DirEntry]]]: A list of tuples containing
        the current path and a list of directory entries.

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as temp_dir:
        ...     test_dir = Path(temp_dir) / "test_dir"
        ...     test_dir.mkdir()
        ...     file1 = test_dir / "file1.txt"
        ...     file1.touch()
        ...     sub_dir = test_dir / "sub_dir"
        ...     sub_dir.mkdir()
        ...     file2 = sub_dir / "file2.txt"
        ...     file2.touch()
        ...     entries = list(walk_dir(test_dir))
        ...     len(entries)
        2
        >>> entries[0][0] == test_dir
        True
        >>> sorted([i.name for i in entries[0][1]])
        ['file1.txt', 'sub_dir']
        >>> entries[1][0] == sub_dir
        True
        >>> sorted([i.name for i in entries[1][1]])
        ['file2.txt']
    """

    paths = [path]
    while paths:
        path = paths.pop(0)
        with os.scandir(path) as scandir_it:
            entries = list(scandir_it)
        yield path, entries
        for entry in entries:
            if entry.is_dir():
                paths.append(path._make_child_relpath(entry.name))


def walk_files(path: Path) -> Generator[Path, None, None]:
    """
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as temp_dir:
    ...     test_dir = Path(temp_dir) / "test_dir"
    ...     test_dir.mkdir()
    ...     file1 = test_dir / "file1.txt"
    ...     file1.touch()
    ...     sub_dir = test_dir / "sub_dir"
    ...     sub_dir.mkdir()
    ...     file2 = sub_dir / "file2.txt"
    ...     file2.touch()
    ...     files = list(walk_files(test_dir))
    ...     len(files)
    2
    >>> [i.name for i in files]
    ['file1.txt', 'file2.txt']
    """
    for root, entries in walk_dir(path):
        for p in entries:
            if not p.is_dir():
                yield root / p


def list_files(root: Path, without_root=True) -> List[str]:
    """
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as temp_dir:
    ...     test_dir = Path(temp_dir) / "test_dir"
    ...     test_dir.mkdir()
    ...     file1 = test_dir / "file1.txt"
    ...     file1.touch()
    ...     sub_dir = test_dir / "sub_dir"
    ...     sub_dir.mkdir()
    ...     file2 = sub_dir / "file2.txt"
    ...     file2.touch()
    ...     files = list_files(test_dir)
    ...     len(files)
    2
    >>> files
    ['file1.txt', 'sub_dir/file2.txt']
    """
    result = []
    for file_path in walk_files(root):
        if without_root:
            result.append(str(file_path.relative_to(root)))
        else:
            result.append(str(file_path))
    return result
