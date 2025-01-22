# Podflow/httpfs/port_judge.py
# coding: utf-8

import socket


def port_judge(host, port):
    # 创建一个新的 socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 设置 socket 为可重用
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        # 尝试绑定到指定端口
        sock.bind((host, port))
    except OSError:
        # 如果绑定失败，说明端口被占用
        return False
    else:
        # 如果绑定成功，端口可用，关闭 socket
        sock.close()
        return True
