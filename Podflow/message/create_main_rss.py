# Podflow/message/create_main_rss.py
# coding: utf-8

from Podflow import gVar
from Podflow.youtube.build import youtube_xml_items
from Podflow.bilibili.build import bilibili_xml_items
from Podflow.message.get_media_name import get_media_name


# 生成主rss模块
def create_main_rss():
    channelid_youtube_ids = gVar.channelid_youtube_ids
    for output_dir, output_dir_youtube in channelid_youtube_ids.items():
        channelid_youtube_value = gVar.channelid_youtube[output_dir_youtube]
        items = youtube_xml_items(output_dir)
        items["DisplayRSSaddress"] = channelid_youtube_value["DisplayRSSaddress"]
        items["QRcode"] = channelid_youtube_value["QRcode"]
        items["ID_Name"] = output_dir_youtube
        items["InmainRSS"] = channelid_youtube_value["InmainRSS"]
        items["type"] = "youtube"
        gVar.all_youtube_content_ytid[output_dir] = get_media_name("youtube", items["items"])
        gVar.all_items[output_dir] = items

    channelid_bilibili_ids = gVar.channelid_bilibili_ids
    for output_dir, output_dir_bilibili in channelid_bilibili_ids.items():
        channelid_bilibili_value = gVar.channelid_bilibili[output_dir_bilibili]
        items = bilibili_xml_items(output_dir)
        items["DisplayRSSaddress"] = channelid_bilibili_value["DisplayRSSaddress"]
        items["QRcode"] = channelid_bilibili_value["QRcode"]
        items["ID_Name"] = output_dir_bilibili
        items["InmainRSS"] = channelid_bilibili_value["InmainRSS"]
        items["type"] = "bilibili"
        gVar.all_bilibili_content_bvid[output_dir] = get_media_name("bilibili", items["items"])
        gVar.all_items[output_dir] = items
