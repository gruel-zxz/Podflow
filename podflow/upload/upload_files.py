# podflow/upload/upload_files.py
# coding: utf-8

from datetime import datetime
from podflow import gVar
from podflow.httpfs.to_html import ansi_to_html
from podflow.upload.build_hash import build_hash
from podflow.basic.http_client import http_client
from podflow.httpfs.app_bottle import bottle_app_instance


# 上传文件模块
def upload_file(upload_url, username, password, channelid, filename):
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
            url=f"{upload_url}/upload",
            name="",
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


# 过滤和排序上传媒体模块
def filter_and_sort_media(media_list):
    filtered_sorted = sorted(
        (
            item
            for item in media_list
            if not item["upload"]
            and not item["remove"]
        ),
        key=lambda x: x["media_time"],
    )
    return [
        {"media_id": item["media_id"], "channel_id": item["channel_id"]}
        for item in filtered_sorted
    ]


# 媒体文件上传模块
def record_upload(upload_url, username, password, channelid, filename):
    response, hashs = upload_file(upload_url, username, password, channelid, filename)
    channelname = (
        gVar.channelid_youtube_ids_original | gVar.channelid_bilibili_ids_original
    ).get(channelid, "")
    now_time = datetime.now().strftime("%H:%M:%S")
    result = {
        0: "",
        1: "存在相同文件",
        -2: "用户名错误",
        -3: "密码错误",
        -4: "上传文件为空",
        -5: "文件不完整",
        -6: "频道ID不存在",
        -7: "文件格式有误",
    }
    name = filename.split(".")[0]
    if response:
        code = response.get("code")
        data = response.get("data", {})
        message = response.get("message", "")
        if code in [0, 1]:
            index = find_media_index(gVar.upload_original, filename)
            if index != -1:
                if filename := data.get("filename"):
                    gVar.upload_original[index]["upload"] = True
                    gVar.upload_original[index]["hash"] = hashs
                    gVar.upload_original[index]["filename"] = filename
        if code == 0:
            bottle_text = "\033[32m上传成功\033[0m"
        elif code == 1:
            bottle_text = f"\033[33m上传成功\033[0m: {result.get(code, message)}"
        else:
            bottle_text = f"\033[31m上传失败\033[0m: {result.get(code, message)}"
    else:
        bottle_text = "\033[31m上传失败\033[0m: 网络连接失败"
    bottle_text = f"{now_time}|{channelname}/{name}|{bottle_text}"
    bottle_app_instance.bottle_print.append(bottle_text)
    gVar.index_message["http"].append(ansi_to_html(bottle_text))
    bottle_app_instance.cherry_print(False)


# 总体上传模块
def all_upload(upload_url):
    if gVar.config["upload"]:
        result = filter_and_sort_media(gVar.upload_original)
        username = gVar.upload_json["username"]
        password = gVar.upload_json["password"]
        for item in result:
            record_upload(upload_url, username, password, item["channel_id"], item["media_id"])
            if gVar.upload_stop:
                break
