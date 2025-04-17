# podflow/message/optimize_download.py
# coding: utf-8

from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.basic.time_print import time_print


# 优化下载顺序模块
def optimize_download():
    xmls_quantity = gVar.xmls_quantity
    video_id_update_format = gVar.video_id_update_format
    sorted_video_id_update_format = {}
    time_print("开始优化下载顺序")
    # 按总和从大到小排序
    sorted_channels = sorted(xmls_quantity.items(), key=lambda x: x[1], reverse=True)
    # 根据总和排序数据
    for channel_id, _ in sorted_channels:
        for key, value in video_id_update_format.items():
            if value["id"] == channel_id:
                sorted_video_id_update_format[key] = value
    if len(video_id_update_format) == len(sorted_video_id_update_format):
        gVar.video_id_update_format = sorted_video_id_update_format
        time_print("下载顺序优化\033[32m成功\033[0m")
    else:
        write_log("下载顺序优化\033[31m失败\033[0m")
