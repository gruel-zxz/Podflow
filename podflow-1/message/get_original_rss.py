# podflow/meaasge/get_original_rss.py
# coding: utf-8

import re
import hashlib
from podflow import gVar


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


# 获取原始xml模块
def get_original_rss():
    xmls_original_fail = []
    # 获取原始总xml文件
    try:
        with open(
            f"{gVar.config['filename']}.xml", "r", encoding="utf-8"
        ) as file:  # 打开文件进行读取
            rss_original = file.read()  # 读取文件内容
            get_xmls_original = {
                rss_original_channel: rss_original.split(
                    f"<!-- {{{rss_original_channel}}} -->\n"
                )[1]
                for rss_original_channel in list(
                    set(re.findall(r"(?<=<!-- \{).+?(?=\} -->)", rss_original))
                )
            }
    except FileNotFoundError:  # 文件不存在直接更新
        get_xmls_original = {}
        rss_original = ""
    # 如原始xml无对应的原频道items, 将尝试从对应频道的xml中获取
    for channelid_key in (
        gVar.channelid_youtube_ids | gVar.channelid_bilibili_ids
    ).keys():
        if channelid_key not in get_xmls_original.keys():
            try:
                with open(
                    f"channel_rss/{channelid_key}.xml", "r", encoding="utf-8"
                ) as file:  # 打开文件进行读取
                    youtube_rss_original = file.read()  # 读取文件内容
                    get_xmls_original[channelid_key] = youtube_rss_original.split(
                        f"<!-- {{{channelid_key}}} -->\n"
                    )[1]
            except FileNotFoundError:  # 文件不存在直接更新
                xmls_original_fail.append(channelid_key)
    # 生成原始rss的哈希值
    hash_rss_original = rss_create_hash(rss_original)
    return get_xmls_original, hash_rss_original, xmls_original_fail
