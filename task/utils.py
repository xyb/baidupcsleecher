import logging
import re
import traceback
from http.cookies import SimpleCookie
from urllib.parse import parse_qs
from urllib.parse import urlparse

import requests

SHARED_URL_PREFIX = "https://pan.baidu.com/s/"

logger = logging.getLogger(__name__)


def handle_exception(task, exc):
    message = f"{exc}"
    logger.error(message)
    tb = traceback.format_exc()
    logger.error(tb)
    return message


def cookies2dict(cookie_string):
    """
    >>> cookies2dict('name=xyb; project=leecher')
    {'name': 'xyb', 'project': 'leecher'}
    >>> cookies2dict('')
    {}
    """
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    return {k: v.value for k, v in cookie.items()}


def get_url_query(url, query_name):
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
    ValueError: The shared url is not a valid url. https://test.com/xyb
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

    raise ValueError(f"The shared url is not a valid url. {url}")


def unify_shared_link(url):
    result = parse_shared_link(url)
    return SHARED_URL_PREFIX + result["id"]


def download_url(local_path, url, headers, limit=0):
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
