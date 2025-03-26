# podflow/main_upload.py
# coding: utf-8

import sys
import cherrypy
from podflow.upload.login import get_login
from podflow.basic.time_print import time_print
from podflow.basic.folder_build import folder_build
from podflow.httpfs.app_bottle import bottle_app_instance
from podflow.upload.linked_server import handle_discovery, usable_port


def main_upload():
    # 构建文件夹channel_audiovisual
    folder_build("channel_audiovisual")
    # 构建文件夹channel_data
    folder_build("channel_data")
    # 获取账号密码
    get_login()
    # 服务发现相关配置
    broadcast_port = 37001  # 服务发现用端口
    service_port = 5000  # 实际服务端口
    hostip = "0.0.0.0"

    broadcast_port = usable_port(broadcast_port, 37010)
    service_port = usable_port(service_port, 5010)

    if broadcast_port and service_port:
        # 设置路由
        bottle_app_instance.setup_routes(upload=True)
        # 设置logname
        bottle_app_instance.set_logname(
            logname="upload.log",
            http_fs=True,
        )
        # 启动 CherryPy 服务器
        cherrypy.tree.graft(
            bottle_app_instance.app_bottle
        )  # 将 Bottle 应用嵌入到 CherryPy 中
        cherrypy.config.update(
            {
                "global": {
                    "tools.sessions.on": True,  # 启用会话支持
                    "server.socket_host": hostip,  # 监听所有 IP 地址
                    "server.socket_port": service_port,  # 设置监听端口
                    "log.screen": False,  # 禁用屏幕日志输出
                    "log.access_file": "",  # 关闭访问日志
                    "log.error_file": "",  # 关闭错误日志
                }
            }
        )
        cherrypy.engine.start()  # 启动 CherryPy 服务器
        time_print(f"上传服务已启动|端口: \033[32m{service_port}\033[0m")
        # 服务发现
        handle_discovery(broadcast_port, service_port)
    else:
        if not broadcast_port:
            time_print("\033[31m广播端口被占用\033[97m(37001-37010)\033[0m")
        if not service_port:
            time_print("\033[31m服务端口被占用\033[97m(5000-5010)\033[0m")
        time_print("请清理被占用端口后重试")
        sys.exit(0)
