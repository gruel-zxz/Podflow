# Podflow/httpfs/port_judge.py
# coding: utf-8

import socket


# 定义一个函数，用于判断指定IP地址和端口号是否可用
def port_judge(hostip, port):
    # 尝试创建一个socket对象
    try:
        # 创建一个socket对象，指定地址族为IPv4，类型为TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # 设置socket选项，允许地址重用
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # 绑定socket对象到指定的IP地址和端口号
            sock.bind((hostip, port))
            # 如果绑定成功，返回True
            return True
    # 如果绑定失败，捕获OSError异常，并返回False
    except OSError:
        return False
