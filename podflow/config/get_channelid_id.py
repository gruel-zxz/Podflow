# podflow/config/get_channelid_id.py
# coding: utf-8

from podflow.basic.time_print import time_print


# 读取频道ID模块
def get_channelid_id(channelid, idname):
    output_name = ""
    if idname == "youtube":
        output_name = "YouTube"
    elif idname == "bilibili":
        output_name = "BiliBili"
    if channelid:
        channelid_ids = dict(
            {channel["id"]: key for key, channel in channelid.items()}
        )
        time_print(f"读取{output_name}频道的channelid成功")
    else:
        channelid_ids = {}
    return channelid_ids
