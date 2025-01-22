# Podflow/message/get_video_format.py
# coding: utf-8

from Podflow import gVar
from Podflow.basic.write_log import write_log
from Podflow.basic.split_dict import split_dict
from Podflow.message.want_retry import want_retry
from Podflow.message.get_video_format_multithread import get_video_format_multithread


def get_youtube_format_front(ytid_content_update, backward_update):
    for ytid_key, ytid_value in ytid_content_update.items():
        channelid_youtube_value = gVar.channelid_youtube[
            gVar.channelid_youtube_ids_update[ytid_key]
        ]
        # 获取对应文件类型
        yt_id_file = channelid_youtube_value["media"]
        yt_id_failed_count = channelid_youtube_value["want_retry_count"]
        # 如果为视频格式获取分辨率
        if yt_id_file == "mp4":
            yt_id_quality = channelid_youtube_value["quality"]
        else:
            yt_id_quality = None
        for yt_id in ytid_value:
            if want_retry(yt_id, yt_id_failed_count):
                yt_id_format = {
                    "id": ytid_key,
                    "media": yt_id_file,
                    "quality": yt_id_quality,
                    "url": f"https://www.youtube.com/watch?v={yt_id}",
                    "name": gVar.channelid_youtube_ids[ytid_key],
                    "cookie": None,  # 特定视频需要
                    "backward_update": backward_update,
                    "power": None,
                }
                gVar.video_id_update_format[yt_id] = yt_id_format
            else:
                gVar.video_id_failed.append(yt_id)
                write_log(
                    f"{gVar.channelid_youtube_ids[ytid_key]}|{yt_id}|跳过更新",
                    None,
                    False,
                )


def get_bilibili_format_front(bvid_content_update, backward_update):
    for bvid_key, bvid_value in bvid_content_update.items():
        channelid_bilibili_value = gVar.channelid_bilibili[
            gVar.channelid_bilibili_ids_update[bvid_key]
        ]
        # 获取对应文件类型
        bv_id_file = channelid_bilibili_value["media"]
        bv_id_failed_count = channelid_bilibili_value["want_retry_count"]
        # 如果为视频格式获取分辨率
        if bv_id_file == "mp4":
            bv_id_quality = channelid_bilibili_value["quality"]
        else:
            bv_id_quality = None
        for bv_id in bvid_value:
            if want_retry(bv_id, bv_id_failed_count):
                if backward_update:
                    power = gVar.channelid_bilibili_rss[bvid_key]["backward"]["entry"][
                        bv_id
                    ].get("power", None)
                else:
                    power = gVar.channelid_bilibili_rss[bvid_key]["content"]["entry"][
                        bv_id
                    ].get("power", None)
                bv_id_format = {
                    "id": bvid_key,
                    "media": bv_id_file,
                    "quality": bv_id_quality,
                    "url": f"https://www.bilibili.com/video/{bv_id}",
                    "name": gVar.channelid_bilibili_ids[bvid_key],
                    "cookie": "channel_data/yt_dlp_bilibili.txt",
                    "backward_update": backward_update,
                    "power": power,
                }
                gVar.video_id_update_format[bv_id] = bv_id_format
            else:
                gVar.video_id_failed.append(bv_id)
                write_log(
                    f"{gVar.channelid_bilibili_ids[bvid_key]}|{bv_id}|跳过更新",
                    None,
                    False,
                )


# 获取YouTube&哔哩哔哩视频格式信息模块
def get_video_format():
    get_youtube_format_front(gVar.youtube_content_ytid_update, False)
    get_bilibili_format_front(gVar.bilibili_content_bvid_update, False)
    get_youtube_format_front(gVar.youtube_content_ytid_backward_update, True)
    get_bilibili_format_front(gVar.bilibili_content_bvid_backward_update, True)
    # 按参数拆分获取量
    if len(gVar.video_id_update_format) != 0:
        video_id_update_format_list = split_dict(
            gVar.video_id_update_format, gVar.config["preparation_per_count"]
        )
        for wait_animation_num, video_id_update_format_item in enumerate(
            video_id_update_format_list, start=1
        ):
            wait_animation_display_info = (
                "媒体视频 "
                if len(video_id_update_format_list) == 1
                else f"媒体视频|No.{str(wait_animation_num).zfill(2)} "
            )
            # 获取视频信息多线程模块
            get_video_format_multithread(
                video_id_update_format_item, wait_animation_display_info
            )
