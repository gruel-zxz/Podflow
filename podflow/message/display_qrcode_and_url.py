# podflow/message/display_qrcode_and_url.py
# coding: utf-8

from datetime import datetime
from podflow import gVar
from podflow.basic.qr_code import qr_code
from podflow.basic.time_print import time_print


# 显示网址及二维码模块
def display_qrcode_and_url(
    output_dir,
    display_rss_address,
    qrcode,
    name,
    ids_update,
):
    address = gVar.config["address"]
    if token := gVar.config["token"]:
        xml_url = f"{address}/channel_rss/{output_dir}.xml?token={token}"
    else:
        xml_url = f"{address}/channel_rss/{output_dir}.xml"

    if display_rss_address or output_dir in ids_update:
        update_text = "已更新" if output_dir in ids_update else "无更新"
        time_print(
            f"{name} 播客{update_text}|地址:",
            Url=xml_url,
        )
    if (
        (display_rss_address or output_dir in ids_update)
        and qrcode
        and output_dir not in gVar.displayed_QRcode
    ):
        qr_code(xml_url, True)
        gVar.displayed_QRcode.append(output_dir)
