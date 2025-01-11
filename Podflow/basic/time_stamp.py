# Podflow/basic/time_stamp.py
# coding: utf-8

import time
import threading
import contextlib
from datetime import datetime
from Podflow.basic.http_client import http_client


# 时间戳模块
def time_stamp():
    time_stamps = []

    # 获取时间戳淘宝
    def time_stamp_taobao():
        if response := http_client(
            "http://api.m.taobao.com/rest/api3.do?api=mtop.common.getTimestamp",
            "",
            1,
            0,
        ):
            response_json = response.json()
            with contextlib.suppress(KeyError):
                time_stamps.append(int(response_json["data"]["t"]))

    # 获取时间戳美团
    def time_stamp_meituan():
        if response := http_client(
            "https://cube.meituan.com/ipromotion/cube/toc/component/base/getServerCurrentTime",
            "",
            1,
            0,
        ):
            response_json = response.json()
            with contextlib.suppress(KeyError):
                time_stamps.append(int(response_json["data"]))

    # 获取时间戳苏宁
    def time_stamp_suning():
        if response := http_client("https://f.m.suning.com/api/ct.do", "", 1, 0):
            response_json = response.json()
            with contextlib.suppress(KeyError):
                time_stamps.append(int(response_json["currentTime"]))

    # 创建线程
    thread1 = threading.Thread(target=time_stamp_taobao)
    thread2 = threading.Thread(target=time_stamp_meituan)
    thread3 = threading.Thread(target=time_stamp_suning)
    # 启动线程
    thread1.start()
    thread2.start()
    thread3.start()
    # 等待线程结束
    thread1.join()
    thread2.join()
    thread3.join()
    if time_stamps:
        return int(sum(time_stamps) / len(time_stamps))
    print(f"{datetime.now().strftime('%H:%M:%S')}|\033[31m获取时间戳api失败\033[0m")
    return round(time.time() * 1000)
