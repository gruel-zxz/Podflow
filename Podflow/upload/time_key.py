# podflow/upload/time_key.py
# coding: utf-8

import hashlib
import base64
from datetime import datetime


# 生成时间密钥模块
def time_key(seed, time_interval=300, next_time_zone=False):  # 900 秒 = 15 分钟
    # 获取当前时间戳
    current_time = datetime.now()
    # 计算时间间隔的时间单元
    time_unit = int(current_time.timestamp() // time_interval)
    if next_time_zone:
        time_unit += 1
    # 将时间单元和种子组合生成密钥
    key_input = f"{time_unit}{seed}".encode("utf-8")
    # 使用 SHA-256 哈希算法生成密钥
    hashed_key = hashlib.sha256(key_input).digest()
    # 将密钥编码为 base64 格式
    encoded_key = base64.b64encode(hashed_key).decode("utf-8")
    return encoded_key


# 时间密钥校验模块
def check_time_key(key, seed, time_interval=300):
    key_list = [
        time_key(seed, time_interval),
        time_key(seed, time_interval, True),
    ]
    return key in key_list
