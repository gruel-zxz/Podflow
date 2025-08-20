# podflow/remove/remove_dir.py
# coding: utf-8

import os
import re
import shutil
from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.basic.http_client import http_client


def judge_upload(upload_url, name):
    if upload_url:
        sign = True
        upload_original = gVar.upload_original
        for item in upload_original:
            if item["channel_id"] == name and item["upload"] is True:
                sign = False
                break
        if sign:
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
            "mode": "folder",
            "channelid": name,
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
            if code == 5:
                return True
            else:
                message = result.get(code, "未知错误")
                if error:
                    message += f":\n{error}"
                bottle_text = f"\033[31m远程删除文件夹失败\033[0m: {message}"
                write_log(bottle_text)
                return False
        else:
            bottle_text = f"\033[31m远程删除文件夹失败\033[0m: 网络连接失败{err}"
            write_log(bottle_text)
    elif gVar.config["upload"]:
        return False
    else:
        return True


# 删除已抛弃的媒体文件夹模块
def remove_dir(upload_url):
    def remove_path(name):
        directory_path = f"channel_audiovisual/{name}"
        # 检查目录是否存在
        if os.path.exists(directory_path):
            # 删除该目录及其内容
            shutil.rmtree(directory_path)
        write_log(f"{name}抛弃文件夹已删除")

    folder_names = [
        folder
        for folder in os.listdir("channel_audiovisual")
        if os.path.isdir(f"channel_audiovisual/{folder}")
    ]
    folder_names_youtube = [name for name in folder_names if re.match(r"UC.{22}", name)]
    for name in folder_names_youtube:
        if (
            name not in gVar.channelid_youtube_ids_original
            and judge_upload(upload_url, name)
        ):
            remove_path(name)
    folder_names_bilibili = [name for name in folder_names if re.match(r"[0-9]+", name)]
    for name in folder_names_bilibili:
        if (
            name not in gVar.channelid_bilibili_ids_original
            and judge_upload(upload_url, name)
        ):
            remove_path(name)
