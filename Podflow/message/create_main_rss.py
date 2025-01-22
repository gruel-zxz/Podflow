# Podflow/message/create_main_rss.py
# coding: utf-8

import re
from Podflow import gVar
from Podflow.youtube.build import youtube_xml_items
from Podflow.bilibili.build import bilibili_xml_items
from Podflow.message.display_qrcode_and_url import display_qrcode_and_url


# 生成主rss模块
def create_main_rss():
    channelid_youtube_ids = gVar.channelid_youtube_ids
    for output_dir, output_dir_youtube in channelid_youtube_ids.items():
        channelid_youtube_value = gVar.channelid_youtube[output_dir_youtube]
        items = youtube_xml_items(output_dir)
        display_qrcode_and_url(
            output_dir,
            channelid_youtube_value,
            output_dir_youtube,
            gVar.channelid_youtube_ids_update,
        )
        if channelid_youtube_value["InmainRSS"]:
            gVar.all_items.append(items)
        gVar.all_youtube_content_ytid[output_dir] = re.findall(
            r"(?:/UC.{22}/)(.{11}\.m4a|.{11}\.mp4)(?=\"|\?)",
            items,
        )
    channelid_bilibili_ids = gVar.channelid_bilibili_ids
    for output_dir, output_dir_bilibili in channelid_bilibili_ids.items():
        channelid_bilibili_value = gVar.channelid_bilibili[output_dir_bilibili]
        items = bilibili_xml_items(output_dir)
        display_qrcode_and_url(
            output_dir,
            channelid_bilibili_value,
            output_dir_bilibili,
            gVar.channelid_bilibili_ids_update,
        )
        if channelid_bilibili_value["InmainRSS"]:
            gVar.all_items.append(items)
        gVar.all_bilibili_content_bvid[output_dir] = re.findall(
            r"(?:/[0-9]+/)(BV.{10}\.m4a|BV.{10}\.mp4|BV.{10}_p[0-9]+\.m4a|BV.{10}_p[0-9]+\.mp4|BV.{10}_[0-9]{9}\.m4a|BV.{10}_[0-9]{9}\.mp4)(?=\"|\?)",
            items,
        )
