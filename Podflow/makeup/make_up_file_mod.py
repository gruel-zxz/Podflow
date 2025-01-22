# Podflow/makeup/make_up_file_mod.py
# coding: utf-8

import os
from Podflow import gVar
from Podflow.basic.write_log import write_log
from Podflow.download.dl_aideo_video import dl_aideo_video


# 下载补全Youtube和哔哩哔哩视频模块
def make_up_file_mod():
    for video_id, id_value in gVar.make_up_file_format.items():
        media = id_value["media"]
        id_num = id_value["id"]
        if f"{video_id}.{media}" not in os.listdir(f"channel_audiovisual/{id_num}"):
            name = id_value["name"]
            write_log(f"{name}|{video_id} 缺失并重新下载")
            if dl_aideo_video(
                video_id,
                id_num,
                media,
                id_value["format"],
                gVar.config["retry_count"],
                id_value["download"]["url"],
                name,
                id_value["cookie"],
                id_value["download"]["num"],
            ):
                gVar.video_id_failed.append(video_id)
                write_log(f"{id_value['name']}|{video_id} \033[31m无法下载\033[0m")
