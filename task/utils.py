from http.cookies import SimpleCookie


def cookies2dict(cookie_string):
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    return {k: v.value for k, v in cookie.items()}
