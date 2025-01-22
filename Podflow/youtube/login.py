# Podflow/youtube/login.py
# coding: utf-8

from datetime import datetime
from Podflow.basic.http_client import http_client
from Podflow.basic.write_log import write_log
from Podflow.netscape.get_cookie_dict import get_cookie_dict


def get_youtube_cookie_fail(arg0):
    print(f"{datetime.now().strftime('%H:%M:%S')}{arg0}")
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
            print(
                f"{datetime.now().strftime('%H:%M:%S')}|YouTube \033[32m获取cookie成功\033[0m"
            )
            return youtube_cookie
        elif '"LOGGED_IN":false' in html_content:
            return get_youtube_cookie_fail("|登陆YouTube失败")
        else:
            return get_youtube_cookie_fail("|登陆YouTube无法判断")
    else:
        write_log("YouTube \033[31m获取cookie失败\033[0m")
        return None
