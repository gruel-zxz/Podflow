# Podflow/remove/remove_file.py
# coding: utf-8

import os
from Podflow import gVar
from Podflow.basic.write_log import write_log


# 删除多余媒体文件模块
def remove_file():
    channelid_youtube_ids = gVar.channelid_youtube_ids

    for output_dir, name in channelid_youtube_ids.items():
        for file_name in os.listdir(f"channel_audiovisual/{output_dir}"):
            if file_name not in gVar.all_youtube_content_ytid[output_dir]:
                os.remove(f"channel_audiovisual/{output_dir}/{file_name}")
                write_log(f"{name}|{file_name}已删除")

    channelid_bilibili_ids = gVar.channelid_bilibili_ids
    for output_dir, name in channelid_bilibili_ids.items():
        for file_name in os.listdir(f"channel_audiovisual/{output_dir}"):
            if file_name not in gVar.all_bilibili_content_bvid[output_dir]:
                os.remove(f"channel_audiovisual/{output_dir}/{file_name}")
                write_log(f"{name}|{file_name}已删除")
