# podflow/upload/linked_client.py
# coding: utf-8

import time
import socket
import struct
import threading
from podflow import gVar
from podflow.upload.time_key import time_key
from podflow.basic.time_print import time_print
from podflow.httpfs.progress_bar import progress_update


BROADCAST_PORT = 37001
TIMEOUT = 1  # 搜索超时时间（秒）
MAX_BROADCAST_PORT = 37010  # 尝试广播的最大端口


# 获取本机局域网 IP (此函数在有代理时可能失效，但保留作为fallback或无代理时的功能)
def get_local_ip():
    try:
        # 尝试连接一个外部地址来确定哪个本地接口被用于路由
        # 注意：在某些代理/VPN配置下，这可能返回代理或VPN分配的IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # 非真实连接
            ip = s.getsockname()[0]
            time_print(f"局域网IP:{ip}")
            return ip
    except Exception as e:
        time_print(f"\033[31m获取本地 IP 失败:\033[0m {e}")
        return None


# 计算广播地址（默认 255.255.255.0）
def calculate_broadcast(ip, netmask="255.255.255.0"):
    try:
        # 确保输入是有效的IPv4地址
        socket.inet_aton(ip)
        socket.inet_aton(netmask)

        ip_packed = struct.unpack("!I", socket.inet_aton(ip))[0]
        mask_packed = struct.unpack("!I", socket.inet_aton(netmask))[0]
        broadcast_packed = ip_packed | ~mask_packed & 0xFFFFFFFF
        address = socket.inet_ntoa(struct.pack("!I", broadcast_packed))
        time_print(f"广播地址:{address}")
        return address
    except socket.error as e:
        time_print(f"\033[31m计算广播地址失败(无效IP或掩码):\033[0m {e}")
        return "255.255.255.255" # 回退地址
    except Exception as e:
        time_print(f"\033[31m计算广播地址失败:\033[0m {e}")
        return "255.255.255.255"  # 回退地址


# 发现局域网内的服务器
def discover_server(broadcast_ip, broadcast_port, time_out):
    servers = []
    # 创建UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(time_out)
        send_text = time_key("PODFLOW_DISCOVER_SERVER_REQUEST")
        send_text = send_text.encode("utf-8")
        try:
            # 发送广播请求
            sock.sendto(send_text, (broadcast_ip, broadcast_port))
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
        upload_ip = gVar.config["upload_ip"]
        if upload_ip:
            broadcast_ip = upload_ip
        else:
            local_ip = get_local_ip()
            if not local_ip:
                # 如果无法获取本地IP，广播发现也无法进行
                time_print("\033[31m无法获取本地IP，跳过广播发现。\033[0m")
                return
            broadcast_ip = calculate_broadcast(local_ip)
            if broadcast_ip in ["255.255.255.255", local_ip, "0.0.0.0"]:
                # 避免向无效或自己的地址广播
                time_print(f"\033[31m计算出的广播地址无效或为本机地址: {broadcast_ip}，跳过广播发现。\033[0m")
                return
        # 打印正在搜索上传服务器
        time_print("正在搜索上传服务器...")
        # 服务器列表为空
        servers = []
        # 在允许的端口范围内尝试发现服务器
        progress_lock = threading.Lock()
        def try_port(port, servers):
            server = discover_server(broadcast_ip, port, TIMEOUT)
            with progress_lock:
                if server:
                    servers.extend(server)
                progress_update(0.0005, added=True)
        threads = []
        for port in range(BROADCAST_PORT, MAX_BROADCAST_PORT + 1):
            t = threading.Thread(target=try_port, args=(port, servers))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        if not servers:
            time_print("找不到上传服务器", True)
        else:
            # 选择第一个找到的服务器
            server_ip, server_port = servers[0]
            time_print(f"正在连接到{server_ip}:{server_port}...", True)
            return f"http://{server_ip}:{server_port}"
