# Podflow/config/get_channelid.py
# coding: utf-8

from datetime import datetime
from Podflow import gVar
from Podflow.basic.write_log import write_log


# 从配置文件中获取频道模块
def get_channelid(name):
    config = gVar.config
    output_name = ""
    if name == "youtube":
        output_name = "YouTube"
    elif name == "bilibili":
        output_name = "BiliBili"
    if f"channelid_{name}" in config:
        print(f"{datetime.now().strftime('%H:%M:%S')}|已读取{output_name}频道信息")
        return config[f"channelid_{name}"]
    else:
        write_log(f"{output_name}频道信息不存在")
        return {}
