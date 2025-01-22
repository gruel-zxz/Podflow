# Podflow/message/display_qrcode_and_url.py
# coding: utf-8

from datetime import datetime
from Podflow import gVar
from Podflow.basic.qr_code import qr_code


# 显示网址及二维码模块
def display_qrcode_and_url(
    output_dir,
    channelid_video,
    channelid_video_name,
    channelid_video_ids_update,
):
    address = gVar.config["address"]
    if token := gVar.config["token"]:
        xml_url = f"{address}/channel_rss/{output_dir}.xml?token={token}"
    else:
        xml_url = f"{address}/channel_rss/{output_dir}.xml"

    if channelid_video["DisplayRSSaddress"] or output_dir in channelid_video_ids_update:
        update_text = "已更新" if output_dir in channelid_video_ids_update else "无更新"
        print(
            f"{datetime.now().strftime('%H:%M:%S')}|{channelid_video_name} 播客{update_text}|地址:\n\033[34m{xml_url}\033[0m"
        )
    if (
        (
            channelid_video["DisplayRSSaddress"]
            or output_dir in channelid_video_ids_update
        )
        and channelid_video["QRcode"]
        and output_dir not in gVar.displayed_QRcode
    ):
        qr_code(xml_url)
        gVar.displayed_QRcode.append(output_dir)
