from http.cookies import SimpleCookie
from urllib.parse import urlparse, parse_qs


def cookies2dict(cookie_string):
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    return {k: v.value for k, v in cookie.items()}


def get_url_query(url, query_name):
    parsed_url = urlparse(url)
    return parse_qs(parsed_url.query)[query_name][0]
