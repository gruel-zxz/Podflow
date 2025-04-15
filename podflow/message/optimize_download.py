# podflow/message/optimize_download.py
# coding: utf-8

from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.basic.time_print import time_print


# 优化下载顺序模块
def optimize_download():
    xmls_quantity = gVar.xmls_quantity
    video_id_update_format = gVar.video_id_update_format
    channel_sums = {}
    sorted_video_id_update_format = {}
    time_print("开始计算频道媒体数量")
    # 计算每个频道的总和
    for channel_id, values in xmls_quantity.items():
        total = values["original"] + values["update"] + values["backward"]
        channel_sums[channel_id] = total
        gVar.xmls_quantity[channel_id]["total"] = total
    time_print("开始对频道进行排序")
    # 按总和从大到小排序
    sorted_channels = sorted(channel_sums.items(), key=lambda x: x[1], reverse=True)
    time_print("开始优化下载顺序")
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
