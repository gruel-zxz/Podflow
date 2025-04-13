# podflow/Netscape/get_cookie_dict.py
# coding: utf-8

from http.cookiejar import LoadError, MozillaCookieJar
from podflow.basic.time_print import time_print


# 将Netscape转Dict模块
def get_cookie_dict(file):
    parts = file.split("/")
    try:
        # 加载Netscape格式的cookie文件
        cookie_jar = MozillaCookieJar(file)
        cookie_jar.load(ignore_discard=True)
        return {cookie.name: cookie.value for cookie in cookie_jar}
    except FileNotFoundError:
        time_print(f"{parts[-1]}文件不存在")
        return None
    except LoadError:
        time_print(f"{parts[-1]}文件错误")
        return None
