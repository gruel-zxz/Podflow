# podflow/netscape/update_netscape.py
# coding: utf-8

from http.cookiejar import MozillaCookieJar


# 更新Netscape_HTTP_Cookie模块
def update_netscape(response_cookies, file: str):
    netscape_cookie_jar = MozillaCookieJar(file)
    try:
        netscape_cookie_jar.load(ignore_discard=True, ignore_expires=True)
    except Exception:
        return False
    for cookie in response_cookies:
        netscape_cookie_jar.set_cookie(cookie)
    try:
        netscape_cookie_jar.save(ignore_discard=True, ignore_expires=True)
        return True
    except Exception:
        return False
