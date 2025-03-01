# Podflow/upload/linked_client.py
# coding: utf-8

import time
import socket
from datetime import datetime
from Podflow.upload.upload_print import upload_print


BROADCAST_PORT = 37000
TIMEOUT = 1  # 搜索超时时间（秒）
MAX_BROADCAST_PORT = 37101  # 尝试广播的最大端口


# 发现局域网内的服务器
def discover_server(broadcast_port, timeout):
    servers = []

    # 创建UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        try:
            # 发送广播请求
            sock.sendto(b"DISCOVER_SERVER_REQUEST", ("<broadcast>", broadcast_port))
        except Exception as e:
            upload_print(f"广播请求发送失败: {e}")
            return servers

        # 等待响应
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                if data.startswith(b"SERVER_INFO|"):
                    try:
                        port = int(data.decode().split("|")[1])
                        servers.append((addr[0], port))
                    except (IndexError, ValueError):
                        upload_print(f"收到来自 {addr} 的服务响应格式不正确")
            except socket.timeout:
                break
            except Exception as e:
                upload_print(f"接收数据出错: {e}")
                break

    return servers


# 自动发现并连接服务器模块
def connect_server():
    upload_print("正在搜索服务器...")

    current_port = BROADCAST_PORT
    servers = []
    time_print = f"{datetime.now().strftime('%H:%M:%S')}|"

    # 在允许的端口范围内尝试发现服务器
    while current_port < MAX_BROADCAST_PORT:
        print(f"\r{time_print}正在尝试广播端口 {current_port}...", end="")
        servers = discover_server(current_port, TIMEOUT)
        if servers:
            print("")
            break
        current_port += 1

    if not servers:
        upload_print("找不到服务器")
        return

    # 选择第一个找到的服务器
    server_ip, server_port = servers[0]
    upload_print(f"正在连接到{server_ip}:{server_port}")
