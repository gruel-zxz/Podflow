# Podflow/upload/linked_server.py
# coding: utf-8

import socket
from Podflow.basic.write_log import write_log
from Podflow.basic.time_print import time_print
from Podflow.httpfs.port_judge import port_judge
from Podflow.upload.time_key import check_time_key


# 定义一个函数，用于判断端口是否可用
def usable_port(port, max_num):
    # 定义主机IP地址
    hostip = "0.0.0.0"
    # 循环判断端口是否可用
    while port <= max_num:
        # 调用port_judge函数判断端口是否可用
        if port_judge(hostip, port):
            # 如果端口可用，则返回该端口
            return port
        else:
            # 如果端口不可用，则将端口加1
            port += 1
    # 如果循环结束后，仍然没有找到可用的端口，则返回None
    return None


# 处理服务发现请求的UDP服务模块
def handle_discovery(broadcast_port, service_port):
    # 创建UDP套接字
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # 设置套接字选项，允许地址重用
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 设置套接字选项，允许广播
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # 绑定套接字到广播端口
        sock.bind(("0.0.0.0", broadcast_port))
        # 打印发现服务已启动
        time_print(f"发现服务已启动|端口: \033[32m{broadcast_port}\033[0m")
        # 无限循环，等待接收广播消息
        while True:
            # 接收广播消息
            data, addr = sock.recvfrom(1024)
            # 将接收到的消息解码为字符串
            data = data.decode('utf-8')
            # 检查消息是否包含时间关键字
            if check_time_key(data ,"PODFLOW_DISCOVER_SERVER_REQUEST"):
                # 打印接收到的发现请求成功
                write_log(f"来自{addr[0]}的发现请求\033[32m成功\033[0m")
                # 构造响应消息
                response = f"PODFLOW_SERVER_INFO|{service_port}".encode()
                # 发送响应消息
                sock.sendto(response, addr)
            else:
                # 打印接收到的发现请求失败
                write_log(f"来自{addr[0]}的发现请求\033[31m失败\033[0m")
