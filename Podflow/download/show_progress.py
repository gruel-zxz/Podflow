# Podflow/download/show_progress.py
# coding: utf-8

from Podflow.basic.time_format import time_format
from Podflow.download.convert_bytes import convert_bytes


# 下载显示模块
def show_progress(stream):
    stream = dict(stream)
    if "downloaded_bytes" in stream:
        downloaded_bytes = convert_bytes(stream["downloaded_bytes"]).rjust(9)
    else:
        downloaded_bytes = " Unknow B"
    if "total_bytes" in stream:
        total_bytes = convert_bytes(stream["total_bytes"])
    else:
        total_bytes = "Unknow B"
    if stream["speed"] is None:
        speed = " Unknow B"
    else:
        speed = convert_bytes(stream["speed"], [" B", "KiB", "MiB", "GiB"], 1000).rjust(
            9
        )
    if stream["status"] in ["downloading", "error"]:
        if "total_bytes" in stream:
            percent = stream["downloaded_bytes"] / stream["total_bytes"] * 100
        else:
            percent = 0
        percent = f"{percent:.1f}" if percent == 100 else f"{percent:.2f}"
        percent = percent.rjust(5)
        eta = time_format(stream["eta"]).ljust(8)
        print(
            (
                f"\r\033[94m{percent}%\033[0m|{downloaded_bytes}/{total_bytes}|\033[32m{speed}/s\033[0m|\033[93m{eta}\033[0m"
            ),
            end="",
        )
    if stream["status"] == "finished":
        if "elapsed" in stream:
            elapsed = time_format(stream["elapsed"]).ljust(8)
        else:
            elapsed = "Unknown "
        print(
            f"\r100.0%|{downloaded_bytes}/{total_bytes}|\033[32m{speed}/s\033[0m|\033[97m{elapsed}\033[0m"
        )
