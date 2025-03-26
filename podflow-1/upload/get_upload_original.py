# podflow/upload/get_upload_original.py
# coding: utf-8

import re
import json
from datetime import datetime
from collections import Counter
from email.utils import parsedate_tz, mktime_tz
from podflow import gVar
from podflow.basic.file_save import file_save
from podflow.basic.write_log import write_log
from podflow.message.get_media_name import get_media_name


# 获取原始上传数据模块
def get_upload():
    xmls_original = gVar.xmls_original
    try:
        # 尝试打开并读取 JSON 文件
        with open("channel_data/upload.json", "r") as file:
            upload_original = file.read()  # 读取原始上传数据
        upload_original = json.loads(
            upload_original
        )  # 将读取的字符串转换为 Python 对象（列表或字典）
    except Exception:
        # 如果读取或解析失败，将 upload_original 初始化为空列表
        upload_original = []

    # 如果 upload_original 不为空
    if upload_original:
        # 提取每个条目的 channel_id
        channel_ids = [item.get("channel_id") for item in upload_original]
        # 统计每个 channel_id 的出现次数
        channelid_counts = Counter(channel_ids)
        # 将出现次数转换为字典
        age_counts = dict(channelid_counts)
        # 统计 xmls_original 中每个键对应的 <guid> 标签内的元素数量
        xmls_original_counts = {
            key: len(re.findall(r"(?<=<guid>).+(?=</guid>)", value))
            for key, value in xmls_original.items()
        }
        # 如果两个计数字典不相等，提示错误
        if age_counts != xmls_original_counts:
            print(
                f"{datetime.now().strftime('%H:%M:%S')}|无法获取完整原始上传信息"
            )
    # 如果 upload_original 为空
    else:
        # 遍历 xmls_original 的每个键值对
        for xmls_original_key, xmls_original_value in xmls_original.items():
            # 如果当前键在 channelid_youtube_ids 中
            if xmls_original_key in gVar.channelid_youtube_ids:
                # 使用正则表达式解析包含特定格式媒体ID的字符串
                media = get_media_name("youtube", xmls_original_value)
            # 如果当前键在 channelid_bilibili_ids 中
            elif xmls_original_key in gVar.channelid_bilibili_ids:
                media = get_media_name("bilibili", xmls_original_value)
            else:
                media = []
            # 查找每个上传条目的发布时间
            upload_time = re.findall(
                r"(?<=<pubDate>).+(?=</pubDate>)",
                xmls_original_value,
            )
            # 将日期字符串列表转换为 Unix 时间戳列表
            timestamps = [
                mktime_tz(
                    parsedate_tz(date_string)
                )  # 解析和转换每个日期字符串为 Unix 时间戳
                for date_string in upload_time
                if parsedate_tz(date_string)  # 确保解析成功
            ]
            # 如果媒体和时间戳的数量不匹配，记录错误并清空 upload_original
            if len(media) != len(timestamps):
                write_log("获取原始上传内容失败")  # 错误日志
                upload_original.clear()  # 清空 upload_original
                break  # 退出循环
            # 如果数量匹配，则整合 media_id、channel_id 和上传时间到 upload_original 列表
            upload_original += [
                {
                    "media_id": key,
                    "channel_id": xmls_original_key,
                    "media_time": value,
                    "upload": False,
                    "remove": False,
                    "hash": None,
                }
                for value, key in zip(
                    timestamps, media
                )  # 使用 zip() 将 media 和 timestamps 组合成对
            ]
        # 如果成功填充 upload_original
        if upload_original:
            file_save(upload_original, "upload.json", "channel_data")  # 保存到文件
    return upload_original


# 初始化原始上传信息
def get_upload_original():
    if gVar.config["upload"]:
        if upload_original := get_upload():
            gVar.upload_original = upload_original
        else:
            gVar.config["upload"] = False
