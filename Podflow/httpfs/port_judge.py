# Podflow/httpfs/port_judge.py
# coding: utf-8

import socket


def port_judge(hostip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((hostip, port))
            return True
    except OSError:
        return False
