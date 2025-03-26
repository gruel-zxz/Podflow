# podflow/message/create_main_rss.py
# coding: utf-8

import time
from podflow import gVar
from podflow.youtube.build import youtube_xml_items
from podflow.bilibili.build import bilibili_xml_items
from podflow.message.get_media_name import get_media_name


def update_output_dir():
    output_dirs = []
    for format_value in gVar.video_id_update_format.values():
        if (
            isinstance(format_value, dict)
            and format_value["main"] not in gVar.video_id_failed
            and not format_value.get("finish",False)
        ):
            output_dirs.append(format_value["id"])
    return output_dirs


# 生成主rss模块
def create_main_rss():
    channelid_youtube_ids = gVar.channelid_youtube_ids
    channelid_bilibili_ids = gVar.channelid_bilibili_ids
    gVar.all_items = {
        key: {} for key in channelid_youtube_ids | channelid_bilibili_ids
    }
    all_channelid = list(gVar.all_items.keys())

    while all_channelid:
        for index, output_dir in enumerate(all_channelid):
            if output_dir in update_output_dir():
                time.sleep(1)
            else:
                if output_dir in channelid_youtube_ids:
                    output_dir_youtube = channelid_youtube_ids[output_dir]
                    channelid_youtube_value = gVar.channelid_youtube[output_dir_youtube]
                    items = youtube_xml_items(output_dir)
                    items["DisplayRSSaddress"] = channelid_youtube_value[
                        "DisplayRSSaddress"
                    ]
                    items["QRcode"] = channelid_youtube_value["QRcode"]
                    items["ID_Name"] = output_dir_youtube
                    items["InmainRSS"] = channelid_youtube_value["InmainRSS"]
                    items["type"] = "youtube"
                    gVar.all_youtube_content_ytid[output_dir] = get_media_name(
                        "youtube", items["items"]
                    )
                    gVar.all_items[output_dir] = items
                elif output_dir in channelid_bilibili_ids:
                    output_dir_bilibili = channelid_bilibili_ids[output_dir]
                    channelid_bilibili_value = gVar.channelid_bilibili[
                        output_dir_bilibili
                    ]
                    items = bilibili_xml_items(output_dir)
                    items["DisplayRSSaddress"] = channelid_bilibili_value[
                        "DisplayRSSaddress"
                    ]
                    items["QRcode"] = channelid_bilibili_value["QRcode"]
                    items["ID_Name"] = output_dir_bilibili
                    items["InmainRSS"] = channelid_bilibili_value["InmainRSS"]
                    items["type"] = "bilibili"
                    gVar.all_bilibili_content_bvid[output_dir] = get_media_name(
                        "bilibili", items["items"]
                    )
                    gVar.all_items[output_dir] = items
                del all_channelid[index]
                break
