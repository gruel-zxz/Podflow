# podflow/youtube/login.py
# coding: utf-8


from http.cookiejar import LoadError, MozillaCookieJar
from podflow.basic.write_log import write_log
from podflow.basic.time_print import time_print
from podflow.basic.http_client import http_client


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


def get_youtube_cookie_fail(arg0):
    time_print(arg0)
    write_log("YouTube \033[31m获取cookie失败\033[0m")
    return None


# 获取YouTube cookie模块
def get_youtube_cookie(channelid_youtube_ids):
    if not channelid_youtube_ids:
        return
    youtube_cookie = get_cookie_dict("channel_data/yt_dlp_youtube.txt")
    if youtube_cookie is None:
        write_log("YouTube \033[31m获取cookie失败\033[0m")
        return None
    if response := http_client(
        "https://www.youtube.com", "YouTube主页", 10, 4, True, youtube_cookie
    ):
        html_content = response.text
        if '"LOGGED_IN":true' in html_content:
            updata_data = update_netscape(
                response.cookies,
                "channel_data/yt_dlp_youtube.txt",
            )
            if updata_data:
                time_print("YouTube \033[32m获取cookie成功\033[0m")
            else:
                return get_youtube_cookie_fail("更新YouTube cookie失败")
            new_youtube_cookie = response.cookies.get_dict()
            for my_cookie_name, my_cookie_value in new_youtube_cookie.items():
                youtube_cookie[my_cookie_name] = my_cookie_value
            return youtube_cookie
        elif '"LOGGED_IN":false' in html_content:
            return get_youtube_cookie_fail("登陆YouTube失败")
        else:
            return get_youtube_cookie_fail("登陆YouTube无法判断")
    else:
        write_log("YouTube \033[31m获取cookie失败\033[0m")
        return None
