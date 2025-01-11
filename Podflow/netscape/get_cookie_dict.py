# Podflow/Netscape/get_cookie_dict.py
# coding: utf-8

from datetime import datetime
from http.cookiejar import LoadError, MozillaCookieJar


# 将Netscape转Dict模块
def get_cookie_dict(file):
    parts = file.split("/")
    try:
        # 加载Netscape格式的cookie文件
        cookie_jar = MozillaCookieJar(file)
        cookie_jar.load(ignore_discard=True)
        return {cookie.name: cookie.value for cookie in cookie_jar}
    except FileNotFoundError:
        print(f"{datetime.now().strftime('%H:%M:%S')}|{parts[-1]}文件不存在")
        return None
    except LoadError:
        print(f"{datetime.now().strftime('%H:%M:%S')}|{parts[-1]}文件错误")
        return None
