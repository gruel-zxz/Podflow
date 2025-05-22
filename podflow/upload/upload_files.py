# podflow/upload/upload_files.py
# coding: utf-8

import time
from podflow.upload.build_hash import build_hash
from podflow.basic.http_client import http_client


def upload_file(username, password, channelid, filename):
    filename = f"channel_audiovisual/{channelid}/{filename}"
    with open(filename, "rb") as file:
        file.seek(0)
        hashs = build_hash(file)
        file.seek(0)
        data = {
            "username": username,
            "password": password,
            "channel_id": channelid,
            "hash": hashs,
        }
        if response := http_client(
            url="http://10.0.3.231:5000/upload",
            name="1",
            data=data,
            mode="post",
            file=file,
        ):
            return response.json()
        else:
            return None
    return None


def find_media_index(upload_original, target_media_id):
    for index, item in enumerate(upload_original):
        if item.get("media_id") == target_media_id:
            return index  # 返回找到的索引
    return -1


def filter_and_sort_media(media_list, day):
    current_time = int(time.time())
    one_month_ago = current_time - day * 24 * 60 * 60  # 30天前的时间戳
    filtered_sorted = sorted(
        (
            item
            for item in media_list
            if not item["upload"]
            and not item["remove"]
            and item["media_time"] < one_month_ago
        ),
        key=lambda x: x["media_time"],
    )
    result = [
        {"media_id": item["media_id"], "channel_id": item["channel_id"]}
        for item in filtered_sorted
    ]
    return result
