# Podflow/upload/login.py
# coding: utf-8

import os
import json
import uuid
import hashlib
from Podflow import gVar
from Podflow.upload.time_key import time_key
from Podflow.basic.file_save import file_save
from Podflow.basic.write_log import write_log
from Podflow.basic.time_print import time_print
from Podflow.basic.http_client import http_client


def get_login():
    try:
        with open("channel_data/upload_login.json", "r") as file:
            upload_data = file.read()
        gVar.upload_data = json.loads(upload_data)
    except Exception:
        file_save(gVar.upload_data, "upload_login.json", "channel_data")


def create():
    new_username = str(uuid.uuid4())
    while new_username in gVar.upload_data:
        new_username = str(uuid.uuid4())
    new_password = hashlib.sha256(os.urandom(64)).hexdigest()
    gVar.upload_data[new_username] = new_password
    file_save(gVar.upload_data, "upload_login.json", "channel_data")
    return new_username, new_password


def get_account(url):
    url = f"{url}/newuser"
    token = time_key(
        "We need to generate an account password for uploading non one-time items that need to be saved."
    )
    data = {"token": token}
    if response := http_client(
        url=url,
        name="获取上传服务账号密码",
        data=data,
    ):
        return response.json()


def login(url, username, password):
    url = f"{url}/login"
    data = {
        "username": username,
        "password": password,
    }
    if response := http_client(
        url=url,
        name="登陆上传服务",
        data=data,
    ):
        return response.json()


def login_upload(url):
    try:
        # 尝试打开并读取 JSON 文件
        with open("channel_data/upload_data.json", "r") as file:
            upload_json = file.read()
        upload_json = json.loads(
            upload_json
        )
    except Exception:
        upload_json = {}
    if "username" not in upload_json:
        write_log("上传服务账号密码不存在")
        time_print("获取上传服务账号密码...")
        account_data = get_account(url)
        if "code" in account_data:
            if account_data["code"] == 0:
                write_log("账号密码获取\033[32m成功\033[0m")
                username = account_data["data"]["username"]
                password = account_data["data"]["password"]
                upload_json = {
                    "username": username,
                    "password": password,
                }
                file_save(upload_json, "upload_data.json", "channel_data")
                return upload_json
            elif account_data["code"] == -1:
                write_log("账号密码获取\033[31m失败\033[0m: 认证失败")
                return
            else:
                write_log("账号密码获取\033[31m失败\033[0m")
                return
        else:
            write_log("账号密码获取\033[31m失败\033[0m: 无法连接")
            return
    else:
        username = upload_json["username"]
        password = upload_json.get("password", "")
        login_data = login(url, username, password)
        if "code" in login_data:
            if login_data["code"] == 0:
                time_print("登陆上传服务\033[32m成功\033[0m")
                return upload_json
            elif login_data["code"] == -1:
                write_log("登陆上传服务\033[31m失败\033[0m: 认证失败")
                return
            elif login_data["code"] == -2:
                write_log("登陆上传服务\033[31m失败\033[0m: 账号错误")
                return
            elif login_data["code"] == -3:
                write_log("登陆上传服务\033[31m失败\033[0m: 密码错误")
                return
            else:
                write_log("登陆上传服务\033[31m失败\033[0m")
                return
        else:
            write_log("登陆上传服务\033[31m失败\033[0m: 无法连接")
            return
