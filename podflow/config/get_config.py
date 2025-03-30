# podflow/config/get_config.py
# coding: utf-8

import os
import sys
import json
from podflow import default_config
from podflow.basic.write_log import write_log
from podflow.basic.time_print import time_print


# 获取配置信息config模块
def get_config(file_name="config.json"):
    # 检查当前文件夹中是否存在config文件
    if not os.path.exists(file_name):
        if os.path.exists("config.json"):
            write_log(f"不存在配置文件{file_name}, 将使用原始配置文件")
            file_name = "config.json"
        else:
            # 如果文件不存在, 创建并写入默认字典
            with open("config.json", "w") as file:
                json.dump(default_config, file, indent=4)
            write_log("不存在配置文件, 已新建, 默认频道")
            return default_config
    # 如果文件存在, 读取字典并保存到config变量中
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            config = json.load(file)
        time_print("已读取配置文件")
        return config
    # 如果config格式有问题, 停止运行并报错
    except Exception as config_error:
        write_log(f"配置文件有误, 请检查{file_name}, {str(config_error)}")
        sys.exit(0)
