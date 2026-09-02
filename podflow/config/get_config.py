# podflow/config/get_config.py
# coding: utf-8

import os
import sys
import json
import copy
from podflow import gVar
from podflow import default_config
from podflow.basic.file_save import file_save
from podflow.basic.write_log import write_log
from podflow.basic.time_print import time_print


# 获取配置信息config模块
def get_config(file_name="config.json", first=True):
    # 检查当前文件夹中是否存在config文件
    if not os.path.exists(file_name):
        if first:
            if os.path.exists("config.json"):
                write_log(f"不存在配置文件{file_name}, 将使用原始配置文件")
                file_name = "config.json"
            else:
                # 如果文件不存在, 创建并写入默认字典
                file_save(default_config, "config.json")
                write_log("不存在配置文件, 已新建, 默认频道")
                return default_config
        else:
            write_log(f"配置文件{file_name}被删除, 将被恢复")
            file_save(gVar.config, file_name)
            return gVar.config

    # 如果文件存在, 读取字典并保存到config变量中
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            config = json.load(file)
        time_print("已读取配置文件")
    # 如果config格式有问题, 停止运行并报错
    except Exception as config_error:
        if first:
            write_log(f"配置文件有误, 请检查{file_name}, {str(config_error)}")
            sys.exit(0)
        else:
            write_log(f"配置文件有误, 将使用原配置, 请检查{file_name}, {str(config_error)}")
            return gVar.config
        
    # --- 针对 first 状态的分支逻辑 ---
    if first:
        # 初次启动，直接返回读取的完整配置
        gVar.original_config = config.copy()
        return config
    else:
        new_config = copy.deepcopy(gVar.original_config)
        for key, value in config.items():
            if key not in ["channelid_youtube", "channelid_bilibili"] and new_config.get(key) != value:
                write_log("提示：检测到无法应用的修改，需重启后启用，当前将使用原始参数")
                break
        
        for name in ["channelid_youtube", "channelid_bilibili"]:
            if name in config:
                new_config[name] = config[name]
            elif name in new_config:
                del new_config[name]
        return new_config
