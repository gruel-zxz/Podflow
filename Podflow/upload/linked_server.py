# Podflow/upload/linked_server.py
# coding: utf-8

import socket
from Podflow.basic.time_print import time_print
from Podflow.httpfs.port_judge import port_judge
from Podflow.upload.time_key import check_time_key


def usable_port(port, max_num):
    hostip = "0.0.0.0"
    while port <= max_num:
        if port_judge(hostip, port):
            return port
        else:
            port += 1
    return None


# 处理服务发现请求的UDP服务模块
def handle_discovery(broadcast_port, service_port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", broadcast_port))
        time_print("发现服务已启动...")
        while True:
            data, addr = sock.recvfrom(1024)
            data = data.decode('utf-8')
            if check_time_key(data ,"PODFLOW_DISCOVER_SERVER_REQUEST"):
                time_print(f"来自{addr}的发现请求\033[32m成功\033[0m")
                response = f"PODFLOW_SERVER_INFO|{service_port}".encode()
                sock.sendto(response, addr)
            else:
                time_print(f"来自{addr}的发现请求\033[31m失败\033[0m")
