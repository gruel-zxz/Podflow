# Podflow/youtube_login.py
# coding: utf-8

from Podflow import gVar
from datetime import datetime
from Podflow.Netscape import get_cookie_dict
from Podflow.basis import write_log, http_client

# 获取YouTube cookie模块
def get_youtube_cookie():
    youtube_cookie = get_cookie_dict("channel_data/yt_dlp_youtube.txt")
    if gVar.channelid_youtube_ids:
        if youtube_cookie is None:
            write_log("YouTube \033[31m获取cookie失败\033[0m")
            return None
        if response := http_client("https://www.youtube.com", "YouTube主页", 10, 4, True, youtube_cookie):
            html_content = response.text
            if "\"LOGGED_IN\":true" in html_content:
                print(f"{datetime.now().strftime('%H:%M:%S')}|YouTube \033[32m获取cookie成功\033[0m")
                return youtube_cookie
            elif "\"LOGGED_IN\":false" in html_content:
                print(f"{datetime.now().strftime('%H:%M:%S')}|登陆YouTube失败")
                write_log("YouTube \033[31m获取cookie失败\033[0m")
                return None
            else:
                print(f"{datetime.now().strftime('%H:%M:%S')}|登陆YouTube无法判断")
                write_log("YouTube \033[31m获取cookie失败\033[0m")
                return None
        else:
            write_log("YouTube \033[31m获取cookie失败\033[0m")
            return None