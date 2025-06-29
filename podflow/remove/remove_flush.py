# podflow/remove/remove_flush.py
# coding: utf-8

from podflow import gVar
from podflow.basic.http_client import http_client
from podflow.httpfs.app_bottle import bottle_app_instance

# 缓存文件清理模块
def remove_flush(upload_url):
    if gVar.upload_json:
        result = {
            3: "缓存文件清理成功",
            -2: "用户名错误",
            -3: "密码错误",
            -10: "缓存文件不存在",
            -11: "缓存文件删除失败"
        }
        username = gVar.upload_json["username"]
        password = gVar.upload_json["password"]
        data = {
            "username": username,
            "password": password,
        }
        response, err = http_client(
            url=f"{upload_url}/flush",
            name="",
            max_retries=3,
            data=data,
            mode="post",
            mistake=True,
        )
        if response:
            response = response.json()
            code = response.get("code")
            data = response.get("data", {})
            message = response.get("message", "")
            if code == 3:
                bottle_text = "\033[32m缓存文件清理成功\033[0m"
            elif code == -11:
                error_message = response.get("error", "")
                if error_message:
                    bottle_text = f"\033[31m缓存文件清理失败\033[0m: {error_message}"
                else:
                    bottle_text = "\033[31m缓存文件清理失败\033[0m"
            else:
                bottle_text = f"\033[31m缓存文件清理失败\033[0m: {result.get(code, message)}"
        else:
            bottle_text = f"\033[31m缓存文件清理失败\033[0m: 网络连接失败{err}"
        bottle_app_instance.add_bottle_print(upload_url, "flush", bottle_text)
        bottle_app_instance.cherry_print(False)
