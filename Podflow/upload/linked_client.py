# Podflow/upload/linked_client.py
# coding: utf-8

import os
import time
import socket
from datetime import datetime
from Podflow import gVar
from Podflow.upload.time_key import time_key
from Podflow.basic.time_print import time_print


BROADCAST_PORT = 37001
TIMEOUT = 1  # 搜索超时时间（秒）
MAX_BROADCAST_PORT = 37010  # 尝试广播的最大端口


# 发现局域网内的服务器
def discover_server(broadcast_port, time_out):
    servers = []

    # 创建UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(time_out)
        send_text = time_key("PODFLOW_DISCOVER_SERVER_REQUEST")
        send_text = send_text.encode("utf-8")

        try:
            # 发送广播请求
            sock.sendto(send_text, ("<broadcast>", broadcast_port))
        except Exception:
            time_print("\033[31m请求发送失败\033[0m", False, True, False)
            return servers

        # 等待响应
        start_time = time.time()
        while time.time() - start_time < time_out:
            try:
                data, addr = sock.recvfrom(1024)
                if data.startswith(b"PODFLOW_SERVER_INFO|"):
                    try:
                        port = int(data.decode().split("|")[1])
                        servers.append((addr[0], port))
                    except (IndexError, ValueError):
                        time_print("\033[31m响应格式错误\033[0m", False, True, False)
            except socket.timeout:
                break
            except Exception:
                time_print("\033[31m接收数据出错\033[0m", False, True, False)
                break
    return servers


# 自动发现并连接服务器模块
def connect_upload_server():
    # 如果配置中启用了上传功能
    if gVar.config["upload"]:
        # 打印正在搜索上传服务器
        time_print("正在搜索上传服务器...")
        # 当前端口设置为广播端口
        current_port = BROADCAST_PORT
        # 服务器列表为空
        servers = []
        # 获取当前时间
        time_text = f"{datetime.now().strftime('%H:%M:%S')}|"
        # 获取命令行字节宽度
        try:
            terminal_width = os.get_terminal_size().columns
        except OSError:
            terminal_width = 47
        # 在允许的端口范围内尝试发现服务器
        while current_port < MAX_BROADCAST_PORT + 1:
            # 清空终端
            time_print(" " * terminal_width, True, True, False)
            # 打印尝试广播端口
            time_print(f"{time_text}尝试广播端口{current_port}...", True, True, False)
            servers = discover_server(current_port, TIMEOUT)
            if servers:
                break
            current_port += 1
        print("")
        if not servers:
            time_print("找不到上传服务器", True)
        else:
            # 选择第一个找到的服务器
            server_ip, server_port = servers[0]
            time_print(f"正在连接到{server_ip}:{server_port}...", True)
            return f"http://{server_ip}:{server_port}"
