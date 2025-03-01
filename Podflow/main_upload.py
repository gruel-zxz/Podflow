# Podflow/main_upload.py
# coding: utf-8

import sys
import threading
from Podflow.upload.upload_print import upload_print
from Podflow.upload.linked_server import handle_discovery, usable_port


def main_upload():
    # 服务发现相关配置
    broadcast_port = 37001  # 服务发现用端口
    service_port = 5000  # 实际服务端口

    broadcast_port = usable_port(broadcast_port, 37100)
    service_port = usable_port(service_port, 5050)
    if broadcast_port and service_port:
        discovery_thread = threading.Thread(
            target=handle_discovery,
            args=(broadcast_port, service_port),
        )
        discovery_thread.start()
    else:
        if not broadcast_port:
            upload_print("\033[31m广播端口被占用\033[0m")
        if not service_port:
            upload_print("\033[31m服务端口被占用\033[0m")
        sys.exit(0)
