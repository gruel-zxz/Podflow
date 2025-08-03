# podflow/youtube/__init__.py
# coding: utf-8

import os
import yt_dlp
from podflow.basic.write_log import write_log
from podflow.basic.time_print import time_print
from podflow.message.fail_message_initialize import fail_message_initialize


# yt-dlp校验cookie模块
def yt_dlp_check(file, url):
    parts = file.split("/")
    if not os.path.exists(file):
        time_print(f"{parts[-1]}文件不存在")
        return False

    class MyLogger:
        def debug(self, msg):
            pass
        def warning(self, msg):
            pass
        def info(self, msg):
            pass
        def error(self, msg):
            pass

    ydl_opts = {
        "cookiefile": file,
        "quiet": True,
        "no_warnings": True,
        "flat_playlist": True,
        "extract_flat": True,
        "logger": MyLogger(),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
        playlist_id = info_dict.get("id", "")
        if playlist_id == "WL":
            return True
        else:
            time_print("cookie校验返回异常")
            return False
    except yt_dlp.utils.DownloadError as e:
        error_message = str(e).lower()
        e = fail_message_initialize(e, "WL")
        if any(
            keyword in error_message
            for keyword in ["login required", "sign in", "private", "forbidden"]
        ):
            time_print(f"cookie无效或已过期\n{e}")
        else:
            time_print(f"cookie无效或网络异常\n{e}")
        return False
    except Exception as e:
        e = fail_message_initialize(e, "WL")
        time_print(f"cookie发生未知错误\n{e}")
        return False


# 校验YouTube cookie模块
def check_youtube_cookie(channelid_youtube_ids):
    if not channelid_youtube_ids:
        return False
    youtube_cookie = yt_dlp_check(
        "channel_data/yt_dlp_youtube.txt",
        "https://www.youtube.com/playlist?list=WL",
    )
    if youtube_cookie:
        time_print("YouTube \033[32m校验cookie成功\033[0m")
    else:
        write_log("YouTube \033[31m校验cookie失败\033[0m")
    return youtube_cookie
