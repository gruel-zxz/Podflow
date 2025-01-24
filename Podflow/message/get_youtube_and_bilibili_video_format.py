# Podflow/message/get_youtube_and_bilibili_video_format.py
# coding: utf-8

from Podflow import gVar
from Podflow.basic.write_log import write_log
from Podflow.message.media_format import media_format


def one_format(id_update_format, id_num):
    entry_id_update_format = id_update_format[0]
    gVar.video_id_update_format[id_num]["url"] = entry_id_update_format["url"]
    gVar.video_id_update_format[id_num]["format"] = entry_id_update_format["duration_and_id"]
    gVar.video_id_update_format[id_num]["title"] = entry_id_update_format["title"]
    gVar.video_id_update_format[id_num]["timestamp"] = entry_id_update_format["timestamp"]
    gVar.video_id_update_format[id_num]["description"] = entry_id_update_format["description"]
    gVar.video_id_update_format[id_num]["main"] = id_num
    gVar.video_id_update_format[id_num]["image"] = entry_id_update_format["image"]
    gVar.video_id_update_format[id_num]["download"] = entry_id_update_format["download"]


# YouTube&哔哩哔哩视频信息模块
def get_youtube_and_bilibili_video_format(id_num, stop_flag, video_format_lock, prepare_animation):
    id_update_format = media_format(
        gVar.video_id_update_format[id_num]["url"],
        id_num,
        gVar.video_id_update_format[id_num]["media"],
        gVar.video_id_update_format[id_num]["quality"],
        gVar.video_id_update_format[id_num]["cookie"],
    )
    for fail_info in ["年龄限制", "需登录", "请求拒绝"]:
        if fail_info in id_update_format:
            if gVar.youtube_cookie:
                gVar.video_id_update_format[id_num]["cookie"] = "channel_data/yt_dlp_youtube.txt"
                id_update_format = media_format(
                    gVar.video_id_update_format[id_num]["url"],
                    id_num,
                    gVar.video_id_update_format[id_num]["media"],
                    gVar.video_id_update_format[id_num]["quality"],
                    gVar.video_id_update_format[id_num]["cookie"],
                )
                if fail_info in id_update_format:
                    id_update_format = f"\x1b[31m{fail_info}\x1b[0m(Cookies错误)"
            else:
                id_update_format = f"\x1b[31m{fail_info}\x1b[0m(需要Cookies)"
            break
    if gVar.video_id_update_format[id_num]["power"] is True and (
            "试看" in id_update_format
            or id_update_format == "无法获取音频ID"
        ):
        id_update_format = "\x1b[31m充电专属\x1b[0m"
    if isinstance(id_update_format, list):
        if len(id_update_format) == 1:
            one_format(id_update_format, id_num)
        else:
            entrys_id = []
            for entry_id_update_format in id_update_format:
                entry_id = entry_id_update_format["id"]
                entrys_id.append(entry_id)
                gVar.video_id_update_format[entry_id] = {
                    "id": gVar.video_id_update_format[id_num]["id"],
                    "media": gVar.video_id_update_format[id_num]["media"],
                    "quality": gVar.video_id_update_format[id_num]["quality"],
                    "url": entry_id_update_format["url"],
                    "name": gVar.video_id_update_format[id_num]["name"],
                    "cookie": gVar.video_id_update_format[id_num]["cookie"],
                    "format": entry_id_update_format["duration_and_id"],
                    "title": entry_id_update_format["title"],
                    "timestamp": entry_id_update_format["timestamp"],
                    "description": entry_id_update_format["description"],
                    "main": id_num,
                    "image": entry_id_update_format["image"],
                    "download": entry_id_update_format["download"],
                    "backward_update": gVar.video_id_update_format[id_num]["backward_update"],
                }
            gVar.video_id_update_format[id_num] = entrys_id
    else:
        with video_format_lock:
            stop_flag[0] = "error"
            prepare_animation.join()
            gVar.video_id_failed.append(id_num)
            write_log(
                f"{gVar.video_id_update_format[id_num]['name']}|{id_num}|{id_update_format}",
                None,
                True,
                False,
            )
            del gVar.video_id_update_format[id_num]
