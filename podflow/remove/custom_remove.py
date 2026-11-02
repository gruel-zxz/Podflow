# podflow/remove/custom_remove.py
# coding: utf-8

import os
from podflow.basic.write_log import write_log
from podflow.basic.custom_media_file import get_custom_media


# 删除多余的custom_media媒体模块
def custom_remove():
    # 自定义媒体的存放文件夹(channel_audiovisual下的custom_media文件夹)
    custom_media_output_dir = "custom_media"
    # 收集custom_media.json中所有条目引用的媒体文件名
    keep_files = set()
    for media in get_custom_media():
        output_format = media.get("type")
        for entry in media.get("lists", []):
            video_id = entry.get("id") or media.get("id", "")
            if output_format in ("m4a", "mp4"):
                keep_files.add(f"{video_id}.{output_format}")
            else:  # type缺失或异常时保守处理, 两种后缀的文件均保留
                keep_files.add(f"{video_id}.m4a")
                keep_files.add(f"{video_id}.mp4")
    folder_path = f"channel_audiovisual/{custom_media_output_dir}"
    # 文件夹不存在时无需清理
    if not os.path.exists(folder_path):
        return
    # 遍历custom_media文件夹, 删除未被条目引用的媒体文件
    for file_name in os.listdir(folder_path):
        if file_name in keep_files or not os.path.isfile(
            f"{folder_path}/{file_name}"
        ):
            continue
        os.remove(f"{folder_path}/{file_name}")
        write_log(f"custom_media|{file_name}抛弃文件已删除")
