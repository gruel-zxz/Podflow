# podflow/message/rss_create_hash.py
# coding: utf-8

import re
import hashlib


# 生成哈希值模块
def create_hash(data):
    data_str = str(data)
    hash_object = hashlib.sha256()
    hash_object.update(data_str.encode())
    return hash_object.hexdigest()


# rss生成哈希值模块
def rss_create_hash(data):
    patterns = [
        r"<lastBuildDate>(\w+), (\d{2}) (\w+) (\d{4}) (\d{2}):(\d{2}):(\d{2}) \+\d{4}</lastBuildDate>",
        r"Podflow_light\.png",
        r"Podflow_dark\.png",
    ]
    replacement = ""
    for pattern in patterns:
        data = re.sub(pattern, replacement, data)
    return create_hash(data)
