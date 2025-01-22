# Podflow/message/original_rss_fail_print.py
# coding: utf-8

from Podflow import gVar
from Podflow.basic.write_log import write_log


# 打印无法保留原节目信息模块
def original_rss_fail_print(xmls_original_fail):
    channelid_ids = gVar.channelid_youtube_ids | gVar.channelid_bilibili_ids
    for item in xmls_original_fail:
        if item in channelid_ids.keys():
            write_log(
                f"RSS文件中不存在 {channelid_ids[item]} 无法保留原节目"
            )
