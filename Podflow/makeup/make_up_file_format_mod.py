# Podflow/makeup/make_up_file_format_mod.py
# coding: utf-8

import threading
from datetime import datetime
from Podflow import gVar
from Podflow.basic.write_log import write_log
from Podflow.message.media_format import media_format


def makeup_format(video_id, makeup_format_lock):
    id_value = gVar.make_up_file_format[video_id]
    makeup_id_format = media_format(
        id_value["url"],
        id_value["main"],
        id_value["media"],
        id_value["quality"],
        id_value["cookie"],
    )
    for fail_info in ["年龄限制", "需登录"]:
        if fail_info in makeup_id_format:
            if gVar.youtube_cookie:
                gVar.make_up_file_format[video_id][
                    "cookie"
                ] = "channel_data/yt_dlp_youtube.txt"
                makeup_id_format = media_format(
                    id_value["url"],
                    id_value["main"],
                    id_value["media"],
                    id_value["quality"],
                    "channel_data/yt_dlp_youtube.txt",
                )
                if fail_info in makeup_id_format:
                    makeup_id_format = f"\x1b[31m{fail_info}\x1b[0m(Cookies错误)"
            else:
                makeup_id_format = f"\x1b[31m{fail_info}\x1b[0m(需要Cookies)"
            break
    if isinstance(makeup_id_format, list):
        if len(makeup_id_format) == 1:
            entry_id_makeup_format = makeup_id_format[0]
            gVar.make_up_file_format[video_id]["format"] = entry_id_makeup_format[
                "duration_and_id"
            ]
            gVar.make_up_file_format[video_id]["download"] = entry_id_makeup_format[
                "download"
            ]
        else:
            entrys_id = []
            for entry_id_makeup_format in makeup_id_format:
                entry_id = entry_id_makeup_format["id"]
                entrys_id.append(entry_id)
                gVar.make_up_file_format[entry_id] = {
                    "id": id_value["id"],
                    "name": id_value["name"],
                    "media": id_value["media"],
                    "quality": id_value["quality"],
                    "url": entry_id_makeup_format["url"],
                    "cookie": id_value["cookie"],
                    "format": entry_id_makeup_format["duration_and_id"],
                    "main": id_value["main"],
                    "download": entry_id_makeup_format["download"],
                }
            del gVar.make_up_file_format[video_id]
    else:
        with makeup_format_lock:
            write_log(f"{id_value['name']}|{video_id}|{makeup_id_format}")
            gVar.make_up_file_format_fail[video_id] = id_value[
                "id"
            ]  # 将无法补全的媒体添加到失败字典中
            del gVar.make_up_file_format[video_id]


# 补全在rss中缺失的媒体格式信息模块
def make_up_file_format_mod():
    # 判断是否补全
    if len(gVar.make_up_file_format) != 0:
        print(
            f"{datetime.now().strftime('%H:%M:%S')}|补全缺失媒体 \033[34m下载准备中...\033[0m"
        )
    # 创建线程锁
    makeup_format_lock = threading.Lock()
    # 创建线程列表
    makeup_format_threads = []
    for video_id in gVar.make_up_file_format:
        thread = threading.Thread(
            target=makeup_format,
            args=(
                video_id,
                makeup_format_lock,
            ),
        )
        makeup_format_threads.append(thread)
        thread.start()
    # 等待所有线程完成
    for thread in makeup_format_threads:
        thread.join()
