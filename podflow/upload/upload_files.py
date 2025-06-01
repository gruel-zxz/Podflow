# podflow/upload/upload_files.py
# coding: utf-8

import time
from datetime import datetime
from podflow import gVar
from podflow.httpfs.to_html import ansi_to_html
from podflow.upload.build_hash import build_hash
from podflow.basic.http_client import http_client
from podflow.httpfs.app_bottle import bottle_app_instance


# 上传文件模块
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
            return response.json(), hashs
        else:
            return None, hashs
    return None, hashs


# 查找位置模块
def find_media_index(upload_original, target_media_id):
    for index, item in enumerate(upload_original):
        if item.get("media_id") == target_media_id:
            return index  # 返回找到的索引
    return -1


# 过滤和排序媒体模块
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


def record_upload(username, password, channelid, filename):
    response, hashs = upload_file(username, password, channelid, filename)
    channelname = (
        gVar.channelid_youtube_ids_original | gVar.channelid_bilibili_ids_original
    ).get(channelid, "")
    now_time = datetime.now().strftime("%H:%M:%S")
    if response:
        code = response.get("code")
        data = response.get("data", {})
        message = response.get("message", "")
        if code in [0, 1]:
            index = find_media_index(gVar.upload_original, filename)
            if index != -1:
                filename = data.get("filename")
                if filename:
                    gVar.upload_original[index]["upload"] = True
                    gVar.upload_original[index]["hash"] = hashs
                    gVar.upload_original[index]["filename"] = hashs

        bottle_text = f"{now_time}|{channelname}/{filename} Upload: {message}"
    else:
        bottle_text = f"{now_time}|{channelname}/{filename} Upload Failed"
    bottle_app_instance.bottle_print.append(bottle_text)
    gVar.index_message["http"].append(ansi_to_html(bottle_text))
    bottle_app_instance.cherry_print(False)
