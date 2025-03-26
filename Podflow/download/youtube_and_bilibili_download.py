# podflow/download/youtube_and_bilibili_download.py
# coding: utf-8

from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.download.dl_aideo_video import dl_aideo_video


# 下载YouTube和哔哩哔哩视频
def youtube_and_bilibili_download():
    for video_id, format_value in gVar.video_id_update_format.items():
        if isinstance(format_value, dict) and format_value["main"] not in gVar.video_id_failed:
            output_dir_name = format_value["name"]
            display_color = "\033[35m" if format_value["backward_update"] else "\033[95m"
            if dl_aideo_video(
                video_id,
                format_value["id"],
                format_value["media"],
                format_value["format"],
                gVar.config["retry_count"],
                format_value["download"]["url"],
                output_dir_name,
                format_value["cookie"],
                format_value["download"]["num"],
                display_color
            ):
                gVar.video_id_failed.append(format_value["main"])
                write_log(
                    f"{display_color}{output_dir_name}\033[0m|{video_id} \033[31m无法下载\033[0m"
                )
            gVar.video_id_update_format[video_id]["finish"] = True