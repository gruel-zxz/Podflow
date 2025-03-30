# podflow/config/get_channelid.py
# coding: utf-8

from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.basic.time_print import time_print


# 从配置文件中获取频道模块
def get_channelid(name):
    config = gVar.config
    output_name = ""
    if name == "youtube":
        output_name = "YouTube"
    elif name == "bilibili":
        output_name = "BiliBili"
    if f"channelid_{name}" in config:
        time_print(f"已读取{output_name}频道信息")
        return config[f"channelid_{name}"]
    else:
        write_log(f"{output_name}频道信息不存在")
        return {}
