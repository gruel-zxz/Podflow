# podflow/makeup/make_up_file.py
# coding: utf-8

import os
from podflow import gVar


# 补全缺失媒体文件到字典模块
def make_up_file():
    channelid_youtube_ids = gVar.channelid_youtube_ids
    channelid_bilibili_ids = gVar.channelid_bilibili_ids
    num = 0
    for output_dir in channelid_youtube_ids:
        num += len(gVar.all_youtube_content_ytid[output_dir])
    for output_dir in channelid_bilibili_ids:
        num += len(gVar.all_bilibili_content_bvid[output_dir])
    ratio_part = 0.01 / num if num else 0
    for output_dir, name in channelid_youtube_ids.items():
        youtube_os_list = os.listdir(f"channel_audiovisual/{output_dir}")
        for file_name in gVar.all_youtube_content_ytid[output_dir]:
            if file_name not in youtube_os_list:
                main = file_name.split(".")[0]
                media = file_name.split(".")[1]
                video_id_format = {
                    "id": output_dir,
                    "media": media,
                    "url": f"https://www.youtube.com/watch?v={main}",
                    "name": name,
                    "cookie": None,
                    "main": main,
                }
                if media == "mp4":
                    video_quality = gVar.channelid_youtube[name]["quality"]
                else:
                    video_quality = 1080
                video_id_format["quality"] = video_quality
                gVar.make_up_file_format[main] = video_id_format
            # 更新进度条
            ratio = gVar.index_message["schedule"][1] + ratio_part
            gVar.index_message["schedule"][1] = ratio

    for output_dir, name in channelid_bilibili_ids.items():
        bilibili_os_list = os.listdir(f"channel_audiovisual/{output_dir}")
        for file_name in gVar.all_bilibili_content_bvid[output_dir]:
            if file_name not in bilibili_os_list:
                main = file_name.split(".")[0][:12]
                if main not in gVar.make_up_file_format:
                    media = file_name.split(".")[1]
                    video_id_format = {
                        "id": output_dir,
                        "media": media,
                        "url": f"https://www.bilibili.com/video/{main}",
                        "name": name,
                        "cookie": "channel_data/yt_dlp_bilibili.txt",
                        "main": main,
                    }
                    if media == "mp4":
                        video_quality = gVar.channelid_bilibili[name]["quality"]
                    else:
                        video_quality = 1080
                    video_id_format["quality"] = video_quality
                    gVar.make_up_file_format[main] = video_id_format
            # 更新进度条
            ratio = gVar.index_message["schedule"][1] + ratio_part
            if ratio > 0.85:
                ratio = 0.85
            gVar.index_message["schedule"][1] = ratio
