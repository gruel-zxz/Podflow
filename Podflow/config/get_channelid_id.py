# Podflow/config/get_channelid_id.py
# coding: utf-8

from datetime import datetime


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
        print(f"{datetime.now().strftime('%H:%M:%S')}|读取{output_name}频道的channelid成功")
    else:
        channelid_ids = {}
    return channelid_ids
