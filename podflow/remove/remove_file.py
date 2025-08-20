# podflow/remove/remove_file.py
# coding: utf-8

import os
from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.basic.http_client import http_client
from podflow.upload.find_media_index import find_media_index


def judge_upload(upload_url, output_dir, file_name):
    if upload_url:
        upload_original = gVar.upload_original
        index = find_media_index(upload_original, file_name)
        if index != -1:
            return True
        item = upload_original[index]
        if not item["upload"]:
            return True
        result = {
            -2: "用户名错误",
            -3: "密码错误",
            -13: "删除模式错误",
            -6: "频道ID不存在",
            -14: "未提供文件名",
            -15: "文件名不匹配",
            -16: "频道ID不匹配",
            -17: "用户名不匹配",
            -18: "文件不存在",
            -19: "删除文件错误",
            -20: "未找到用户文件",
        }
        username = gVar.upload_json["username"]
        password = gVar.upload_json["password"]
        data = {
            "username": username,
            "password": password,
            "mode": "file",
            "channelid": output_dir,
            "filename": file_name,
        }
        response, err = http_client(
            url=f"{upload_url}/remove",
            name="",
            max_retries=3,
            data=data,
            mode="post",
            mistake=True,
        )
        if response:
            response = response.json()
            code = response.get("code")
            error = response.get("error", "")
            if code == 4:
                return True
            else:
                message = result.get(code, "未知错误")
                if error:
                    message += f":\n{error}"
                bottle_text = f"\033[31m远程删除文件失败\033[0m: {message}"
                write_log(bottle_text)
                return False
        else:
            bottle_text = f"\033[31m远程删除文件失败\033[0m: 网络连接失败{err}"
            write_log(bottle_text)
    elif gVar.config["upload"]:
        return False
    else:
        return True


# 删除多余媒体文件模块
def remove_file(upload_url):
    channelid_youtube_ids = gVar.channelid_youtube_ids
    for output_dir, name in channelid_youtube_ids.items():
        for file_name in os.listdir(f"channel_audiovisual/{output_dir}"):
            if file_name not in gVar.all_youtube_content_ytid[output_dir]:
                if judge_upload(upload_url, output_dir, file_name):
                    os.remove(f"channel_audiovisual/{output_dir}/{file_name}")
                    write_log(f"{name}|{file_name}抛弃文件已删除")

    channelid_bilibili_ids = gVar.channelid_bilibili_ids
    for output_dir, name in channelid_bilibili_ids.items():
        for file_name in os.listdir(f"channel_audiovisual/{output_dir}"):
            if file_name not in gVar.all_bilibili_content_bvid[output_dir]:
                if judge_upload(upload_url, output_dir, file_name):
                    os.remove(f"channel_audiovisual/{output_dir}/{file_name}")
                    write_log(f"{name}|{file_name}抛弃文件已删除")
