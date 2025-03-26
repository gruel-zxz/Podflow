# podflow/remove/remove_dir.py
# coding: utf-8

import os
import re
import shutil
from podflow import gVar
from podflow.basic.write_log import write_log


# 删除已抛弃的媒体文件夹模块
def remove_dir():
    def remove_path(name):
        directory_path = f"channel_audiovisual/{name}"
        # 检查目录是否存在
        if os.path.exists(directory_path):
            # 删除该目录及其内容
            shutil.rmtree(directory_path)
        write_log(f"{name}文件夹已删除")

    folder_names = [
        folder
        for folder in os.listdir("channel_audiovisual")
        if os.path.isdir(f"channel_audiovisual/{folder}")
    ]
    folder_names_youtube = [name for name in folder_names if re.match(r"UC.{22}", name)]
    for name in folder_names_youtube:
        if name not in gVar.channelid_youtube_ids_original:
            remove_path(name)
    folder_names_bilibili = [name for name in folder_names if re.match(r"[0-9]+", name)]
    for name in folder_names_bilibili:
        if name not in gVar.channelid_bilibili_ids_original:
            remove_path(name)
