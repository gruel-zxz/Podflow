# podflow/upload/uploaded_remove.py
# coding: utf-8

import os
import time
from datetime import datetime, timedelta
from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.basic.time_format import time_format
from podflow.basic.get_duration import get_duration
from podflow.upload.find_media_index import find_media_index


# 过滤和排序上传媒体模块
def filter_and_sort_media(media_list):
    filtered_sorted = sorted(
        (
            item
            for item in media_list
            if item["upload"]
            and not item["remove"]
        ),
        key=lambda x: x["media_time"],
    )
    return [
        {"media_id": item["media_id"], "channel_id": item["channel_id"]}
        for item in filtered_sorted
    ]

# 上传已删除媒体模块
def uploaded_remove(upload_url):
    if upload_url:
        # 当前时间
        now = datetime.now()
        # 30天前的时间
        one_month_ago = now - timedelta(days=30)
        # 转换为时间戳（秒级）
        timestamp = int(time.mktime(one_month_ago.timetuple()))
        result = filter_and_sort_media(gVar.upload_original)
        num = 0
        for item in result:
            if num < 10 and item["media_time"] < timestamp:
                break
            num += 1
            output_dir = item["channel_id"]
            file_name = item["media_id"]
            index = find_media_index(gVar.upload_original, file_name)
            if index != -1:
                gVar.upload_original[index]["remove"] = True
                file_path = f"channel_audiovisual/{output_dir}/{file_name}"
                duration = time_format(get_duration(file_path))
                gVar.upload_original[index]["duration"] = duration
                os.remove(file_path)
                write_log(f"{file_name}本地文件已删除")
