#!/usr/bin/env python
# coding: utf-8

import os
import re
import sys
import html
import json
import math
import time
import hashlib
import zipfile
import argparse
import binascii
import threading
import subprocess
import urllib.parse
from hashlib import md5
from functools import reduce
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# 获取命令行参数并判断
shortcuts_url_original =[]
argument = ""
update_num = -1
def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
    return ivalue
# 创建 ArgumentParser 对象
parser = argparse.ArgumentParser(description="you can try: python Podflow.py -n 24 -d 3600")
# 参数
parser.add_argument("-n", "--times", nargs=1, type=positive_int, metavar="NUM", help="number of times")
parser.add_argument("-d", "--delay", type=positive_int, default=900, metavar="NUM", help="delay in seconds(default: 900)")
parser.add_argument("--shortcuts", nargs="*", type=str, metavar="URL", help="only shortcuts can be work")
parser.add_argument("--file", nargs='?', help=argparse.SUPPRESS)
# 解析参数
args = parser.parse_args()
time_delay = args.delay
# 检查并处理参数的状态
if args.times is not None:
    update_num = int(args.times[0])
if args.shortcuts is not None:
    update_num = 1
    argument = "a-shell"
    shortcuts_url_original = args.shortcuts
if args.file is not None and ".json" in args.file:
    update_num = 1
    argument = ""
    shortcuts_url_original = []

# 默认参数
default_config = {
    "preparation_per_count": 100,
    "completion_count": 100,
    "retry_count": 5,
    "url": "http://127.0.0.1:8000",
    "title": "Podflow",
    "filename": "Podflow",
    "link": "https://github.com/gruel-zxz/podflow",
    "description": "在iOS平台上借助workflow和a-shell搭建专属的播客服务器。",
    "icon": "https://raw.githubusercontent.com/gruel-zxz/podflow/main/Podflow.png",
    "category": "TV &amp; Film",
    "channelid_youtube": {
        "youtube": {
            "update_size": 15,
            "id": "UCBR8-60-B28hp2BmDPdntcQ",
            "title": "YouTube",
            "quality": "480",
            "last_size": 50,
            "media": "m4a",
            "DisplayRSSaddress": False,
            "InmainRSS": True,
            "QRcode": False,
            "BackwardUpdate": False,
            "BackwardUpdate_size": 3,
        }
    },
    "channelid_bilibili": {
        "哔哩哔哩弹幕网": {
            "update_size": 25,
            "id": "8047632",
            "title": "哔哩哔哩弹幕网",
            "quality": "480",
            "last_size": 100,
            "media": "m4a",
            "DisplayRSSaddress": False,
            "InmainRSS": True,
            "QRcode": False,
            "BackwardUpdate": False,
            "BackwardUpdate_size": 3,
            "AllPartGet": False,
        }
    },
}
# 如果InmainRSS为False或频道有更新则无视DisplayRSSaddress的状态, 都会变为True。

print(f"{datetime.now().strftime('%H:%M:%S')}|Podflow开始运行.....")

# 全局变量
config = {}  #配置文件字典
channelid_youtube = {}  # YouTube频道字典
channelid_bilibili = {}  # 哔哩哔哩频道字典
channelid_youtube_ids = {}  # YouTube频道ID字典
channelid_youtube_ids_original = {}  # 原始YouTube频道ID字典
channelid_bilibili_ids = {}  # 哔哩哔哩频道ID字典
channelid_bilibili_ids_original = {}  # 原始哔哩哔哩频道ID字典

server_process_print_flag = ["keep"]  # httpserver进程打印标志列表
update_generate_rss = True  # 更新并生成rss布朗值
displayed_QRcode = []  # 已显示二维码列表

bilibili_data = {}  # 哔哩哔哩data字典
channelid_youtube_ids_update = {}  # 需更新的YouTube频道字典
youtube_content_ytid_update = {}  # 需下载YouTube视频字典
youtube_content_ytid_backward_update = {}  # 向后更新需下载YouTube视频字典
channelid_youtube_rss = {}  # YouTube频道最新Rss Response字典
channelid_bilibili_ids_update = {}  # 需更新的哔哩哔哩频道字典
bilibili_content_bvid_update = {}  # 需下载哔哩哔哩视频字典
channelid_bilibili_rss = {}  # 哔哩哔哩频道最新Rss Response字典
bilibili_content_bvid_backward_update = {}  # 向后更新需下载哔哩哔哩视频字典
video_id_failed = []  # YouTube&哔哩哔哩视频下载失败列表
video_id_update_format = {}  # YouTube和哔哩哔哩视频下载的详细信息字典
hash_rss_original = ""  # 原始rss哈希值文本
xmls_original = {}  # 原始xml信息字典
xmls_original_fail = []  # 未获取原始xml频道列表
youtube_xml_get_tree = {}  # YouTube频道简介和图标字典
all_youtube_content_ytid = {}  # 所有YouTube视频id字典
all_bilibili_content_bvid = {}  # 所有哔哩哔哩视频id字典
all_items = []  # 更新后所有item明细列表
overall_rss = ""  # 更新后的rss文本
make_up_file_format = {}  # 补全缺失媒体字典
make_up_file_format_fail = {}  # 补全缺失媒体失败字典

shortcuts_url = {}  # 输出至shortcut的url字典

# 文件保存模块
def file_save(content, file_name, folder=None):
    # 如果指定了文件夹则将文件保存到指定的文件夹中
    if folder:
        file_path = os.path.join(os.getcwd(), folder, file_name)
    else:
        # 如果没有指定文件夹则将文件保存在当前工作目录中
        file_path = os.path.join(os.getcwd(), file_name)
    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as file:
        if "." in file_name and file_name.split(".")[-1] == "json":
            json.dump(content, file, ensure_ascii=False, indent=4)
        else:
            file.write(content)

# 日志模块
def write_log(log, suffix=None, display=True, time_display=True, only_log=None):
    # 获取当前的具体时间
    current_time = datetime.now()
    # 格式化输出, 只保留年月日时分秒
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    # 打开文件, 并读取原有内容
    try:
        with open("log.txt", "r", encoding="utf-8") as file:
            contents = file.read()
    except FileNotFoundError:
        contents = ""
    # 将新的日志内容添加在原有内容之前
    log_in = re.sub(r"\033\[[0-9;]+m", "", log)
    log_in = re.sub(r"\n", "", log_in)
    new_contents = f"{formatted_time} {log_in}{only_log}\n{contents}" if only_log else f"{formatted_time} {log_in}\n{contents}"
    # 将新的日志内容写入文件
    file_save(new_contents, "log.txt")
    if display:
        formatted_time_mini = current_time.strftime("%H:%M:%S")
        log_print = f"{formatted_time_mini}|{log}" if time_display else f"{log}"
        log_print = f"{log_print}|{suffix}" if suffix else f"{log_print}"
        print(log_print)

# 查看ffmpeg、requests、yt-dlp模块是否安装
exit_sys = False  # 设置暂停运行变量

ffmpeg_worry = """\033[0mFFmpeg安装方法:
Ubuntu:
\033[32msudo apt update
sudo apt install ffmpeg\033[0m
CentOS:
\033[32msudo yum update
sudo yum install ffmpeg\033[0m
Debian:
\033[32msudo apt-get update
sudo apt-get install ffmpeg\033[0m
Arch Linux、Fedora:
\033[32msudo pacman -S ffmpeg
sudo dnf install ffmpeg\033[0m
检查FFmpeg版本:
\033[32mffmpeg -version\033[0m"""
try:
    # 执行 ffmpeg 命令获取版本信息
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    output = result.stdout.lower()
    # 检查输出中是否包含 ffmpeg 版本信息
    if "ffmpeg version" not in output:
        write_log("FFmpeg 未安装, 请安装后重试")
        print(ffmpeg_worry)
        sys.exit(0)
except FileNotFoundError:
    write_log("FFmpeg 未安装, 请安装后重试")
    print(ffmpeg_worry)
    sys.exit(0)

try:
    import requests
    # 如果导入成功你可以在这里使用requests库
except ImportError:
    try:
        subprocess.run(
            ["pip", "install", "chardet", "-U"], capture_output=True, text=True
        )
        subprocess.run(
            ["pip", "install", "requests", "-U"], capture_output=True, text=True
        )
        write_log("\033[31mrequests安装成功, 请重新运行\033[0m")
        exit_sys = True
    except FileNotFoundError:
        write_log("\033[31mrequests安装失败请重试\033[0m")
        exit_sys = True

try:
    import yt_dlp
    # 如果导入成功你可以在这里使用requests库
except ImportError:
    try:
        subprocess.run(
            ["pip", "install", "yt-dlp", "-U"], capture_output=True, text=True
        )
        write_log("\033[31myt-dlp安装成功, 请重新运行\033[0m")
        exit_sys = True
    except FileNotFoundError:
        write_log("\033[31myt-dlp安装失败请重试\033[0m")
        exit_sys = True

if exit_sys:  #判断是否暂停运行
    sys.exit(0)

# HTTP 请求重试模块
def http_client(url, name="", max_retries=10, retry_delay=4, headers_possess=False, cookies=None, data=None, mode="get"):
    user_agent = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    if "bilibili" in url:
        user_agent["Referer"] = "https://www.bilibili.com/"
    elif "youtube" in url:
        user_agent["Referer"] = "https://www.youtube.com/"
    elif "douyin" in url:
        headers_douyin = {
            'authority': 'sso.douyin.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'origin': 'https://www.douyin.com',
            'referer': 'https://www.douyin.com/',
            'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        }
        user_agent.update(headers_douyin)
    err = None  # 初始化 err 变量
    response = None  # 初始化 response 变量
    # 创建一个Session对象
    session = requests.Session()
    if headers_possess:
        session.headers.update(user_agent)
    if cookies:
        session.cookies.update(cookies)
    if data:
        session.params.update(data)
    for num in range(max_retries):
        try:
            if mode != "post":
                response = session.get(url, timeout=8)
            else:
                response = session.post(url, timeout=8)
            response.raise_for_status()
        except Exception as http_get_error:
            if response is not None and response.status_code in {404}:
                return response
            if name:
                print(
                    f"{datetime.now().strftime('%H:%M:%S')}|{name}|\033[31m连接异常重试中...\033[97m{num + 1}\033[0m"
                )
            if err:
                err = f":\n{str(http_get_error)}"
            else:
                err = ""
        else:
            return response
        time.sleep(retry_delay)
    if name:
        print(
            f"{datetime.now().strftime('%H:%M:%S')}|{name}|\033[31m达到最大重试次数\033[97m{max_retries}\033[0m{err}"
        )
    return response

# 批量正则表达式替换删除模块
def vary_replace(varys, text):
    for vary in varys:
        text = re.sub(vary, "", text)
    return text

# 读取三方库当日日志模块
def read_today_library_log():
    try:
        # 打开文件进行读取
        with open("log.txt", "r", encoding="utf-8") as log_file:
            log_lines = log_file.readlines()  # 读取所有行
        today_log_lines = []
        for log_line in log_lines:
            if f"{(datetime.now()- timedelta(days=1)).strftime('%Y-%m-%d')}" not in log_line:
                if "更新成功" in log_line or "安装成功" in log_line or "无需更新" in log_line:
                    today_log_lines.append(log_line)
            else:
                break
        today_library_log = "".join(today_log_lines)
        # 释放 lines 变量内存空间
        del log_lines
        return today_library_log
    except Exception:
        return ""

# 安装库模块
def library_install(library, library_install_dic=None):
    if version:= re.search(
        r"(?<=Version\: ).+",
        subprocess.run(["pip", "show", library], capture_output=True, text=True).stdout,
    ):
        write_log(f"{library}已安装")
        if library in library_install_dic:
            version_update = library_install_dic[library]
        else:
            # 获取最新版本编号
            version_update = http_client(
                f"https://pypi.org/project/{library}/", f"{library}", 2, 2
            )
            if version_update:
                version_update = re.search(
                    r"(?<=<h1 class=\"package-header__name\">).+?(?=</h1>)",
                    version_update.text,
                    flags=re.DOTALL,
                )
        # 如果库已安装, 判断是否为最新
        if version_update is None or version.group() not in version_update.group():
            # 如果库已安装, 则尝试更新
            try:
                subprocess.run(
                    ["pip", "install", "--upgrade", library],
                    capture_output=True,
                    text=True,
                )
                write_log(f"{library}更新成功")
            except FileNotFoundError:
                write_log(f"{library}更新失败")
        else:
            write_log(f"{library}无需更新|版本：\033[32m{version.group()}\033[0m")
    else:
        write_log(f"{library}未安装")
        # 如果库未安装, 则尝试安装
        try:
            subprocess.run(
                ["pip", "install", library, "-U"], capture_output=True, text=True
            )
            write_log(f"{library}安装成功")
        except FileNotFoundError:
            write_log(f"{library}安装失败")
            sys.exit(0)

# 安装/更新并加载三方库
library_install_list = [
    "yt-dlp",
    "astral",
    "qrcode",
    "chardet",
    "requests",
    "pycryptodome",
    "ffmpeg-python",
    "BeautifulSoup4",
    "RangeHTTPServer"
]

library_import = False
today_library_log = read_today_library_log()

while library_import is False:
    try:
        import ffmpeg
        import qrcode
        import yt_dlp
        from astral.sun import sun
        from astral import LocationInfo
        from Cryptodome.Cipher import PKCS1_OAEP
        from Cryptodome.PublicKey import RSA
        from Cryptodome.Hash import SHA256
        from bs4 import BeautifulSoup
        library_import = True
    except ImportError:
        today_library_log = ""
    for library in library_install_list:
        if library not in today_library_log:
            library_install_dic = {}
            def library_install_get(library):
                # 获取最新版本编号
                version_update = http_client(
                    f"https://pypi.org/project/{library}/", f"{library}", 2, 2
                )
                if version_update:
                    version_update = re.search(
                        r"(?<=<h1 class=\"package-header__name\">).+?(?=</h1>)",
                        version_update.text,
                        flags=re.DOTALL,
                    )
                if version_update:
                    library_install_dic[library] = version_update

            # 创建线程列表
            library_install_get_threads = []
            for library in library_install_list:
                thread = threading.Thread(target=library_install_get, args=(library,))
                library_install_get_threads.append(thread)
                thread.start()
            # 等待所有线程完成
            for thread in library_install_get_threads:
                thread.join()
            # 安装更新三方库
            for library in library_install_list:
                library_install(library, library_install_dic)
                today_library_log += f" {library}"
            break

# 获取时间戳模块
def time_stamp():
    if response:= http_client("https://api.m.taobao.com/rest/api3.do?api=mtop.common.getTimestamp", '获取时间戳', 3, 5):
        response_json = response.json()
    else:
        return round(time.time() * 1000)
    try:
        return response_json["data"]["t"]
    except KeyError:
        return round(time.time() * 1000)

# 格式化时间模块
def time_format(duration):
    if duration is None:
        return "Unknown"
    duration = int(duration)
    hours, remaining_seconds = divmod(duration, 3600)
    minutes = remaining_seconds // 60
    remaining_seconds = remaining_seconds % 60
    if hours > 0:
        return "{:02}:{:02}:{:02}".format(hours, minutes, remaining_seconds)
    else:
        return "{:02}:{:02}".format(minutes, remaining_seconds)

# 格式化字节模块
def convert_bytes(byte_size, units=None, outweigh=1024):
    if units is None:
        units = [" B", "KB", "MB", "GB"]
    if byte_size is None:
        byte_size = 0
    # 初始单位是字节
    unit_index = 0
    # 将字节大小除以1024直到小于1024为止
    while byte_size > outweigh and unit_index < len(units) - 1:
        byte_size /= 1024.0
        unit_index += 1
    # 格式化结果并返回
    return f"{byte_size:.2f}{units[unit_index]}"

# 网址二维码模块
def qr_code(data):
    # 创建一个QRCode对象
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=0,
    )
    # 设置二维码的数据
    qr.add_data(data)
    # 获取QR Code矩阵
    qr.make(fit=True)
    matrix = qr.make_image(fill_color="black", back_color="white").modules
    # 获取图像的宽度和高度
    width, height = len(matrix), len(matrix)
    height_double = math.ceil(height / 2)
    # 转换图像为ASCII字符
    fonts = ["▀", "▄", "█", " "]
    ascii_art = ""
    for y in range(height_double):
        if (y + 1) * 2 - 1 >= height:
            for x in range(width):
                ascii_art += (
                    fonts[0] if matrix[(y + 1) * 2 - 2][x] is True else fonts[3]
                )
        else:
            for x in range(width):
                if (
                    matrix[(y + 1) * 2 - 2][x] is True
                    and matrix[(y + 1) * 2 - 1][x] is True
                ):
                    ascii_art += fonts[2]
                elif (
                    matrix[(y + 1) * 2 - 2][x] is True
                    and matrix[(y + 1) * 2 - 1][x] is False
                ):
                    ascii_art += fonts[0]
                elif (
                    matrix[(y + 1) * 2 - 2][x] is False
                    and matrix[(y + 1) * 2 - 1][x] is True
                ):
                    ascii_art += fonts[1]
                else:
                    ascii_art += fonts[3]
            ascii_art += "\n"
    print(ascii_art)
    return height_double

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
        speed = convert_bytes(stream["speed"], [" B", "KiB", "MiB", "GiB"], 1000).rjust(9)
    if stream["status"] in ["downloading", "error"]:
        if "total_bytes" in stream:
            bar = stream["downloaded_bytes"] / stream["total_bytes"] * 100
        else:
            bar = 0
        bar = f"{bar:.1f}" if bar == 100 else f"{bar:.2f}"
        bar = bar.rjust(5)
        eta = time_format(stream["eta"]).ljust(8)
        print(
            (
                f"\r\033[94m{bar}%\033[0m|{downloaded_bytes}/{total_bytes}|\033[32m{speed}/s\033[0m|\033[93m{eta}\033[0m"
            ),
            end="",
        )
    if stream["status"] == "finished":
        if "elapsed" in stream:
            elapsed = time_format(stream["elapsed"]).ljust(8)
        else:
            elapsed = "Unknown "
        print(f"\r100.0%|{downloaded_bytes}/{total_bytes}|\033[32m{speed}/s\033[0m|\033[97m{elapsed}\033[0m")

# 获取媒体时长和ID模块
def media_format(video_website, video_url, media="m4a", quality="480", cookies=None):
    fail_message = None
    class MyLogger:
        def debug(self, msg):
            pass
        def warning(self, msg):
            pass
        def info(self, msg):
            pass
        def error(self, msg):
            pass
    def duration_and_formats(video_website, video_url):
        fail_message, infos = None, []
        try:
            # 初始化 yt_dlp 实例, 并忽略错误
            if cookies:
                ydl_opts = {
                    "no_warnings": True,
                    "quiet": True,  # 禁止非错误信息的输出
                    "logger": MyLogger(),
                    "http_headers": {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                        "Referer": "https://www.bilibili.com/",
                    },
                    'cookiefile': cookies,  # cookies 是你的 cookies 文件名
                }
            else:
                ydl_opts = {
                    "no_warnings": True,
                    "quiet": True,  # 禁止非错误信息的输出
                    "logger": MyLogger(),
                }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 使用提供的 URL 提取视频信息
                if info_dict:= ydl.extract_info(
                    f"{video_website}", download=False
                ):
                    # 获取视频时长并返回
                    entries = info_dict.get("entries", None)
                    download_url = info_dict.get("original_url", None)
                    if entries:
                        for playlist_num, entry in enumerate(entries):
                            infos.append({
                                "title": entry.get("title"),
                                "duration": entry.get("duration"),
                                "formats": entry.get("formats"),
                                "timestamp": entry.get("timestamp"),
                                "id": entry.get("id"),
                                "description": entry.get("description"),
                                "url": entry.get("webpage_url"),
                                "image": entry.get("thumbnail"),
                                "download": {
                                    "url": download_url,
                                    "num": playlist_num + 1,
                                }
                            })
                    else:
                        infos.append({
                            "title": info_dict.get("title"),
                            "duration": info_dict.get("duration"),
                            "formats": info_dict.get("formats"),
                            "timestamp": info_dict.get("timestamp"),
                            "id": info_dict.get("id"),
                            "description": info_dict.get("description"),
                            "url": info_dict.get("webpage_url"),
                            "image": info_dict.get("thumbnail"),
                            "download": {
                                "url": download_url,
                                "num": None
                            }
                        })
        except Exception as message_error:
            fail_message = (
                (str(message_error))
                .replace("ERROR: ", "")
                .replace("\033[0;31mERROR:\033[0m ", "")
                .replace(f"{video_url}: ", "")
                .replace("[youtube] ", "")
            )
        return fail_message, infos
    error_reason = {
        r"Premieres in ": "\033[31m预播\033[0m|",
        r"This live event will begin in ": "\033[31m直播预约\033[0m|",
        r"Video unavailable\. This video contains content from SME, who has blocked it in your country on copyright grounds": "\033[31m版权保护\033[0m",
        r"Premiere will begin shortly": "\033[31m马上开始首映\033[0m",
        r"Private video\. Sign in if you've been granted access to this video": "\033[31m私享视频\033[0m",
        r"This video is available to this channel's members on level: .*? Join this channel to get access to members-only content and other exclusive perks\.": "\033[31m会员专享\033[0m",
        r"Join this channel to get access to members-only content like this video, and other exclusive perks\.": "\033[31m会员视频\033[0m",
        r"Video unavailable\. This video has been removed by the uploader": "\033[31m视频被删除\033[0m",
        r"Video unavailable": "\033[31m视频不可用\033[0m",
        r"This video has been removed by the uploader": "\033[31m发布者删除\033[0m",
        r"This video has been removed for violating YouTube's policy on harassment and bullying": "\033[31m违规视频\033[0m",
        r"This video is private\. If the owner of this video has granted you access, please sign in\.": "\033[31m私人视频\033[0m",
        r"This video is unavailable": "\033[31m无法观看\033[0m",
        r"The following content is not available on this app\.\. Watch on the latest version of YouTube\.": "\033[31m需App\033[0m",
    }
    def fail_message_initialize(fail_message, error_reason):
        for key in error_reason:
            if re.search(key, fail_message):
                return [key, error_reason[key]]
    video_id_count, change_error, fail_message, infos = 0, None, "", []
    while (
        video_id_count < 3
        and change_error is None
        and (fail_message is not None or infos == [])
    ):
        video_id_count += 1
        fail_message, infos = duration_and_formats(video_website, video_url)
        if fail_message:
            change_error = fail_message_initialize(fail_message, error_reason)
    if change_error:
        fail_message = re.sub(rf"{change_error[0]}", change_error[1], fail_message)
    if fail_message is None:
        lists = []
        for entry in infos:
            duration = entry["duration"]
            formats = entry["formats"]
            if duration == "" or duration is None:
                return "无法获取时长"
            if formats == "" or formats is None:
                return "无法获取格式"
            duration_and_id = []
            duration_and_id.append(duration)
            # 定义条件判断函数
            def check_resolution(item):
                if "aspect_ratio" in item and (
                    isinstance(item["aspect_ratio"], (float, int))
                ):
                    if item["aspect_ratio"] >= 1:
                        return item["height"] <= int(quality)
                    else:
                        return item["width"] <= int(quality)
                else:
                    return False
            def check_ext(item, media):
                return item["ext"] == media if "ext" in item else False
            def check_vcodec(item):
                if "vcodec" in item:
                    return (
                        "vp" not in item["vcodec"].lower()
                        and "av01" not in item["vcodec"].lower()
                        and "hev1" not in item["vcodec"].lower()
                    )
                else:
                    return False
            # 获取最好质量媒体的id
            def best_format_id(formats):
                tbr_max = 0.0
                format_id_best = ""
                vcodec_best = ""
                for format in formats:
                    if (
                        "tbr" in format
                        and "drc" not in format["format_id"]
                        and format["protocol"] == "https"
                        and (isinstance(format["tbr"], (float, int)))
                        and format["tbr"] >= tbr_max
                    ):
                        tbr_max = format["tbr"]
                        format_id_best = format["format_id"]
                        vcodec_best = format["vcodec"]
                return format_id_best, vcodec_best
            # 进行筛选
            formats_m4a = list(
                filter(lambda item: check_ext(item, "m4a") and check_vcodec(item), formats)
            )
            (best_formats_m4a, vcodec_best) = best_format_id(formats_m4a)
            if best_formats_m4a == "" or best_formats_m4a is None:
                return "无法获取音频ID"
            duration_and_id.append(best_formats_m4a)
            if media == "mp4":
                formats_mp4 = list(
                    filter(
                        lambda item: check_resolution(item)
                        and check_ext(item, "mp4")
                        and check_vcodec(item),
                        formats,
                    )
                )
                (best_formats_mp4, vcodec_best) = best_format_id(formats_mp4)
                if best_formats_mp4 == "" or best_formats_mp4 is None:
                    return "无法获取视频ID"
                duration_and_id.append(best_formats_mp4)
                duration_and_id.append(vcodec_best)
            lists.append({
                "duration_and_id": duration_and_id,
                "title": entry.get("title"),
                "timestamp": entry.get("timestamp"),
                "id": entry.get("id"),
                "description": entry.get("description"),
                "url": entry.get("url"),
                "image": entry.get("image"),
                "download": entry.get("download"),
            })
        return lists
    else:
        return fail_message

# 获取已下载视频时长模块
def get_duration_ffmpeg(file_path):
    try:
        # 调用ffmpeg获取视频文件的时长信息
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        return math.ceil(duration)
    except ffmpeg.Error as e:
        error_note = e.stderr.decode('utf-8').splitlines()[-1]
        write_log(f"\033[31mError:\033[0m {error_note}")

# 等待动画模块
def wait_animation(stop_flag, wait_animation_display_info):
    animation = "."
    i = 1
    prepare_youtube_print = datetime.now().strftime("%H:%M:%S")
    while True:
        if stop_flag[0] == "keep":
            print(
                f"\r{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation.ljust(5)}\033[0m",
                end="",
            )
        elif stop_flag[0] == "error":
            print(
                f"\r{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation} \033[31m失败: \033[0m"
            )
            break
        elif stop_flag[0] == "end":
            print(
                f"\r{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation} 已完成\033[0m"
            )
            break
        if i % 5 == 0:
            animation = "."
        else:
            animation += "."
        i += 1
        time.sleep(0.5)

# 下载视频模块
def download_video(
    video_url,
    output_dir,
    output_format,
    format_id,
    video_website,
    video_write_log,
    sesuffix="",
    cookies=None,
    playlist_num=None,
):
    class MyLogger:
        def debug(self, msg):
            pass
        def warning(self, msg):
            pass
        def info(self, msg):
            pass
        def error(self, msg):
            print(
                msg
                .replace("ERROR: ", "")
                .replace("\033[0;31mERROR:\033[0m ", "")
                .replace(f"{video_url}: ", "")
                .replace("[youtube] ", "")
                .replace("[download] ", "")
            )
    ydl_opts = {
        "outtmpl": f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}",  # 输出文件路径和名称
        "format": f"{format_id}",  # 指定下载的最佳音频和视频格式
        "noprogress": True,
        "quiet": True,
        "progress_hooks": [show_progress],
        "logger": MyLogger(),
        "throttled_rate": "70K",  # 设置最小下载速率为:字节/秒
    }
    if cookies:
        ydl_opts["http_headers"] = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
        }
        ydl_opts["cookiefile"] = cookies  # cookies 是你的 cookies 文件名
    if playlist_num:  # 播放列表的第n个视频
        ydl_opts["playliststart"] = playlist_num
        ydl_opts["playlistend"] = playlist_num
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"{video_website}"])  # 下载指定视频链接的视频
    except Exception as download_video_error:
        write_log(
            f"{video_write_log} \033[31m下载失败\033[0m", None, True, True, (f"错误信息: {str(download_video_error)}")
            .replace("ERROR: ", "")
            .replace("\033[0;31mERROR:\033[0m ", "")
            .replace(f"{video_url}: ", "")
            .replace("[youtube] ", "")
            .replace("[download] ", "")
        )  # 写入下载失败的日志信息
        return video_url

# 视频完整下载模块
def dl_full_video(
    video_url,
    output_dir,
    output_format,
    format_id,
    id_duration,
    video_website,
    video_write_log,
    sesuffix="",
    cookies=None,
    playlist_num=None,
):
    if download_video(
        video_url,
        output_dir,
        output_format,
        format_id,
        video_website,
        video_write_log,
        sesuffix,
        cookies,
        playlist_num,
    ):
        return video_url
    duration_video = get_duration_ffmpeg(
        f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}"
    )  # 获取已下载视频的实际时长
    if abs(id_duration - duration_video) <= 1:  # 检查实际时长与预计时长是否一致
        return None
    if duration_video:
        write_log(
            f"{video_write_log} \033[31m下载失败\033[0m\n错误信息: 不完整({id_duration}|{duration_video})"
        )
        os.remove(
            f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}"
        )  # 删除不完整的视频
    return video_url

# 视频重试下载模块
def dl_retry_video(
    video_url,
    output_dir,
    output_format,
    format_id,
    id_duration,
    retry_count,
    video_website,
    video_write_log,
    sesuffix="",
    cookies=None,
    playlist_num=None,
):
    video_id_failed = dl_full_video(
        video_url,
        output_dir,
        output_format,
        format_id,
        id_duration,
        video_website,
        video_write_log,
        sesuffix,
        cookies,
        playlist_num,
    )
    # 下载失败后重复尝试下载视频
    video_id_count = 0
    while video_id_count < retry_count and video_id_failed:
        video_id_count += 1
        write_log(f"{video_write_log}第\033[34m{video_id_count}\033[0m次重新下载")
        video_id_failed = dl_full_video(
            video_url,
            output_dir,
            output_format,
            format_id,
            id_duration,
            video_website,
            video_write_log,
            sesuffix,
            cookies,
            playlist_num,
        )
    return video_id_failed

# 音视频总下载模块
def dl_aideo_video(
    video_url,
    output_dir,
    output_format,
    video_format,
    retry_count,
    video_website,
    output_dir_name="",
    cookies=None,
    playlist_num=None,
):
    if output_dir_name:
        video_write_log = f"\033[95m{output_dir_name}\033[0m|{video_url}"
    else:
        video_write_log = video_url
    id_duration = video_format[0]
    print(
        f"{datetime.now().strftime('%H:%M:%S')}|{video_write_log} \033[34m开始下载\033[0m",
        end="",
    )
    if output_format == "m4a":
        if video_format[1] in ["140", "30280"]:
            print("")
        else:
            print(f" \033[97m{video_format[1]}\033[0m")
        video_id_failed = dl_retry_video(
            video_url,
            output_dir,
            "m4a",
            video_format[1],
            id_duration,
            retry_count,
            video_website,
            video_write_log,
            "",
            cookies,
            playlist_num,
        )
    else:
        print(
            f"\n{datetime.now().strftime('%H:%M:%S')}|\033[34m视频部分开始下载\033[0m \033[97m{video_format[2]}\033[0m"
        )
        video_id_failed = dl_retry_video(
            video_url,
            output_dir,
            "mp4",
            video_format[2],
            id_duration,
            retry_count,
            video_website,
            video_write_log,
            ".part",
            cookies,
            playlist_num,
        )
        if video_id_failed is None:
            print(
                f"{datetime.now().strftime('%H:%M:%S')}|\033[34m音频部分开始下载\033[0m \033[97m{video_format[1]}\033[0m"
            )
            video_id_failed = dl_retry_video(
                video_url,
                output_dir,
                "m4a",
                video_format[1],
                id_duration,
                retry_count,
                video_website,
                video_write_log,
                ".part",
                cookies,
                playlist_num,
            )
        if video_id_failed is None:
            print(
                f"{datetime.now().strftime('%H:%M:%S')}|\033[34m开始合成...\033[0m", end=""
            )
            # 构建FFmpeg命令
            ffmpeg_cmd = [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                f"channel_audiovisual/{output_dir}/{video_url}.part.mp4",
                "-i",
                f"channel_audiovisual/{output_dir}/{video_url}.part.m4a",
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                f"channel_audiovisual/{output_dir}/{video_url}.mp4",
            ]
            # 执行FFmpeg命令
            try:
                subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
                print(" \033[32m合成成功\033[0m")
                os.remove(f"channel_audiovisual/{output_dir}/{video_url}.part.mp4")
                os.remove(f"channel_audiovisual/{output_dir}/{video_url}.part.m4a")
            except subprocess.CalledProcessError as dl_aideo_video_error:
                video_id_failed = video_url
                write_log(f"\n{video_write_log} \033[31m下载失败\033[0m\n错误信息: 合成失败:{dl_aideo_video_error}")
    if video_id_failed is None:
        write_log(f"{video_write_log} \033[32m下载成功\033[0m", None, True, True, f' {video_format[1] if output_format == "m4a" else f"{video_format[1]}+{video_format[2]}"}')  # 写入下载成功的日志信息
    return video_id_failed

# 构建文件夹模块
def folder_build(folder_name, parent_folder_name=None):
    if parent_folder_name:
        folder_path = os.path.join(os.getcwd(), parent_folder_name, folder_name)
    else:
        folder_path = os.path.join(os.getcwd(), folder_name)
    if not os.path.exists(folder_path):  # 判断文件夹是否存在
        os.makedirs(folder_path)  # 创建文件夹
        write_log(f"文件夹{folder_name}创建成功")

# 字典拆分模块
def split_dict(data, chunk_size=100, firse_item_only=False):
    chunks = []
    if chunk_size == 0:
        return [{}]
    else:
        if firse_item_only:
            end_value = chunk_size
        else:
            end_value = len(data)
        for i in range(0, end_value, chunk_size):
            chunk = dict(list(data.items())[i:i+chunk_size])
            chunks.append(chunk)
        return chunks

# 合并整形列表模块
def list_merge_tidy(list1, list2=[], length=None):
    final_list = []
    for item in list1 + list2:
        if item:
            item = item[:length]
        if item not in final_list:
            final_list.append(item)
    return final_list

# 获取配置信息config模块
def get_config():
    # 检查当前文件夹中是否存在config.json文件
    if not os.path.exists("config.json"):
        # 如果文件不存在, 创建并写入默认字典
        with open("config.json", "w") as file:
            json.dump(default_config, file, indent=4)
        write_log("不存在配置文件, 已新建, 默认频道")
        config = default_config
    else:
        # 如果文件存在, 读取字典并保存到config变量中
        try:
            with open("config.json", "r", encoding="utf-8") as file:
                config = json.load(file)
            print(f"{datetime.now().strftime('%H:%M:%S')}|已读取配置文件")
        # 如果config格式有问题, 停止运行并报错
        except Exception as config_error:
            write_log(f"配置文件有误, 请检查config.json, {str(config_error)}")
            sys.exit(0)
    return config

# 纠正配置信息config模块
def correct_config():
    # 对completion_count进行纠正
    if (
        "completion_count" not in config
        or not isinstance(config["completion_count"], int)
        or config["completion_count"] < 0
    ):
        config["completion_count"] = default_config["completion_count"]
    # 对preparation_per_count进行纠正
    if (
        "preparation_per_count" not in config
        or not isinstance(config["preparation_per_count"], int)
        or config["preparation_per_count"] <= 0
    ):
        config["preparation_per_count"] = default_config["preparation_per_count"]
    # 对retry_count进行纠正
    if (
        "retry_count" not in config
        or not isinstance(config["retry_count"], int)
        or config["retry_count"] <= 0
    ):
        config["retry_count"] = default_config["retry_count"]
    # 对url进行纠正
    if "url" not in config or not re.search(
        r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", config["url"]
    ):
        config["url"] = default_config["url"]
    # 对title进行纠正
    if "title" not in config:
        config["title"] = default_config["title"]
    # 对filename进行纠正
    if "filename" not in config:
        config["filename"] = default_config["filename"]
    # 对link进行纠正
    if "link" not in config or not re.search(
        r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", config["link"]
    ):
        config["link"] = default_config["link"]
    # 对description进行纠正
    if "description" not in config:
        config["description"] = default_config["description"]
    # 对icon进行纠正
    if "icon" not in config or not re.search(
        r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", config["icon"]
    ):
        config["icon"] = default_config["icon"]
    # 对category进行纠正
    if "category" not in config:
        config["category"] = default_config["category"]
    if f"{config['url']}/{config['filename']}.xml" not in shortcuts_url_original:
        shortcuts_url[f"{config['filename']}(Main RSS)"] = f"{config['url']}/{config['filename']}.xml"

# 根据经纬度判断昼夜模块
def judging_day_and_night(latitude, longitude):
    # 创建一个 LocationInfo 对象，只提供经纬度信息
    location = LocationInfo("", "", "", latitude=latitude, longitude=longitude)
    # 获取当前日期和时间，并为其添加时区信息
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    tommorrow = now + timedelta(days=1)
    def sunrise_sunset(time):
        # 创建一个 Sun 对象
        sun_time = sun(location.observer, date=time)
        # 计算日出和日落时间，以及日落前和日出后的一小时
        sunrise = sun_time["sunrise"]
        sunset = sun_time["sunset"]
        sunrise_minus_one_hour = sunrise  # - timedelta(hours=1)
        sunset_plus_one_hour = sunset  # + timedelta(hours=1)
        return sunrise_minus_one_hour, sunset_plus_one_hour
    sunrise_now, sunset_now = sunrise_sunset(now)
    sunrise_yesterday, sunset_yesterday = sunrise_sunset(yesterday)
    sunrise_tommorrow, sunset_tommorrow = sunrise_sunset(tommorrow)
    # 判断现在是白天还是晚上
    if sunrise_now < sunset_now:
        if (
            sunrise_now < now < sunset_now
            or sunrise_yesterday < now < sunset_yesterday
            or sunrise_tommorrow < now < sunset_tommorrow
        ):
            return "light"
        else:
            return "dark"
    else:
        if (
            sunrise_now > now > sunset_now
            or sunrise_yesterday > now > sunset_yesterday
            or sunrise_tommorrow > now > sunset_tommorrow
        ):
            return "dark"
        else:
            return "light"

# 根据日出日落修改封面(只适用原封面)模块
def channge_icon():
    if config["icon"] == default_config["icon"]:
        def ipinfo():
            if response:= http_client("https://ipinfo.io/json/", "", 1, 0):
                data = response.json()
                # 提取经度和纬度
                coordinates = data ["loc"].split(",")
                return True, coordinates[0], coordinates[1]
            else: 
                return False, None, None
        def ipapi():
            if response:= http_client("http://ip-api.com/json/", "", 1, 0):
                data = response.json()
                # 提取经度和纬度
                return True, data["lat"], data["lon"]
            else: 
                return False, None, None
        def freegeoip():
            if response:= http_client("https://freegeoip.app/json/", "", 1, 0):
                data = response.json()
                # 提取经度和纬度
                return True, data["latitude"], data["longitude"]
            else: 
                return False, None, None
        label = False
        # 公网获取经纬度
        label, latitude, longitude = ipinfo()
        if label is False:
            write_log("获取昼夜信息重试中...\033[97m1\033[0m")
            label, latitude, longitude = ipapi()
            if label is False:
                write_log("获取昼夜信息重试中...\033[97m2\033[0m")
                label, latitude, longitude = freegeoip()
                if label is False:
                    write_log("获取昼夜信息失败")
        if label:
            picture_name = f"Podflow_{judging_day_and_night(latitude, longitude)}"
            config["icon"] = f"https://raw.githubusercontent.com/gruel-zxz/podflow/main/{picture_name}.png"

# 从配置文件中获取频道模块
def get_channelid(name):
    if name == "youtube":
        output_name = "YouTube"
    elif name == "bilibili":
        output_name = "BiliBili"
    if f"channelid_{name}" in config:
        print(f"{datetime.now().strftime('%H:%M:%S')}|已读取{output_name}频道信息")
        return config[f"channelid_{name}"]
    else:
        write_log(f"{output_name}频道信息不存在")
        return {}

# channelid修正模块
def correct_channelid(channelid, website):
    if website == "youtube":
        channelid_name = "youtube"
        output_name = "YouTube"
    elif website == "bilibili":
        channelid_name = "哔哩哔哩弹幕网"
        output_name = "BiliBili"
    # 音视频格式及分辨率常量
    video_media = [
        "m4v",
        "mov",
        "qt",
        "avi",
        "flv",
        "wmv",
        "asf",
        "mpeg",
        "mpg",
        "vob",
        "mkv",
        "rm",
        "rmvb",
        "vob",
        "ts",
        "dat",
    ]
    dpi = [
        "144",
        "180",
        "216",
        "240",
        "360",
        "480",
        "720",
        "1080",
        "1440",
        "2160",
        "4320",
    ]
    media = ["m4a", "mp4"]
    # 复制字典channelid, 遍历复制后的字典进行操作以避免在循环中删除元素导致的迭代错误
    channelid_copy = channelid.copy()
    # 对channelid的错误进行更正
    for channelid_key, channeli_value in channelid_copy.items():
        # 判断是否为字典
        if not isinstance(channeli_value, dict):
            channeli_value = {"id": channeli_value}
            channelid[channelid_key] = channeli_value
        # 判断id是否正确
        if "id" not in channeli_value or (
            website == "youtube" and not re.search(
                r"^UC.{22}", channeli_value["id"]
            )
        ) or (
            website == "bilibili" and not channeli_value["id"].isdigit()
        ):
            # 删除错误的
            del channelid[channelid_key]
            write_log(f"{output_name}频道 {channelid_key} ID不正确")
        else:
            # 对update_size进行纠正
            if (
                "update_size" not in channeli_value
                or not isinstance(channeli_value["update_size"], int)
                or channeli_value["update_size"] <= 0
            ):
                channelid[channelid_key]["update_size"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["update_size"]
            # 对id进行纠正
            if website == "youtube":
                channelid[channelid_key]["id"] = re.search(
                    r"UC.{22}", channeli_value["id"]
                ).group()
            # 对last_size进行纠正
            if (
                "last_size" not in channeli_value
                or not isinstance(channeli_value["last_size"], int)
                or channeli_value["last_size"] <= 0
            ):
                channelid[channelid_key]["last_size"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["last_size"]
            channelid[channelid_key]["last_size"] = max(
                channelid[channelid_key]["last_size"],
                channelid[channelid_key]["update_size"],
            )
            # 对title进行纠正
            if "title" not in channeli_value:
                channelid[channelid_key]["title"] = channelid_key
            # 对quality进行纠正
            if (
                (
                    "quality" not in channeli_value
                    or channeli_value["quality"] not in dpi
                )
                and "media" in channeli_value
                and channeli_value["media"] == "mp4"
            ):
                channelid[channelid_key]["quality"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["quality"]
            # 对media进行纠正
            if (
                "media" in channeli_value
                and channeli_value["media"] not in media
                and channeli_value["media"] in video_media
            ):
                channelid[channelid_key]["media"] = "mp4"
            elif (
                "media" in channeli_value
                and channeli_value["media"] not in media
                or "media" not in channeli_value
            ):
                channelid[channelid_key]["media"] = "m4a"
            # 对DisplayRSSaddress进行纠正
            if "DisplayRSSaddress" not in channeli_value or not isinstance(
                channeli_value["DisplayRSSaddress"], bool
            ):
                channelid[channelid_key]["DisplayRSSaddress"] = False
            # 对InmainRSS进行纠正
            if "InmainRSS" in channeli_value and isinstance(
                channeli_value["InmainRSS"], bool
            ):
                if channeli_value["InmainRSS"] is False:
                    channelid[channelid_key]["DisplayRSSaddress"] = True
            else:
                channelid[channelid_key]["InmainRSS"] = True
            # 对QRcode进行纠正
            if "QRcode" not in channeli_value or not isinstance(
                channeli_value["QRcode"], bool
            ):
                channelid[channelid_key]["QRcode"] = False
            # 对BackwardUpdate进行纠正
            if "BackwardUpdate" not in channeli_value or not isinstance(
                channeli_value["BackwardUpdate"], bool
            ):
                channelid[channelid_key]["BackwardUpdate"] = False
            # 对BackwardUpdate_size进行纠正
            if channelid[channelid_key]["BackwardUpdate"] and (
                "BackwardUpdate_size" not in channeli_value
                or not isinstance(channeli_value["BackwardUpdate_size"], int)
                or channeli_value["BackwardUpdate_size"] <= 0
            ):
                channelid[channelid_key]["BackwardUpdate_size"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["BackwardUpdate_size"]
            if website == "bilibili":
                # 对AllPartGet进行纠正
                if "AllPartGet" not in channeli_value or not isinstance(
                    channeli_value["AllPartGet"], bool
                ):
                    channelid[channelid_key]["AllPartGet"] = False
        if channelid[channelid_key]["InmainRSS"] is False and f"{config['url']}/channel_rss/{channeli_value['id']}.xml" not in shortcuts_url_original:
            shortcuts_url[channelid_key] = f"{config['url']}/channel_rss/{channeli_value['id']}.xml"
    return channelid

# 读取频道ID模块
def get_channelid_id(channelid, idname):
    if idname == "youtube":
        output_name = "YouTube"
    elif idname == "bilibili":
        output_name = "BiliBili"
    if channelid:
        channelid_ids = dict(
            {channel["id"]: key for key, channel in channelid.items()}
        )
        print(f"{datetime.now().strftime('%H:%M:%S')}|读取{output_name}频道的channelid成功")
    else:
        channelid_ids = {}
    return channelid_ids

# 获取最新的img_key和sub_key模块
def getWbiKeys(bilibili_cookie=None):
    bilibili_url = "https://api.bilibili.com/x/web-interface/nav"
    if resp:= http_client(bilibili_url, "获取最新的img_key和sub_key", 10, 4, True, bilibili_cookie):
        resp.raise_for_status()
        json_content = resp.json()
        img_url: str = json_content['data']['wbi_img']['img_url']
        sub_url: str = json_content['data']['wbi_img']['sub_url']
        img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
        return img_key, sub_key
    else:
        return "", ""

# 生成Netscape_HTTP_Cookie模块
def bulid_Netscape_HTTP_Cookie(file_name, cookie={}):
    cookie_jar = f'''# Netscape HTTP Cookie File
# This file is generated by yt-dlp.  Do not edit.

.bilibili.com	TRUE	/	FALSE	0	SESSDATA	{cookie.get("SESSDATA", "")}
.bilibili.com	TRUE	/	FALSE	0	bili_jct	{cookie.get("bili_jct", "")}
.bilibili.com	TRUE	/	FALSE	0	DedeUserID	{cookie.get("DedeUserID", "")}
.bilibili.com	TRUE	/	FALSE	0	DedeUserID__ckMd5	{cookie.get("DedeUserID__ckMd5", "")}
.bilibili.com	TRUE	/	FALSE	0	sid	{cookie.get("sid", "")}
.bilibili.com	TRUE	/	FALSE	0	buvid3	{cookie.get("buvid3", "")}
.bilibili.com	TRUE	/	FALSE	0	b_nut	{cookie.get("b_nut", "")}
'''
    file_save(cookie_jar, f"{file_name}.txt")

# 申请哔哩哔哩二维码并获取token和URL模块
def bilibili_request_qr_code():
    # 实际申请二维码的API请求
    response = http_client('https://passport.bilibili.com/x/passport-login/web/qrcode/generate', '申请BiliBili二维码', 3, 5, True)
    data = response.json()
    return data['data']['qrcode_key'], data['data']['url']

# 扫码登录哔哩哔哩并返回状态和cookie模块
def bilibili_scan_login(token):
    # 发送GET请求
    response = http_client('https://passport.bilibili.com/x/passport-login/web/qrcode/poll', '', 1, 1, True, None, {'qrcode_key': token})
    if response:
        data = response.json()
        cookies = response.cookies
        return data['data']['code'], cookies, data['data']['refresh_token']
    else:
        return None, None, None

# 登陆哔哩哔哩模块
def bilibili_login():
    buvid3_and_bnut = http_client("https://www.bilibili.com", "哔哩哔哩主页", 10, 4, True).cookies.get_dict()
    token, url = bilibili_request_qr_code()
    print(f"{datetime.now().strftime('%H:%M:%S')}|请用BiliBili App扫描登录:")
    upward = qr_code(url)
    login_status_change = ""
    time_print = f"{datetime.now().strftime('%H:%M:%S')}|BiliBili "
    while True:
        status, cookie, refresh_token = bilibili_scan_login(token)
        if status == 86101:
            login_status = '\033[0m未扫描\033[0m'
        elif status == 86038:
            login_status = '\033[31m二维码超时, 请重试\033[0m'
        elif status == 86090:
            login_status = '\033[32m扫描成功\033[0m'
        elif status == 0:
            login_status = '\033[32m登陆成功\033[0m'
        if login_status_change != login_status:
            if login_status == '':
                print(f"{time_print}{login_status}".ljust(42), end = "")
            else:
                print(f"\r{time_print}{login_status}".ljust(42), end = "")
        login_status_change = login_status
        if status == 86038:
            print("")
            return status, refresh_token, upward
        elif status == 0:
            print("")
            cookie["buvid3"] = buvid3_and_bnut.get("buvid3", "")
            cookie["b_nut"] = buvid3_and_bnut.get("b_nut", "")
            return cookie, refresh_token, upward
        time.sleep(1)

# 保存哔哩哔哩登陆成功后的cookies模块
def save_bilibili_cookies():
    bilibili_cookie, refresh_token, upward = bilibili_login()
    if bilibili_cookie == 86038:
        return {"cookie": None}, upward
    else:
        bilibili_cookie = requests.utils.dict_from_cookiejar(bilibili_cookie)
        bilibili_data = {
            "cookie": bilibili_cookie,
            "refresh_token": refresh_token
        }
        bulid_Netscape_HTTP_Cookie("yt_dlp_bilibili", bilibili_cookie)
        return bilibili_data, upward

# 检查哔哩哔哩是否需要刷新模块
def judgment_bilibili_update(cookies):
    url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
    response = http_client(url, 'BiliBili刷新判断', 3, 5, True, cookies)
    response = response.json()
    if response["code"] == 0:
        return response["code"], response["data"]["refresh"]
    else:
        return response["code"], None

# 哔哩哔哩cookie刷新模块
def bilibili_cookie_update(bilibili_data):
    bilibili_cookie = bilibili_data["cookie"]
    # 获取refresh_csrf
    key = RSA.importKey('''\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----''')
    # 生成CorrespondPath模块
    def getCorrespondPath(ts):
        cipher = PKCS1_OAEP.new(key, SHA256)
        encrypted = cipher.encrypt(f'refresh_{ts}'.encode())
        return binascii.b2a_hex(encrypted).decode()
    # 获取当前时间戳
    ts = time_stamp()
    # 获取refresh_csrf
    refresh_csrf_response = http_client(f"https://www.bilibili.com/correspond/1/{getCorrespondPath(ts)}", '获取refresh_csrf', 3, 5, True, bilibili_cookie)
    if refresh_csrf_match:= re.search(r'<div id="1-name">(.+?)</div>', refresh_csrf_response.text):
        refresh_csrf_value = refresh_csrf_match[1]
    else:
        return {"cookie": None}
    # 更新bilibili_cookie
    update_cookie_url = 'https://passport.bilibili.com/x/passport-login/web/cookie/refresh'
    update_cookie_data = {
        'csrf': bilibili_cookie["bili_jct"],
        'refresh_csrf': refresh_csrf_value,
        'source': 'main_web',
        'refresh_token': bilibili_data["refresh_token"]
    }
    update_cookie_response = http_client(update_cookie_url, '更新BiliBili_cookie', 3, 5, True, bilibili_cookie, update_cookie_data, "post")
    if update_cookie_response.json()["code"] == 0:
        new_bilibili_cookie = requests.utils.dict_from_cookiejar(update_cookie_response.cookies)
        new_refresh_token = update_cookie_response.json()["data"]["refresh_token"]
    else:
        return {"cookie": None}
    # 确认更新bilibili_cookie
    confirm_cookie_url = 'https://passport.bilibili.com/x/passport-login/web/confirm/refresh'
    confirm_cookie_data = {
        'csrf': new_bilibili_cookie["bili_jct"],
        'refresh_token': bilibili_data["refresh_token"]
    }
    confirm_cookie_response = http_client(confirm_cookie_url, '确认更新BiliBili_cookie', 3, 5, True, new_bilibili_cookie, confirm_cookie_data, "post")
    if confirm_cookie_response.json()["code"] == 0:
        new_bilibili_cookie["buvid3"] = bilibili_cookie["buvid3"]
        new_bilibili_cookie["b_nut"] = bilibili_cookie["b_nut"]
        bilibili_data["cookie"] = new_bilibili_cookie
        bilibili_data["refresh_token"] = new_refresh_token
        bulid_Netscape_HTTP_Cookie("yt_dlp_bilibili", new_bilibili_cookie)
        return bilibili_data
    else:
        return {"cookie": None}

# 登陆刷新哔哩哔哩并获取data
def get_bilibili_data(channelid_bilibili_ids):
    if channelid_bilibili_ids:
        try:
            with open('bilibili_data.json', 'r') as file:
                bilibili_data = file.read()
            bilibili_data = json.loads(bilibili_data)
        except Exception:
            bilibili_data = {"cookie":None, "timestamp": 0.0}
        if time.time() - bilibili_data["timestamp"] - 60*60 > 0:
            bilibili_login_code, bilibili_login_refresh_token = judgment_bilibili_update(bilibili_data["cookie"])
            upward = 0
            try_num = 0
            while try_num < 2 and (bilibili_login_code != 0 or bilibili_login_refresh_token is not False):
                if bilibili_login_code != 0:
                    if try_num == 0:
                        print(f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[31m未登陆\033[0m")
                    else:
                        print(f"\033[{upward + 3}F\033[{upward + 3}K{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[31m未登陆, 重试第\033[0m{try_num}\033[31m次\033[0m")
                    bilibili_data, upward = save_bilibili_cookies()
                    try_num += 1
                else:
                    print(f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[33m需刷新\033[0m")
                    bilibili_data = bilibili_cookie_update(bilibili_data)
                    if bilibili_data["cookie"]:
                        print(f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[32m刷新成功\033[0m")
                    else:
                        print(f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[31m刷新失败, 重新登陆\033[0m")
                bilibili_login_code, bilibili_login_refresh_token = judgment_bilibili_update(bilibili_data["cookie"])
            if bilibili_login_code == 0 and bilibili_login_refresh_token is False:
                print(f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[32m获取cookie成功\033[0m")
                img_key, sub_key = getWbiKeys()
                bilibili_data["img_key"] = img_key
                bilibili_data["sub_key"] = sub_key
                bilibili_data["timestamp"] = time.time()
                file_save(bilibili_data, "bilibili_data.json")
                if not os.path.isfile("yt_dlp_bilibili.txt"):
                    bulid_Netscape_HTTP_Cookie("yt_dlp_bilibili", bilibili_data["cookie"])
                return channelid_bilibili_ids, bilibili_data
            else:
                print(f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[31m获取cookie失败\033[0m")
                return {}, {"cookie":None, "timestamp": 0.0}
        else:
            print(f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[33m获取cookie成功\033[0m")
            if not os.path.isfile("yt_dlp_bilibili.txt"):
                bulid_Netscape_HTTP_Cookie("yt_dlp_bilibili", bilibili_data["cookie"])
            return channelid_bilibili_ids, bilibili_data
    else:
        return {}, {"cookie":None, "timestamp": 0.0}

# WBI签名模块
def WBI_signature(params={}, img_key="", sub_key=""):
    mixinKeyEncTab = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]
    def getMixinKey(orig: str):
        '对 imgKey 和 subKey 进行字符顺序打乱编码'
        return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]
    def encWbi(params: dict, img_key: str, sub_key: str):
        '为请求参数进行 wbi 签名'
        mixin_key = getMixinKey(img_key + sub_key)
        curr_time = round(time.time())
        params['wts'] = curr_time                                   # 添加 wts 字段
        params = dict(sorted(params.items()))                       # 按照 key 重排参数
        # 过滤 value 中的 "!'()*" 字符
        params = {
            k: ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
            for k, v 
            in params.items()
        }
        query = urllib.parse.urlencode(params)                      # 序列化参数
        wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
        params['w_rid'] = wbi_sign
        return params
    return encWbi(
        params=params,
        img_key=img_key,
        sub_key=sub_key
    )

# 通过bs4获取html中字典模块
def get_html_dict(url, name, script_label):
    if response:= http_client(url, name):
        html_content = response.text
        # 使用Beautiful Soup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        # 查找对应的 script 标签
        data_script = soup.find('script', string=lambda t: t and script_label in t)
        if data_script:
            try:
                # 使用正则表达式提取 JSON 数据
                pattern = re.compile(r'\{.*\}', re.DOTALL)
                match = pattern.search(data_script.text)
                if match:
                    data_str = match.group()
                    data = json.loads(data_str)
                    return data
            except json.JSONDecodeError:
                None

# 获取文件列表和分P列表
def get_file_list(video_key, video_media="m4a", length=12):
    media = (
        ("m4a", "mp4", "part")
        if video_media == "m4a"
        else ("mp4", "part")
    )
    try:
        content_id = [
            file  # 获取文件名（包括扩展名）
            for file in os.listdir(f"channel_audiovisual/{video_key}")  # 遍历指定目录下的所有文件
            if file.endswith(media)  # 筛选出以 media 结尾的文件
        ]
        content_id_items = []
        items_counts = {}
        for id in content_id:
            if len(id) > length + 4:
                content_id_items.append(id)
            if '.part' in id:
                items_counts[id[:length]] = 0
        content_id_items = [id[:length] for id in content_id_items]
        for id in content_id_items:
            if id not in items_counts:
                qtys = content_id_items.count(id)
                if video_media == "m4a":
                    pattern = re.compile(rf"{id}_[0-9]*\.(m4a|mp4)")
                else:
                    pattern = re.compile(rf"{id}_[0-9]*\.(mp4)")
                if len([item for item in content_id if pattern.search(item)]) == qtys:
                    items_counts[id] = qtys
                else:
                    fail = False
                    for qty in range(qtys):
                        if video_media == "m4a":
                            if f"{id}_p{qty+1}.m4a" not in content_id and f"{id}_p{qty+1}.mp4" not in content_id:
                                fail = True
                        else:
                            if f"{id}_p{qty+1}.mp4" not in content_id:
                                fail = True
                    if fail:
                        items_counts[id] = 0
                    else:
                        items_counts[id] = qtys
        content_id = list_merge_tidy(content_id, [] ,length)
        for id, num in items_counts.copy().items():
            if (num == 1 or num == 0) and id in content_id:
                content_id.remove(id)
                del items_counts[id]
    except Exception:
        content_id = []
        items_counts = {}
    return content_id, items_counts

# 从YouTube播放列表获取更新模块
def get_youtube_html_playlists(youtube_key, youtube_value, guids=[""], direction_forward=True, update_size=20, youtube_content_ytid_original=[]):
    idlist = []
    item = {}
    threads = []
    fail = []
    try:
        if direction_forward:
            videoid_start = guids[0]
        else:
            videoid_start = guids[-1]
    except IndexError:
        videoid_start = ""
    # 获取媒体相关信息模块
    def get_video_item(videoid, youtube_value):
        yt_Initial_Player_Response = get_html_dict(f"https://www.youtube.com/watch?v={videoid}", f"{youtube_value}|{videoid}", "ytInitialPlayerResponse")
        try:
            player_Microformat_Renderer = yt_Initial_Player_Response["microformat"]["playerMicroformatRenderer"]
        except (KeyError, TypeError, IndexError, ValueError):
            player_Microformat_Renderer = {}
            fail.append(videoid)
        if player_Microformat_Renderer:
            try:
                item[videoid]["description"] = player_Microformat_Renderer["description"]["simpleText"]
            except (KeyError, TypeError, IndexError, ValueError):
                item[videoid]["description"] = ""
            item[videoid]["pubDate"] = player_Microformat_Renderer["publishDate"]
            item[videoid]["image"] = player_Microformat_Renderer["thumbnail"]["thumbnails"][0]["url"]
            try:
                fail.remove(videoid)
            except (KeyError, TypeError, IndexError, ValueError):
                pass
    yt_initial_data = get_html_dict(f"https://www.youtube.com/watch?v={videoid_start}&list=UULF{youtube_key[-22:]}", f"{youtube_value} HTML", "ytInitialData")
    try:
        playlists = yt_initial_data['contents']['twoColumnWatchNextResults']['playlist']['playlist']['contents']
        main_title = yt_initial_data['contents']['twoColumnWatchNextResults']['playlist']['playlist']["ownerName"]["simpleText"]
    except (KeyError, TypeError, IndexError, ValueError):
        return None
    if direction_forward or videoid_start == "":
        for playlist in playlists:
            videoid = playlist['playlistPanelVideoRenderer']['videoId']
            if playlist['playlistPanelVideoRenderer']['navigationEndpoint']['watchEndpoint']['index'] == update_size:
                break
            if videoid not in guids:
                title = playlist['playlistPanelVideoRenderer']['title']['simpleText']
                idlist.append(videoid)
                item[videoid] = {
                    "title": title,
                    "yt-dlp": True,
                }
                if videoid in youtube_content_ytid_original:
                    item[videoid]["yt-dlp"] = False
                    item_thread = threading.Thread(target=get_video_item, args=(videoid, youtube_value,))
                    item_thread.start()
                    threads.append(item_thread)
    else:
        reversed_playlists = []
        for playlist in reversed(playlists):
            videoid = playlist['playlistPanelVideoRenderer']['videoId']
            if videoid not in guids:
                reversed_playlists.append(playlist)
            else:
                break
        for playlist in reversed(reversed_playlists[-update_size:]):
            videoid = playlist['playlistPanelVideoRenderer']['videoId']
            title = playlist['playlistPanelVideoRenderer']['title']['simpleText']
            idlist.append(videoid)
            item[videoid] = {
                "title": title,
                "yt-dlp": True,
            }
            if videoid in youtube_content_ytid_original:
                item[videoid]["yt-dlp"] = False
                item_thread = threading.Thread(target=get_video_item, args=(videoid, youtube_value,))
                item_thread.start()
                threads.append(item_thread)
    for thread in threads:
        thread.join()
    for videoid in fail:
        get_video_item(videoid, youtube_value)
    if fail:
        if direction_forward or videoid_start == "":
            for videoid in fail:
                print(f"{datetime.now().strftime('%H:%M:%S')}|{youtube_value}|{videoid} HTML无法更新, 将不获取")
                idlist.remove(videoid)
                del item[videoid]
        else:
            print(f"{datetime.now().strftime('%H:%M:%S')}|{youtube_value} HTML有失败只更新部分")
            index = len(idlist)
            for videoid in fail:
                if videoid in idlist:
                    index = min(idlist.index(videoid), index)
            idlist_fail = idlist[index:]
            idlist = idlist[:index]
            for videoid in idlist_fail:
                idlist.remove(videoid)
    return {"list": idlist, "item": item, "title": main_title}

# 更新Youtube频道xml模块
def youtube_rss_update(youtube_key, youtube_value, pattern_youtube_varys, pattern_youtube404):
    # 获取已下载媒体名称
    youtube_media = (
        ("m4a", "mp4")
        if channelid_youtube[youtube_value]["media"] == "m4a"
        else ("mp4",)
    )
    try:
        youtube_content_ytid_original = [
            os.path.splitext(file)[0]  # 获取文件名（不包括扩展名）
            for file in os.listdir(
                f"channel_audiovisual/{youtube_key}"
            )  # 遍历指定目录下的所有文件
            if file.endswith(youtube_media)  # 筛选出以 youtube_media 结尾的文件
        ]
    except Exception:
        youtube_content_ytid_original = []
    try:
        original_item = xmls_original[youtube_key]
        guids = re.findall(r"(?<=<guid>).+(?=</guid>)", original_item)
    except KeyError:
        guids = []
    # 构建 URL
    youtube_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={youtube_key}"
    youtube_response = http_client(youtube_url, youtube_value)
    youtube_html_playlists = None
    if youtube_response is not None and re.search(pattern_youtube404, youtube_response.text, re.DOTALL):
        for _ in range(3):
            if youtube_html_playlists:= get_youtube_html_playlists(
                youtube_key,
                youtube_value,
                [elem for elem in guids if elem in youtube_content_ytid_original],
                True,
                channelid_youtube[youtube_value]["update_size"],
                youtube_content_ytid_original
            ):
                break
    # 读取原Youtube频道xml文件并判断是否要更新
    try:
        with open(
            f"channel_id/{youtube_key}.txt", "r", encoding="utf-8"
        ) as file:  # 打开文件进行读取
            youtube_content_original = file.read()  # 读取文件内容
            youtube_content_original_clean = vary_replace(pattern_youtube_varys, youtube_content_original)
    except FileNotFoundError:  # 文件不存在
        youtube_content_original = None
        youtube_content_original_clean = None
    if youtube_html_playlists is not None:
        channelid_youtube_rss[youtube_key] = {"content": youtube_html_playlists, "type": "dict"}
        if youtube_html_playlists["item"]:
            channelid_youtube_ids_update[youtube_key] = youtube_value
        youtube_content_ytid = youtube_html_playlists["list"]
    else:
        if youtube_response is not None:
            channelid_youtube_rss[youtube_key] = {"content": youtube_response, "type": "html"}
            youtube_content = youtube_response.text
            youtube_content_clean = vary_replace(pattern_youtube_varys, youtube_content)
            if youtube_content_clean != youtube_content_original_clean and youtube_response:  # 判断是否要更新
                channelid_youtube_ids_update[youtube_key] = youtube_value
        else:
            channelid_youtube_rss[youtube_key] = {"content": youtube_content_original, "type": "text"}
            youtube_content = youtube_content_original
        try:
            youtube_content_ytid = re.findall(
                r"(?<=<id>yt:video:).{11}(?=</id>)", youtube_content
            )
        except TypeError:
            youtube_content_ytid = []
        youtube_content_ytid = youtube_content_ytid[
            : channelid_youtube[youtube_value]["update_size"]
        ]
        youtube_content_new = list_merge_tidy(youtube_content_ytid ,guids)
    if youtube_content_ytid:= [
        exclude
        for exclude in youtube_content_ytid
        if exclude not in youtube_content_ytid_original
    ]:
        channelid_youtube_ids_update[youtube_key] = youtube_value
        youtube_content_ytid_update[youtube_key] = youtube_content_ytid
    # 向后更新
    if channelid_youtube[youtube_value]["BackwardUpdate"] and guids:
        backward_update_size = channelid_youtube[youtube_value]["last_size"] - len(youtube_content_new)
        if backward_update_size > 0:
            for _ in range(3):
                if youtube_html_backward_playlists:= get_youtube_html_playlists(
                    youtube_key,
                    youtube_value,
                    guids,
                    False,
                    min(backward_update_size, channelid_youtube[youtube_value]["BackwardUpdate_size"]),
                    youtube_content_ytid_original
                ):
                    break
            backward_list = youtube_html_backward_playlists["list"]
            for guid in backward_list.copy():
                if guid in youtube_content_new:
                    backward_list.remove(guid)
            if youtube_html_backward_playlists and backward_list:
                channelid_youtube_ids_update[youtube_key] = youtube_value
                channelid_youtube_rss[youtube_key].update({"backward": youtube_html_backward_playlists})
                youtube_content_ytid_backward = []
                for guid in backward_list:
                    if guid not in youtube_content_ytid_original:
                        youtube_content_ytid_backward.append(guid)
                if youtube_content_ytid_backward:
                    youtube_content_ytid_backward_update[youtube_key] = youtube_content_ytid_backward

# 获取bv所有的分P信息模块
def get_bilibili_all_part(bvid, bilibili_value):
    bvid_part = []
    if bvid_response:= http_client(
        "https://api.bilibili.com/x/player/pagelist",
        f"{bilibili_value}|{bvid}",
        10,
        4,
        True,
        None,
        {"bvid": bvid}
    ):
        bvid_json = bvid_response.json()
        bvid_data = bvid_json["data"]
    else:
        bvid_data =[]
    if len(bvid_data) > 1:
        for part in bvid_data:
            bvid_part.append({
                "cid": part["cid"],
                "page": part["page"],
                "part": part["part"],
                "duration": part["duration"],
                "dimension": part["dimension"],
                "first_frame": part["first_frame"],
            })
    bvid_part.sort(key=lambda x: x["page"], reverse=True)
    return bvid_part

# 获取bv所有的互动视频信息模块
def get_bilibili_interactive(bvid, bilibili_value):
    bvid_part = []
    bvid_cid = []
    bvid_cid_choices = []
    if playerso_response:=http_client(
        "https://api.bilibili.com/x/player.so",
        f"{bilibili_value}|{bvid}",
        10,
        4,
        True,
        None,
        {"id": "cid:1", "bvid": bvid}
    ):
        playerso = playerso_response.text
        # 正则表达式
        pattern = re.compile(r'(?<=<interaction>)(.*?)(?=</interaction>)', re.DOTALL)
        match = pattern.search(playerso)
        if match:
            content = match.group(1).strip()
            try:
                data = json.loads(content)
                graph_version = data["graph_version"]
            except json.JSONDecodeError:
                graph_version = ""
    def get_edge_info(bvid, bilibili_value, graph_version, edge_id):
        if edgeinfo_v2_response:=http_client(
            "https://api.bilibili.com/x/stein/edgeinfo_v2",
            f"{bilibili_value}|{bvid}",
            10,
            4,
            True,
            None,
            {"bvid": bvid, "graph_version": graph_version, "edge_id": edge_id}
        ):
            edgeinfo_v2 = edgeinfo_v2_response.json()
            return edgeinfo_v2["data"]
    def get_choices(data):
        options = []
        if "questions" in data["edges"]:
            for question in data["edges"]["questions"]:
                if "choices" in question:
                    for choice in question["choices"]:
                        if choice["cid"] not in bvid_cid and choice["cid"] not in bvid_cid_choices:
                            bvid_cid_choices.append({
                                "cid": choice["cid"],
                                "edge_id": choice["id"],
                                "option": choice["option"],
                            })
                            options.append(choice["option"])
        return options
    if graph_version:
        data_1 = get_edge_info(bvid, bilibili_value, graph_version, "1")
        for story_list in data_1["story_list"]:
            if story_list["edge_id"] == 1:
                story_list_1 = story_list
                break
        bvid_part.append({
            "cid": story_list_1["cid"],
            "title": data_1["title"],
            "edge_id": story_list_1["edge_id"],
            "first_frame": f"http://i0.hdslb.com/bfs/steins-gate/{story_list_1['cid']}_screenshot.jpg",
            "options": get_choices(data_1),
            "num": 1,
        })
        bvid_cid.append(story_list_1["cid"])
        while len(bvid_cid_choices) != 0:
            if bvid_cid_choices[0]["cid"] not in bvid_cid:
                data = get_edge_info(bvid, bilibili_value, graph_version, bvid_cid_choices[0]["edge_id"])
                bvid_part.append({
                    "cid": bvid_cid_choices[0]["cid"],
                    "title": data["title"],
                    "edge_id": bvid_cid_choices[0]["edge_id"],
                    "first_frame": f"http://i0.hdslb.com/bfs/steins-gate/{bvid_cid_choices[0]['cid']}_screenshot.jpg",
                    "options": get_choices(data),
                    "num": len(bvid_part) + 1
                })
                bvid_cid.append(bvid_cid_choices[0]["cid"])
            del bvid_cid_choices[0]
    bvid_part.sort(key=lambda x: x["num"], reverse=True)
    return bvid_part

# 查询哔哩哔哩用户投稿视频明细模块
def get_bilibili_vlist(bilibili_key, bilibili_value, num=1, all_part_judgement=False):
    bilibili_list = []
    bilibili_entry = {}
    if bilibili_response:= http_client(
        "https://api.bilibili.com/x/space/wbi/arc/search",
        bilibili_value,
        10,
        4,
        True,
        bilibili_data["cookie"],
        WBI_signature(
            {
                "mid": bilibili_key,
                "pn": str(num),
                "ps": "25",
            },
            bilibili_data["img_key"],
            bilibili_data["sub_key"],
        )
    ):
        bilibili_json = bilibili_response.json()
        bilibili_vlists = bilibili_json["data"]["list"]["vlist"]
        for vlist in bilibili_vlists:
            try:
                bilibili_entry[vlist["bvid"]] = {
                    "aid": vlist["aid"],
                    "author": vlist["author"],
                    "bvid": vlist["bvid"],
                    "copyright": vlist["copyright"],
                    "created": vlist["created"],
                    "description": vlist["description"],
                    "is_union_video": vlist["is_union_video"],
                    "length": vlist["length"],
                    "mid": vlist["mid"],
                    "pic": vlist["pic"],
                    "title": vlist["title"],
                    "typeid": vlist["typeid"],
                }
                bilibili_list.append(vlist["bvid"])
            except (KeyError, TypeError, IndexError, ValueError):
                pass
    if all_part_judgement and bilibili_list:
        def all_part(bvid):
            if bvid_part:= get_bilibili_all_part(bvid, bilibili_value):
                bilibili_entry[bvid]["part"] = bvid_part
            elif bvid_edgeinfo:= get_bilibili_interactive(bvid, bilibili_value):
                bilibili_entry[bvid]["edgeinfo"] = bvid_edgeinfo
        # 创建一个线程列表
        threads = []
        for bvid in bilibili_list:
            thread = threading.Thread(target=all_part, args=(bvid,))
            threads.append(thread)
            thread.start()
        # 等待所有线程完成
        for thread in threads:
            thread.join()
    return bilibili_entry, bilibili_list

# 更新哔哩哔哩频道json模块
def bilibili_json_update(bilibili_key, bilibili_value):
    bilibili_space = {}
    bilibili_lists = []
    bilibili_entrys = {}
    # 用户名片信息
    if bilibili_card_response:= http_client(
        "https://api.bilibili.com/x/web-interface/card",
        bilibili_value,
        10,
        4,
        True,
        bilibili_data["cookie"],
        {
            "mid": bilibili_key,
            "photo": "true",
        },
    ):
        bilibili_card_json = bilibili_card_response.json()
        try:
            if bilibili_card_json["code"] == 0:
                bilibili_space = {
                    "mid": bilibili_card_json["data"]["card"]["mid"],
                    "name": bilibili_card_json["data"]["card"]["name"],
                    "sex": bilibili_card_json["data"]["card"]["sex"],
                    "face": bilibili_card_json["data"]["card"]["face"],
                    "spacesta": bilibili_card_json["data"]["card"]["spacesta"],
                    "sign": bilibili_card_json["data"]["card"]["sign"],
                    "Official": bilibili_card_json["data"]["card"]["Official"],
                    "official_verify": bilibili_card_json["data"]["card"]["official_verify"],
                }
            else:
                return bilibili_card_json["code"]
        except (KeyError, TypeError, IndexError, ValueError):
            pass
    else:
        return None
    # 查询哔哩哔哩用户投稿视频明细
    for num in range(math.ceil(channelid_bilibili[bilibili_value]["update_size"] / 25)):
        num += 1
        bilibili_entry, bilibili_list = get_bilibili_vlist(
            bilibili_key,
            f"{bilibili_value}第{num}页",
            num,
            channelid_bilibili[bilibili_value]["AllPartGet"]
        )
        bilibili_entrys = bilibili_entrys | bilibili_entry
        bilibili_lists += bilibili_list
    bilibili_space["entry"] = bilibili_entrys
    bilibili_space["list"] = bilibili_lists
    return bilibili_space

# 更新哔哩哔哩频道xml模块
def bilibili_rss_update(bilibili_key, bilibili_value):
    # 获取已下载文件列表
    bilibili_content_bvid_original = get_file_list(bilibili_key, channelid_bilibili[bilibili_value]["media"])[0]
    # 获取原xml中文件列表
    try:
        original_item = xmls_original[bilibili_key]
        guids = list_merge_tidy(re.findall(r"(?<=<guid>).+(?=</guid>)", original_item), [], 12)
    except KeyError:
        guids = []
    bilibili_space = bilibili_json_update(bilibili_key, bilibili_value)
    # 读取原哔哩哔哩频道xml文件并判断是否要更新
    try:
        with open(
            f"channel_id/{bilibili_key}.json", "r", encoding="utf-8"
        ) as file:  # 打开文件进行读取
            bilibili_space_original = json.load(file)  # 读取文件内容
    except FileNotFoundError:  # 文件不存在
        bilibili_space_original = {}
    if bilibili_space == -404:
        channelid_bilibili_rss[bilibili_key] = {"content": bilibili_space, "type": "int"}
    elif bilibili_space is None:
        channelid_bilibili_rss[bilibili_key] = {"content": bilibili_space_original, "type": "json"}
    else:
        channelid_bilibili_rss[bilibili_key] = {"content": bilibili_space, "type": "dict"}
        if bilibili_space != bilibili_space_original:
            channelid_bilibili_ids_update[bilibili_key] = bilibili_value
        bilibili_content_bvid = bilibili_space["list"][:channelid_bilibili[bilibili_value]["update_size"]]
        bilibili_space_new = list_merge_tidy(bilibili_content_bvid ,guids)
        if bilibili_content_bvid:= [
            exclude
            for exclude in bilibili_content_bvid
            if exclude not in bilibili_content_bvid_original
        ]:
            channelid_bilibili_ids_update[bilibili_key] = bilibili_value
            bilibili_content_bvid_update[bilibili_key] = bilibili_content_bvid
        # 向后更新
        if channelid_bilibili[bilibili_value]["BackwardUpdate"] and guids:
            backward_update_size = channelid_bilibili[bilibili_value]["last_size"] - len(bilibili_space_new)
            if backward_update_size > 0:
                backward_update_size = min(backward_update_size, channelid_bilibili[bilibili_value]["BackwardUpdate_size"])
                backward_update_page_start = math.ceil(len(bilibili_space_new) / 25)
                backward_update_page_end = math.ceil((len(bilibili_space_new) + backward_update_size) / 25)
                backward_entry = {}
                backward_list = []
                for num in range(backward_update_page_start, backward_update_page_end + 1):
                    backward_entry_part, backward_list_part = get_bilibili_vlist(bilibili_key, bilibili_value, num)
                    backward_entry = backward_entry | backward_entry_part
                    backward_list += backward_list_part
                if backward_entry and backward_list and guids[-1] in backward_list:
                    try:
                        backward_list_start = backward_list.index(guids[-1]) + 1
                        backward_list = backward_list[backward_list_start:][:backward_update_size]
                    except ValueError:
                        backward_list = []
                    for guid in backward_list.copy():
                        if guid in bilibili_space_new:
                            backward_list.remove(guid)
                    if backward_list:
                        if channelid_bilibili[bilibili_value]["AllPartGet"]:
                            def backward_all_part(guid):
                                if guid_part:= get_bilibili_all_part(guid, bilibili_value):
                                    backward_entry[guid]["part"] = guid_part
                                elif guid_edgeinfos:= get_bilibili_interactive(guid, bilibili_value):
                                    backward_entry[guid]["edgeinfo"] = guid_edgeinfos
                            # 创建一个线程列表
                            threads = []
                            for guid in backward_entry:
                                thread = threading.Thread(target=backward_all_part, args=(guid,))
                                threads.append(thread)
                                thread.start()
                            # 等待所有线程完成
                            for thread in threads:
                                thread.join()
                        channelid_bilibili_rss[bilibili_key].update({"backward": {"list": backward_list, "entry": backward_entry}})
                        channelid_bilibili_ids_update[bilibili_key] = bilibili_value
                        bilibili_content_bvid_backward = []
                        for guid in backward_list:
                            if guid not in bilibili_content_bvid_original:
                                bilibili_content_bvid_backward.append(guid)
                        if bilibili_content_bvid_backward:
                            bilibili_content_bvid_backward_update[bilibili_key] = bilibili_content_bvid_backward

# 更新Youtube和哔哩哔哩频道xml多线程模块
def update_youtube_bilibili_rss():
    pattern_youtube404 = r"Error 404 \(Not Found\)"  # 设置要匹配的正则表达式模式
    pattern_youtube_varys = [
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-2][0-9]:[0-6][0-9]:[0-6][0-9]\+00:00",
        r'starRating count="[0-9]*"',
        r'statistics views="[0-9]*"',
        r"<id>yt:channel:(UC)?(.{22})?</id>",
        r"<yt:channelId>(UC)?(.{22})?</yt:channelId>",
    ]
    youtube_bilibili_rss_update_threads = []  # 创建线程列表
    # Youtube多线程
    for youtube_key, youtube_value in channelid_youtube_ids.items():
        thread = threading.Thread(
            target=youtube_rss_update, args=(youtube_key, youtube_value, pattern_youtube_varys, pattern_youtube404)
        )
        youtube_bilibili_rss_update_threads.append(thread)
        # 开始多线程
        thread.start()
    # 哔哩哔哩多线程
    for bilibili_key, bilibili_value in channelid_bilibili_ids.items():
        thread = threading.Thread(
            target=bilibili_rss_update, args=(bilibili_key, bilibili_value)
        )
        youtube_bilibili_rss_update_threads.append(thread)
        # 开始多线程
        thread.start()
    # 等待所有线程完成
    for thread in youtube_bilibili_rss_update_threads:
        thread.join()
    # 更新Youtube频道
    for youtube_key, youtube_value in channelid_youtube_ids.copy().items():
        youtube_response = channelid_youtube_rss[youtube_key]["content"]
        youtube_response_type = channelid_youtube_rss[youtube_key]["type"]
        # xml分类及存储
        if youtube_response is not None:
            if youtube_response_type ==  "dict":
                # 构建频道文件夹
                folder_build(youtube_key, "channel_audiovisual")
            else:
                if youtube_response_type ==  "html":
                    youtube_content = youtube_response.text
                elif youtube_response_type ==  "text":
                    youtube_content = youtube_response
                    write_log(f"YouTube频道 {youtube_value} 无法更新")
                # 判断频道id是否正确
                if re.search(pattern_youtube404, youtube_content, re.DOTALL):
                    del channelid_youtube_ids[youtube_key]  # 删除错误ID
                    write_log(f"YouTube频道 {youtube_value} ID不正确无法获取")
                else:
                    # 构建文件
                    file_save(youtube_content, f"{youtube_key}.txt", "channel_id")
                    # 构建频道文件夹
                    folder_build(youtube_key, "channel_audiovisual")
        else:
            if youtube_response_type == "text":
                del channelid_youtube_ids[youtube_key]
            write_log(f"YouTube频道 {youtube_value} 无法更新")
    # 更新哔哩哔哩频道
    for bilibili_key, bilibili_value in channelid_bilibili_ids.copy().items():
        bilibili_space = channelid_bilibili_rss[bilibili_key]["content"]
        bilibili_space_type = channelid_bilibili_rss[bilibili_key]["type"]
        # xml分类及存储
        if bilibili_space_type == "int":
            del channelid_bilibili_ids[bilibili_key]  # 删除错误ID
            write_log(f"BiliBili频道 {bilibili_value} ID不正确无法获取")
        elif bilibili_space_type == "json":
            write_log(f"BiliBili频道 {youtube_value} 无法更新")
            if bilibili_space == {}:
                del channelid_bilibili_ids[bilibili_key]
        else:
            # 构建文件
            file_save(bilibili_space, f"{bilibili_key}.json", "channel_id")
            # 构建频道文件夹
            folder_build(bilibili_key, "channel_audiovisual")

# 输出需要更新的信息模块
def update_information_display(channelid_ids_update, content_id_update, content_id_backward_update, name):
    if channelid_ids_update:
        print_channelid_ids_update = f"需更新的{name}频道:\n"
        # 获取命令行字节宽度
        try:
            terminal_width = os.get_terminal_size().columns
        except OSError:
            terminal_width = 47
        # 尝试拆分输出
        try:
            for channelid_key, channelid_value in channelid_ids_update.items():
                if len(print_channelid_ids_update) != len(name) + 8:
                    if (
                        len(
                            re.sub(
                                r"\033\[[0-9;]+m",
                                "",
                                print_channelid_ids_update.split("\n")[-1],
                            ).encode("GBK")
                        )
                        + len(f" | {channelid_value}".encode("utf-8"))
                        <= terminal_width
                    ):
                        print_channelid_ids_update += " | "
                    else:
                        print_channelid_ids_update += "\n"
                if channelid_key in content_id_update and channelid_key in content_id_backward_update:
                    print_channelid_ids_update += (
                        f"\033[34m{channelid_value}\033[0m"
                    )
                elif channelid_key in content_id_update:
                    print_channelid_ids_update += (
                        f"\033[32m{channelid_value}\033[0m"
                    )
                elif channelid_key in content_id_backward_update:
                    print_channelid_ids_update += (
                        f"\033[36m{channelid_value}\033[0m"
                    )
                else:
                    print_channelid_ids_update += (
                        f"\033[33m{channelid_value}\033[0m"
                    )
        # 如果含有特殊字符将使用此输出
        except Exception:
            len_channelid_ids_update = len(channelid_ids_update)
            count_channelid_ids_update = 1
            for channelid_key, channelid_value in channelid_ids_update.items():
                if channelid_key in content_id_update and channelid_key in content_id_backward_update:
                    print_channelid_ids_update += (
                        f"\033[34m{channelid_value}\033[0m"
                    )
                elif channelid_key in content_id_update:
                    print_channelid_ids_update += (
                        f"\033[32m{channelid_value}\033[0m"
                    )
                elif channelid_key in content_id_backward_update:
                    print_channelid_ids_update += (
                        f"\033[36m{channelid_value}\033[0m"
                    )
                else:
                    print_channelid_ids_update += (
                        f"\033[33m{channelid_value}\033[0m"
                    )
                if count_channelid_ids_update != len_channelid_ids_update:
                    if count_channelid_ids_update % 2 != 0:
                        print_channelid_ids_update += " | "
                    else:
                        print_channelid_ids_update += "\n"
                    count_channelid_ids_update += 1
        write_log(print_channelid_ids_update)

# YouTube&哔哩哔哩视频信息模块
def get_youtube_and_bilibili_video_format(id, stop_flag, video_format_lock, prepare_animation):
    id_update_format = media_format(
        video_id_update_format[id]["url"],
        id,
        video_id_update_format[id]["media"],
        video_id_update_format[id]["quality"],
        video_id_update_format[id]["cookie"],
    )
    if isinstance(id_update_format, list):
        if len(id_update_format) == 1:
            entry_id_update_format = id_update_format[0]
            video_id_update_format[id]["url"] = entry_id_update_format["url"]
            video_id_update_format[id]["format"] = entry_id_update_format["duration_and_id"]
            video_id_update_format[id]["title"] = entry_id_update_format["title"]
            video_id_update_format[id]["timestamp"] = entry_id_update_format["timestamp"]
            video_id_update_format[id]["description"] = entry_id_update_format["description"]
            video_id_update_format[id]["main"] = id
            video_id_update_format[id]["image"] = entry_id_update_format["image"]
            video_id_update_format[id]["download"] = entry_id_update_format["download"]
        else:
            entrys_id = []
            for entry_id_update_format in id_update_format:
                entry_id = entry_id_update_format["id"]
                entrys_id.append(entry_id)
                video_id_update_format[entry_id] = {
                    "id": video_id_update_format[id]["id"],
                    "media": video_id_update_format[id]["media"],
                    "quality": video_id_update_format[id]["quality"],
                    "url": entry_id_update_format["url"],
                    "name": video_id_update_format[id]["name"],
                    "cookie": video_id_update_format[id]["cookie"],
                    "format": entry_id_update_format["duration_and_id"],
                    "title": entry_id_update_format["title"],
                    "timestamp": entry_id_update_format["timestamp"],
                    "description": entry_id_update_format["description"],
                    "main": id,
                    "image": entry_id_update_format["image"],
                    "download": entry_id_update_format["download"],
                }
            video_id_update_format[id] = entrys_id
    else:
        with video_format_lock:
            stop_flag[0] = "error"
            prepare_animation.join()
            video_id_failed.append(id)
            write_log(
                f"{video_id_update_format[id]['name']}|{id}|{id_update_format}",
                None,
                True,
                False,
            )
            del video_id_update_format[id]

# YouTube&哔哩哔哩获取视频信息多线程模块
def get_youtube_and_bilibili_video_format_multithreading(video_id_update_format_item, wait_animation_display_info):
    # 创建共享的标志变量
    stop_flag = ["keep"]  # 使用列表来存储标志变量
    # 创建两个线程分别运行等待动画和其他代码，并传递共享的标志变量
    prepare_animation = threading.Thread(target=wait_animation, args=(stop_flag, wait_animation_display_info,))
    # 启动动画线程
    prepare_animation.start()
    # 创建线程锁
    video_format_lock = threading.Lock()
    # 创建线程列表
    video_id_update_threads = []
    for video_id in video_id_update_format_item.keys():
        thread = threading.Thread(target=get_youtube_and_bilibili_video_format, args=(video_id, stop_flag, video_format_lock, prepare_animation))
        video_id_update_threads.append(thread)
        thread.start()
    # 等待所有线程完成
    for thread in video_id_update_threads:
        thread.join()
    stop_flag[0] = "end"
    prepare_animation.join()

# 获取YouTube&哔哩哔哩视频格式信息模块
def get_video_format():
    def get_youtube_format_front(ytid_content_update):
        for ytid_key, ytid_value in ytid_content_update.items():
            # 获取对应文件类型
            yt_id_file = channelid_youtube[channelid_youtube_ids_update[ytid_key]]["media"]
            # 如果为视频格式获取分辨率
            if yt_id_file == "mp4":
                yt_id_quality = channelid_youtube[channelid_youtube_ids_update[ytid_key]][
                    "quality"
                ]
            else:
                yt_id_quality = None
            for yt_id in ytid_value:
                yt_id_format = {
                    "id": ytid_key,
                    "media": yt_id_file,
                    "quality": yt_id_quality,
                    "url": f"https://www.youtube.com/watch?v={yt_id}",
                    "name": channelid_youtube_ids[ytid_key],
                    "cookie": None,
                }
                video_id_update_format[yt_id] = yt_id_format
    def get_bilibili_format_front(bvid_content_update):
        for bvid_key, bvid_value in bvid_content_update.items():
            # 获取对应文件类型
            bv_id_file = channelid_bilibili[channelid_bilibili_ids_update[bvid_key]]["media"]
            # 如果为视频格式获取分辨率
            if bv_id_file == "mp4":
                bv_id_quality = channelid_bilibili[channelid_bilibili_ids_update[bvid_key]][
                    "quality"
                ]
            else:
                bv_id_quality = None
            for bv_id in bvid_value:
                bv_id_format = {
                    "id": bvid_key,
                    "media": bv_id_file,
                    "quality": bv_id_quality,
                    "url": f"https://www.bilibili.com/video/{bv_id}",
                    "name": channelid_bilibili_ids[bvid_key],
                    "cookie": "yt_dlp_bilibili.txt",
                }
                video_id_update_format[bv_id] = bv_id_format
    get_youtube_format_front(youtube_content_ytid_update)
    get_bilibili_format_front(bilibili_content_bvid_update)
    get_youtube_format_front(youtube_content_ytid_backward_update)
    get_bilibili_format_front(bilibili_content_bvid_backward_update)
    # 按参数拆分获取量
    if len(video_id_update_format) != 0:
        video_id_update_format_list = split_dict(video_id_update_format, config["preparation_per_count"])
        wait_animation_num = 1
        for video_id_update_format_item in video_id_update_format_list:
            if len(video_id_update_format_list) == 1:
                wait_animation_display_info = "媒体视频 "
            else:
                wait_animation_display_info = f"媒体视频|No.{str(wait_animation_num).zfill(2)} "
            wait_animation_num += 1
            # 获取视频信息多线程模块
            get_youtube_and_bilibili_video_format_multithreading(video_id_update_format_item, wait_animation_display_info)

# 下载YouTube和哔哩哔哩视频
def youtube_and_bilibili_download():
    for video_id in video_id_update_format.keys():
        if isinstance(video_id_update_format[video_id], dict) and video_id_update_format[video_id]["main"] not in video_id_failed:
            if dl_aideo_video(
                video_id,
                video_id_update_format[video_id]["id"],
                video_id_update_format[video_id]["media"],
                video_id_update_format[video_id]["format"],
                config["retry_count"],
                video_id_update_format[video_id]["download"]["url"],
                video_id_update_format[video_id]["name"],
                video_id_update_format[video_id]["cookie"],
                video_id_update_format[video_id]["download"]["num"]
            ):
                video_id_failed.append(video_id_update_format[video_id]["main"])
                write_log(
                    f"{video_id_update_format[video_id]['name']}|{video_id} \033[31m无法下载\033[0m"
                )

# 生成XML模块
def xml_rss(title, link, description, category, icon, items):
    # 获取当前时间
    current_time_now = time.time()  # 获取当前时间的秒数
    # 获取当前时区和夏令时信息
    time_info_now = time.localtime(current_time_now)
    # 构造时间字符串
    formatted_time_now = time.strftime("%a, %d %b %Y %H:%M:%S %z", time_info_now)
    itunes_summary = description.replace("\n", "&#xA;")
    if title == "Podflow":
        author = "gruel-zxz"
        subtitle = "gruel-zxz-podflow"
    else:
        author = title
        subtitle = title
    # 创建主XML信息
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
    <channel>
        <title>{title}</title>
        <link>{link}</link>
        <description>{description}</description>
        <category>{category}</category>
        <generator>Podflow (support us at https://github.com/gruel-zxz/podflow)</generator>
        <language>en-us</language>
        <lastBuildDate>{formatted_time_now}</lastBuildDate>
        <pubDate>Sun, 24 Apr 2005 11:20:54 +0800</pubDate>
        <image>
            <url>{icon}</url>
            <title>{title}</title>
            <link>{link}</link>
        </image>
        <itunes:author>{author}</itunes:author>
        <itunes:subtitle>{subtitle}</itunes:subtitle>
        <itunes:summary><![CDATA[{itunes_summary}]]></itunes:summary>
        <itunes:image href="{icon}"></itunes:image>
        <itunes:explicit>no</itunes:explicit>
        <itunes:category text="{category}"></itunes:category>
{items}
    </channel>
</rss>"""

# 生成item模块
def xml_item(
    video_url,
    output_dir,
    video_website,
    channelid_title,
    title,
    description,
    pubDate,
    image,
):
    channelid_title = html.escape(channelid_title)
    # 查看标题中是否有频道名称如无添加到描述中并去除空字符
    title = title.replace('\x00', '')
    if channelid_title not in title:
        if description == "":
            description = f"『{channelid_title}』{description}"
        else:
            description = f"『{channelid_title}』\n{description}".replace('\x00', '')
    # 更换描述换行符
    replacement_description = description.replace("\n", "&#xA;")
    # 获取文件后缀和文件字节大小
    if os.path.exists(f"channel_audiovisual/{output_dir}/{video_url}.mp4"):
        video_length_bytes = os.path.getsize(
            f"channel_audiovisual/{output_dir}/{video_url}.mp4"
        )
        output_format = "mp4"
        video_type = "video/mp4"
    else:
        if os.path.exists(f"channel_audiovisual/{output_dir}/{video_url}.m4a"):
            video_length_bytes = os.path.getsize(
                f"channel_audiovisual/{output_dir}/{video_url}.m4a"
            )
        else:
            video_length_bytes = 0
        output_format = "m4a"
        video_type = "audio/x-m4a"
    # 获取文件时长
    duration = time_format(
        get_duration_ffmpeg(
            f"channel_audiovisual/{output_dir}/{video_url}.{output_format}"
        )
    )
    # 回显对应的item
    return f"""
        <item>
            <guid>{video_url}</guid>
            <title>{title}</title>
            <link>{video_website}</link>
            <description>{replacement_description}</description>
            <pubDate>{pubDate}</pubDate>
            <enclosure url="{config["url"]}/channel_audiovisual/{output_dir}/{video_url}.{output_format}" length="{video_length_bytes}" type="{video_type}"></enclosure>
            <itunes:author>{title}</itunes:author>
            <itunes:subtitle>{title}</itunes:subtitle>
            <itunes:summary><![CDATA[{description}]]></itunes:summary>
            <itunes:image href="{image}"></itunes:image>
            <itunes:duration>{duration}</itunes:duration>
            <itunes:explicit>no</itunes:explicit>
            <itunes:order>1</itunes:order>
        </item>
"""

# 格式化时间加时区模块
def format_time(time_str):
    original_tz = timezone.utc  # 原始时区为UTC
    # 解析时间字符串并转换为datetime对象
    dt = datetime.fromisoformat(time_str[:-6] if time_str[-3] == ":" else time_str[:-5]).replace(tzinfo=original_tz)
    # 转换为目标时区
    if time_str[-3] == ":":
        tz = timedelta(hours=int(time_str[-6:-3]),minutes=int(f"{time_str[-6]}{time_str[-2:]}"))
    else:
        tz = timedelta(hours=int(time_str[-5:-2]),minutes=int(f"{time_str[-5]}{time_str[-2:]}"))
    dt -= tz
    target_tz = timezone(timedelta(seconds=-(time.timezone + time.daylight)))
    dt_target = dt.astimezone(target_tz)
    # 格式化为目标时间字符串
    target_format = "%a, %d %b %Y %H:%M:%S %z"
    pubDate = dt_target.strftime(target_format)
    return pubDate

# 生成YouTube的item模块
def youtube_xml_item(entry):
    # 输入时间字符串和原始时区
    time_str = re.search(r"(?<=<published>).+(?=</published>)", entry).group()
    pubDate = format_time(time_str)
    output_dir = re.search(r"(?<=<yt:channelId>).+(?=</yt:channelId>)", entry).group()
    description = re.search(
        r"(?<=<media:description>).+(?=</media:description>)",
        re.sub(r"\n+", "\n", entry),
        flags=re.DOTALL,
    )
    description = description.group() if description else ""
    id = re.search(r"(?<=<yt:videoId>).+(?=</yt:videoId>)", entry).group()
    return xml_item(
        id,
        output_dir,
        f"https://youtube.com/watch?v={id}",
        channelid_youtube[channelid_youtube_ids[output_dir]]["title"],
        re.search(r"(?<=<title>).+(?=</title>)", entry).group(),
        description,
        pubDate,
        re.search(r"(?<=<media:thumbnail url=\").+(?=\" width=\")", entry).group(),
    )

# 生成原有的item模块
def xml_original_item(original_item):
    guid = re.search(r"(?<=<guid>).+(?=</guid>)", original_item).group()
    title = re.search(r"(?<=<title>).+(?=</title>)", original_item).group()
    link = re.search(r"(?<=<link>).+(?=</link>)", original_item).group()
    description = re.search(r"(?<=<description>).+(?=</description>)", original_item)
    description = description.group() if description else ""
    pubDate = re.search(r"(?<=<pubDate>).+(?=</pubDate>)", original_item).group()
    url = re.search(r"(?<=<enclosure url\=\").+?(?=\")", original_item).group()
    url = re.search(r"(?<=/channel_audiovisual/).+/.+\.(m4a|mp4)", url).group()
    url = f"{config['url']}/channel_audiovisual/{url}"
    length = re.search(r"(?<=length\=\")[0-9]+(?=\")", original_item).group()
    type_video = re.search(
        r"(?<=type\=\")(video/mp4|audio/x-m4a|audio/mpeg)(?=\")", original_item
    ).group()
    if type_video == "audio/mpeg":
        type_video = "audio/x-m4a"
    itunes_author = re.search(
        r"(?<=<itunes:author>).+(?=</itunes:author>)", original_item
    ).group()
    itunes_subtitle = re.search(
        r"(?<=<itunes:subtitle>).+(?=</itunes:subtitle>)", original_item
    ).group()
    itunes_summary = re.search(
        r"(?<=<itunes:summary><\!\[CDATA\[).+(?=\]\]></itunes:summary>)",
        original_item,
        flags=re.DOTALL,
    )
    itunes_summary = itunes_summary.group() if itunes_summary else ""
    itunes_image = re.search(
        r"(?<=<itunes:image href\=\").+(?=\"></itunes:image>)", original_item
    )
    itunes_image = itunes_image.group() if itunes_image else ""
    itunes_duration = re.search(
        r"(?<=<itunes:duration>).+(?=</itunes:duration>)", original_item
    ).group()
    itunes_explicit = re.search(
        r"(?<=<itunes:explicit>).+(?=</itunes:explicit>)", original_item
    ).group()
    itunes_order = re.search(
        r"(?<=<itunes:order>).+(?=</itunes:order>)", original_item
    ).group()
    return f"""
        <item>
            <guid>{guid}</guid>
            <title>{title}</title>
            <link>{link}</link>
            <description>{description}</description>
            <pubDate>{pubDate}</pubDate>
            <enclosure url="{url}" length="{length}" type="{type_video}"></enclosure>
            <itunes:author>{itunes_author}</itunes:author>
            <itunes:subtitle>{itunes_subtitle}</itunes:subtitle>
            <itunes:summary><![CDATA[{itunes_summary}]]></itunes:summary>
            <itunes:image href="{itunes_image}"></itunes:image>
            <itunes:duration>{itunes_duration}</itunes:duration>
            <itunes:explicit>{itunes_explicit}</itunes:explicit>
            <itunes:order>{itunes_order}</itunes:order>
        </item>
"""

# 生成哈希值模块
def create_hash(data):
    data_str = str(data)
    hash_object = hashlib.sha256()
    hash_object.update(data_str.encode())
    hash_value = hash_object.hexdigest()
    return hash_value

# rss生成哈希值模块
def rss_create_hash(data):
    patterns = [
        r"<lastBuildDate>(\w+), (\d{2}) (\w+) (\d{4}) (\d{2}):(\d{2}):(\d{2}) \+\d{4}</lastBuildDate>",
        r"Podflow_light\.png",
        r"Podflow_dark\.png"
    ]
    replacement = ""
    for pattern in patterns:
        data = re.sub(pattern, replacement, data)
    hash_value = create_hash(data)
    return hash_value

# 获取原始xml模块
def get_original_rss():
    xmls_original_fail =[]
    # 获取原始总xml文件
    try:
        with open(f"{config['filename']}.xml", "r", encoding="utf-8") as file:  # 打开文件进行读取
            rss_original = file.read()  # 读取文件内容
            get_xmls_original = {
                rss_original_channel: rss_original.split(
                    f"<!-- {{{rss_original_channel}}} -->\n"
                )[1]
                for rss_original_channel in list(
                    set(re.findall(r"(?<=<!-- \{).+?(?=\} -->)", rss_original))
                )
            }
    except FileNotFoundError:  # 文件不存在直接更新
        get_xmls_original = {}
        rss_original = ""
    # 如原始xml无对应的原频道items, 将尝试从对应频道的xml中获取
    for channelid_key in (channelid_youtube_ids | channelid_bilibili_ids).keys():
        if channelid_key not in get_xmls_original.keys():
            try:
                with open(
                    f"channel_rss/{channelid_key}.xml", "r", encoding="utf-8"
                ) as file:  # 打开文件进行读取
                    youtube_rss_original = file.read()  # 读取文件内容
                    get_xmls_original[channelid_key] = youtube_rss_original.split(
                        f"<!-- {{{channelid_key}}} -->\n"
                    )[1]
            except FileNotFoundError:  # 文件不存在直接更新
                xmls_original_fail.append(channelid_key)
    # 生成原始rss的哈希值
    hash_rss_original = rss_create_hash(rss_original)
    return get_xmls_original, hash_rss_original, xmls_original_fail

# 打印无法保留原节目信息模块
def original_rss_fail_print(xmls_original_fail):
    for item in xmls_original_fail:
        if item in (channelid_youtube_ids | channelid_bilibili_ids).keys():
            write_log(f"RSS文件中不存在 {(channelid_youtube_ids | channelid_bilibili_ids)[item]} 无法保留原节目")

# 获取YouTube频道简介模块
def get_youtube_introduction():
    # 创建线程锁
    youtube_xml_get_lock = threading.Lock()
    # 使用http获取youtube频道简介和图标模块
    def youtube_xml_get(output_dir):
        if channel_about:= http_client(
            f"https://www.youtube.com/channel/{output_dir}/about",
            f"{channelid_youtube_ids[output_dir]} 简介",
            2,
            5,
        ):
            channel_about = channel_about.text
            xml_tree = {
                "icon": re.sub(
                    r"=s(0|[1-9]\d{0,3}|1[0-9]{1,3}|20[0-3][0-9]|204[0-8])-c-k",
                    "=s2048-c-k",
                    re.search(
                        r"https?://yt3.googleusercontent.com/[^\s]*(?=\">)",
                        channel_about,
                    ).group(),
                )
            }
            xml_tree["description"] = re.search(
                r"(?<=\<meta itemprop\=\"description\" content\=\").*?(?=\")",
                channel_about,
                flags=re.DOTALL,
            ).group()
            with youtube_xml_get_lock:
                youtube_xml_get_tree[output_dir] = xml_tree
    # 创建线程列表
    youtube_xml_get_threads = []
    for output_dir in channelid_youtube_ids_update.keys():
        thread = threading.Thread(target=youtube_xml_get, args=(output_dir,))
        youtube_xml_get_threads.append(thread)
        thread.start()
    # 等待所有线程完成
    for thread in youtube_xml_get_threads:
        thread.join()

# 生成YouTube对应channel的需更新的items模块
def youtube_xml_items(output_dir):
    items_list = [f"<!-- {output_dir} -->"]
    entry_num = 0
    def get_xml_item(guid, item):
        video_website = f"https://youtube.com/watch?v={guid}"
        channelid_title = channelid_youtube[channelid_youtube_ids[output_dir]]["title"]
        if item["yt-dlp"]:
            title = html.escape(video_id_update_format[guid]["title"])
            description = html.escape(re.sub(r"\n+", "\n", video_id_update_format[guid]["description"]))
            timestamp = video_id_update_format[guid]["timestamp"]
            published = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
            pubDate = format_time(published)
            image = video_id_update_format[guid]["image"]
        else:
            title = html.escape(item["title"])
            description = html.escape(re.sub(r"\n+", "\n", item["description"]))
            pubDate = format_time(item["pubDate"])
            image = item["image"]
        return xml_item(
            guid,
            output_dir,
            video_website,
            channelid_title,
            title,
            description,
            pubDate,
            image,
        )
    # 最新更新
    if channelid_youtube_rss[output_dir]["type"] == "dict":
        for guid in channelid_youtube_rss[output_dir]["content"]["list"]:
            if guid not in video_id_failed:
                item = channelid_youtube_rss[output_dir]["content"]["item"][guid]
                xml_item_text = get_xml_item(guid, item)
                items_list.append(f"{xml_item_text}<!-- {output_dir} -->")
                entry_num += 1
    else:
        if channelid_youtube_rss[output_dir]["type"] == "html":  # 获取最新的rss信息
            file_xml = channelid_youtube_rss[output_dir]["content"].text
        else:
            file_xml = channelid_youtube_rss[output_dir]["content"]
        entrys = re.findall(r"<entry>.+?</entry>", file_xml, re.DOTALL)
        for entry in entrys:
            if (
                re.search(r"(?<=<yt:videoId>).+(?=</yt:videoId>)", entry).group()
                not in video_id_failed
            ):
                items_list.append(f"{youtube_xml_item(entry)}<!-- {output_dir} -->")
                entry_num += 1
            if (
                entry_num
                >= channelid_youtube[channelid_youtube_ids[output_dir]]["update_size"]
            ):
                break
    items_guid = re.findall(r"(?<=<guid>).+?(?=</guid>)", "".join(items_list))
    # 存量接入
    entry_count = channelid_youtube[channelid_youtube_ids[output_dir]][
        "last_size"
    ] - len(items_guid)
    if xmls_original and output_dir in xmls_original and entry_count > 0:
        xml_num = 0
        for xml in xmls_original[output_dir].split(f"<!-- {output_dir} -->"):
            xml_guid = re.search(r"(?<=<guid>).+(?=</guid>)", xml)
            if xml_guid and xml_guid.group() not in items_guid and xml_guid.group() not in video_id_failed:
                items_list.append(f"{xml_original_item(xml)}<!-- {output_dir} -->")
                xml_num += 1
            if xml_num >= entry_count:
                break
    # 向后更新
    try:
        backward = channelid_youtube_rss[output_dir]["backward"]
        for backward_guid in backward["list"]:
            if backward_guid not in video_id_failed:
                backward_item = backward["item"][backward_guid]
                backward_xml_item_text = get_xml_item(backward_guid, backward_item)
                items_list.append(f"{backward_xml_item_text}<!-- {output_dir} -->")
    except KeyError:
        pass
    # 生成对应xml
    try:
        with open(
            f"channel_rss/{output_dir}.xml", "r", encoding="utf-8"
        ) as file:  # 打开文件进行读取
            root = ET.parse(file).getroot()
            description = (root.findall(".//description")[0]).text
            description = "" if description is None else html.escape(description)
            icon = (root.findall(".//url")[0]).text
    except Exception:  # 参数不存在直接更新
        description = config["description"]
        icon = config["icon"]
    if (
        output_dir in channelid_youtube_ids_update
        and output_dir in youtube_xml_get_tree
    ):
        description = youtube_xml_get_tree[output_dir]["description"]
        icon = youtube_xml_get_tree[output_dir]["icon"]
    category = config["category"]
    if channelid_youtube_rss[output_dir]["type"] == "dict":
        title = channelid_youtube_rss[output_dir]["content"]["title"]
    else:
        title = re.search(r"(?<=<title>).+(?=</title>)", file_xml).group()
    link = f"https://www.youtube.com/channel/{output_dir}"
    items = "".join(items_list)
    items = f"""<!-- {{{output_dir}}} -->
{items}
<!-- {{{output_dir}}} -->"""
    file_save(
        xml_rss(title, link, description, category, icon, items),
        f"{output_dir}.xml",
        "channel_rss",
    )
    return items

# 生成哔哩哔哩对应channel的需更新的items模块
def bilibili_xml_items(output_dir):
    content_id, items_counts = get_file_list(output_dir, channelid_bilibili[channelid_bilibili_ids[output_dir]]["media"])
    items_list = [f"<!-- {output_dir} -->"]
    entry_num = 0
    def get_items_list(guid, item):
        pubDate = datetime.fromtimestamp(item["created"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
        if guid in items_counts:
            if "part" in item:
                guid_parts = item["part"]
            elif "edgeinfo" in item:
                guid_edgeinfos = item["edgeinfo"]
            else:
                if guid_parts:= get_bilibili_all_part(guid, channelid_bilibili_ids[output_dir]):
                    guid_edgeinfos = []
                else:
                    guid_edgeinfos = get_bilibili_interactive(guid, channelid_bilibili_ids[output_dir])
            if items_counts[guid] == len(guid_parts):
                for guid_part in guid_parts:
                    guid_part_text = f"{item['title']} Part{guid_part['page']:0{len(str(len(guid_parts)))}}"
                    if item["title"] != guid_part["part"]:
                        guid_part_text += f" {guid_part['part']}"
                    xml_item_text = xml_item(
                        f"{item['bvid']}_p{guid_part['page']}",
                        output_dir,
                        f"https://www.bilibili.com/video/{guid}?p={guid_part['page']}",
                        channelid_bilibili[channelid_bilibili_ids[output_dir]]["title"],
                        html.escape(guid_part_text),
                        html.escape(re.sub(r"\n+", "\n", item["description"])),
                        format_time(pubDate),
                        guid_part["first_frame"],
                    )
                    items_list.append(f"{xml_item_text}<!-- {output_dir} -->")
            elif items_counts[guid] == len(guid_edgeinfos):
                for guid_edgeinfo in guid_edgeinfos:
                    if guid_edgeinfo["options"]:
                        description = (
                            "〖互动视频〗\n"
                            + "\n".join(guid_edgeinfo["options"])
                            + "\n------------------------------------------------\n"
                            + item["description"]
                        )
                    else:
                        description = (
                            "〖互动视频〗\nTHE END."
                            + "\n------------------------------------------------\n"
                            + item["description"]
                        )
                    guid_edgeinfo_text = f"{item['title']} Part{guid_edgeinfo['num']:0{len(str(len(guid_edgeinfos)))}} {guid_edgeinfo['title']}"
                    xml_item_text = xml_item(
                        f"{item['bvid']}_{guid_edgeinfo['cid']}",
                        output_dir,
                        f"https://www.bilibili.com/video/{guid}",
                        channelid_bilibili[channelid_bilibili_ids[output_dir]]["title"],
                        html.escape(guid_edgeinfo_text),
                        html.escape(re.sub(r"\n+", "\n", description)),
                        format_time(pubDate),
                        guid_edgeinfo["first_frame"],
                    )
                    items_list.append(f"{xml_item_text}<!-- {output_dir} -->")
        else:
            xml_item_text = xml_item(
                item["bvid"],
                output_dir,
                f"https://www.bilibili.com/video/{guid}",
                channelid_bilibili[channelid_bilibili_ids[output_dir]]["title"],
                html.escape(item["title"]),
                html.escape(re.sub(r"\n+", "\n", item["description"])),
                format_time(pubDate),
                item["pic"],
            )
            items_list.append(f"{xml_item_text}<!-- {output_dir} -->")
    # 最新更新
    for guid in channelid_bilibili_rss[output_dir]["content"]["list"]:
        if guid not in video_id_failed and guid in content_id:
            item = channelid_bilibili_rss[output_dir]["content"]["entry"][guid]
            get_items_list(guid, item)
            entry_num += 1
            if (
                entry_num
                >= channelid_bilibili[channelid_bilibili_ids[output_dir]]["update_size"]
            ):
                break
    items_guid = re.findall(r"(?<=<guid>).+?(?=</guid>)", "".join(items_list))
    # 存量接入
    entry_count = channelid_bilibili[channelid_bilibili_ids[output_dir]][
        "last_size"
    ] - len(items_guid)
    if xmls_original and output_dir in xmls_original and entry_count > 0:
        xml_num = 0
        for xml in xmls_original[output_dir].split(f"<!-- {output_dir} -->"):
            xml_guid = re.search(r"(?<=<guid>).+(?=</guid>)", xml)
            if xml_guid and xml_guid.group() not in items_guid and xml_guid.group() not in video_id_failed:
                items_list.append(f"{xml_original_item(xml)}<!-- {output_dir} -->")
                xml_num += 1
            if xml_num >= entry_count:
                break
    # 向后更新
    try:
        backward = channelid_bilibili_rss[output_dir]["backward"]
        for backward_guid in backward["list"]:
            if backward_guid not in video_id_failed and backward_guid in content_id:
                backward_item = backward["entry"][backward_guid]
                get_items_list(backward_guid, backward_item)
    except KeyError:
        pass
    # 生成对应xml
    description = html.escape(channelid_bilibili_rss[output_dir]["content"]["sign"])
    icon = channelid_bilibili_rss[output_dir]["content"]["face"]
    category = config["category"]
    title = html.escape(channelid_bilibili_rss[output_dir]["content"]["name"])
    link = f"https://space.bilibili.com/{output_dir}"
    items = "".join(items_list)
    items = f"""<!-- {{{output_dir}}} -->
{items}
<!-- {{{output_dir}}} -->"""
    file_save(
        xml_rss(title, link, description, category, icon, items),
        f"{output_dir}.xml",
        "channel_rss",
    )
    return items

# 显示网址及二维码模块
def display_qrcode_and_url(output_dir, channelid_video, channelid_video_name, channelid_video_ids_update):
    if output_dir in channelid_video_ids_update:
        update_text = "已更新"
    else:
        update_text = "无更新"
    if (
        channelid_video["DisplayRSSaddress"] 
        or output_dir in channelid_video_ids_update
    ):
        print(f"{datetime.now().strftime('%H:%M:%S')}|{channelid_video_name} 播客{update_text}|地址:\n\033[34m{config['url']}/channel_rss/{output_dir}.xml\033[0m")
    if (
        (
            channelid_video["DisplayRSSaddress"] 
            or output_dir in channelid_video_ids_update
        )
        and channelid_video["QRcode"]
        and output_dir not in displayed_QRcode
    ):
        qr_code(f"{config['url']}/channel_rss/{output_dir}.xml")
        displayed_QRcode.append(output_dir)

# 生成主rss模块
def create_main_rss():
    for output_dir in channelid_youtube_ids:
        items = youtube_xml_items(output_dir)
        display_qrcode_and_url(
            output_dir,
            channelid_youtube[channelid_youtube_ids[output_dir]],
            channelid_youtube_ids[output_dir],
            channelid_youtube_ids_update
        )
        if channelid_youtube[channelid_youtube_ids[output_dir]]["InmainRSS"]:
            all_items.append(items)
        all_youtube_content_ytid[output_dir] = re.findall(
            r"(?:/UC.{22}/)(.{11}\.m4a|.{11}\.mp4)(?=\")", items
        )
    for output_dir in channelid_bilibili_ids:
        items = bilibili_xml_items(output_dir)
        display_qrcode_and_url(
            output_dir,
            channelid_bilibili[channelid_bilibili_ids[output_dir]],
            channelid_bilibili_ids[output_dir],
            channelid_bilibili_ids_update
        )
        if channelid_bilibili[channelid_bilibili_ids[output_dir]]["InmainRSS"]:
            all_items.append(items)
        all_bilibili_content_bvid[output_dir] = re.findall(
            r"(?:/[0-9]+/)(BV.{10}\.m4a|BV.{10}\.mp4|BV.{10}_p[0-9]+\.m4a|BV.{10}_p[0-9]+\.mp4|BV.{10}_[0-9]{9}\.m4a|BV.{10}_[0-9]{9}\.mp4)(?=\")", items
        )

# xml备份保存模块
def backup_zip_save(file_content):
    def get_file_name():
        # 获取当前的具体时间
        current_time = datetime.now()
        # 格式化输出, 只保留年月日时分秒
        formatted_time = current_time.strftime("%Y%m%d%H%M%S")
        return f"{formatted_time}.xml"
    # 定义要添加到压缩包中的文件名和内容
    compress_file_name = "Podflow_backup.zip"
    # 生成新rss的哈希值
    hash_overall_rss = rss_create_hash(overall_rss)
    # 使用哈希值判断新老rss是否一致
    if hash_overall_rss == hash_rss_original:
        judging_save = True
        write_log("频道无更新内容将不进行备份")
    else:
        judging_save = False
    while not judging_save:
        # 获取要写入压缩包的文件名
        file_name_str = get_file_name()
        # 打开压缩文件，如果不存在则创建
        with zipfile.ZipFile(compress_file_name, 'a') as zipf:
            # 设置压缩级别为最大
            zipf.compression = zipfile.ZIP_LZMA
            zipf.compresslevel = 9
            # 检查文件是否已存在于压缩包中
            if file_name_str not in zipf.namelist():
                # 将文件内容写入压缩包
                zipf.writestr(file_name_str, file_content)
                judging_save = True
            else:
                # 如果文件已存在，输出提示信息
                print(f"{file_name_str}已存在于压缩包中，重试中...")

# 删除多余媒体文件模块
def remove_file():
    for output_dir in channelid_youtube_ids:
        for file_name in os.listdir(f"channel_audiovisual/{output_dir}"):
            if file_name not in all_youtube_content_ytid[output_dir]:
                os.remove(f"channel_audiovisual/{output_dir}/{file_name}")
                write_log(f"{channelid_youtube_ids[output_dir]}|{file_name}已删除")
    for output_dir in channelid_bilibili_ids:
        for file_name in os.listdir(f"channel_audiovisual/{output_dir}"):
            if file_name not in all_bilibili_content_bvid[output_dir]:
                os.remove(f"channel_audiovisual/{output_dir}/{file_name}")
                write_log(f"{channelid_bilibili_ids[output_dir]}|{file_name}已删除")

# 删除已抛弃的媒体文件夹模块
def remove_dir():
    folder_names = [
        folder
        for folder in os.listdir("channel_audiovisual")
        if os.path.isdir(f"channel_audiovisual/{folder}")
    ]
    folder_names_youtube = [name for name in folder_names if re.match(r"UC.{22}", name)]
    for name in folder_names_youtube:
        if name not in channelid_youtube_ids_original:
            os.system(f"rm -r channel_audiovisual/{name}")
            write_log(f"{name}文件夹已删除")
    folder_names_bilibili = [name for name in folder_names if re.match(r"[0-9]+", name)]
    for name in folder_names_bilibili:
        if name not in channelid_bilibili_ids_original:
            os.system(f"rm -r channel_audiovisual/{name}")
            write_log(f"{name}文件夹已删除")

# 补全缺失媒体文件到字典模块
def make_up_file():
    for output_dir in channelid_youtube_ids:
        for file_name in all_youtube_content_ytid[output_dir]:
            if file_name not in os.listdir(f"channel_audiovisual/{output_dir}"):
                video_id_format = {
                    "id": output_dir,
                    "media": file_name.split(".")[1],
                    "url": f"https://www.youtube.com/watch?v={output_dir}",
                    "name": channelid_youtube_ids[output_dir],
                    "cookie": None,
                    "main": file_name.split(".")[0],
                }
                if file_name.split(".")[0] == "mp4":
                    video_quality = channelid_youtube[channelid_youtube_ids[output_dir]][
                        "quality"
                    ]
                else:
                    video_quality = 480
                video_id_format["quality"] = video_quality
                make_up_file_format[file_name.split(".")[0]] = video_id_format
    for output_dir in channelid_bilibili_ids:
        for file_name in all_bilibili_content_bvid[output_dir]:
            if file_name not in os.listdir(f"channel_audiovisual/{output_dir}"):
                main = file_name.split(".")[0][:12]
                if main not in make_up_file_format:
                    media = file_name.split(".")[1]
                    video_id_format = {
                        "id": output_dir,
                        "media": media,
                        "url": f"https://www.bilibili.com/video/{main}",
                        "name": channelid_bilibili_ids[output_dir],
                        "cookie": "yt_dlp_bilibili.txt",
                        "main": main
                    }
                    if file_name.split(".")[0] == "mp4":
                        video_quality = channelid_bilibili[channelid_bilibili_ids[output_dir]][
                            "quality"
                        ]
                    else:
                        video_quality = 480
                    video_id_format["quality"] = video_quality
                    make_up_file_format[main] = video_id_format

# 补全在rss中缺失的媒体格式信息模块
def make_up_file_format_mod():
    # 判断是否补全
    if len(make_up_file_format) != 0:
        print(f"{datetime.now().strftime('%H:%M:%S')}|补全缺失媒体 \033[34m下载准备中...\033[0m")
    # 创建线程锁
    makeup_yt_format_lock = threading.Lock()
    def makeup_yt_format(video_id):
        makeup_id_format = media_format(
            make_up_file_format[video_id]["url"],
            make_up_file_format[video_id]["main"],
            make_up_file_format[video_id]["media"],
            make_up_file_format[video_id]["quality"],
            make_up_file_format[video_id]["cookie"],
        )
        if isinstance(makeup_id_format, list):
            if len(makeup_id_format) == 1:
                entry_id_makeup_format = makeup_id_format[0]
                make_up_file_format[video_id]["format"] = entry_id_makeup_format["duration_and_id"]
                make_up_file_format[video_id]["download"] = entry_id_makeup_format["download"]
            else:
                entrys_id = []
                for entry_id_makeup_format in makeup_id_format:
                    entry_id = entry_id_makeup_format["id"]
                    entrys_id.append(entry_id)
                    make_up_file_format[entry_id] = {
                        "id": make_up_file_format[video_id]["id"],
                        "name": make_up_file_format[video_id]["name"],
                        "media": make_up_file_format[video_id]["media"],
                        "quality": make_up_file_format[video_id]["quality"],
                        "url": entry_id_makeup_format["url"],
                        "cookie": make_up_file_format[video_id]["cookie"],
                        "format": entry_id_makeup_format["duration_and_id"],
                        "main": make_up_file_format[video_id]["main"],
                        "download": entry_id_makeup_format["download"],
                    }
                del make_up_file_format[video_id]
        else:
            with makeup_yt_format_lock:
                write_log(
                    f"{make_up_file_format[video_id]['name']}|{video_id}|{makeup_id_format}"
                )
                make_up_file_format_fail[video_id] = make_up_file_format[video_id]['id']  # 将无法补全的媒体添加到失败字典中
                del make_up_file_format[video_id]
    # 创建线程列表
    makeup_yt_format_threads = []
    for video_id in make_up_file_format.keys():
        thread = threading.Thread(target=makeup_yt_format, args=(video_id,))
        makeup_yt_format_threads.append(thread)
        thread.start()
    # 等待所有线程完成
    for thread in makeup_yt_format_threads:
        thread.join()

# 下载补全Youtube和哔哩哔哩视频模块
def make_up_file_mod():
    for video_id in make_up_file_format.keys():
        media = make_up_file_format[video_id]["media"]
        id = make_up_file_format[video_id]["id"]
        name = make_up_file_format[video_id]['name']
        if f"{video_id}.{media}" not in os.listdir(f"channel_audiovisual/{id}"):
            write_log(
                f"{name}|{video_id} 缺失并重新下载"
            )
            if dl_aideo_video(
                video_id,
                id,
                media,
                make_up_file_format[video_id]["format"],
                config["retry_count"],
                make_up_file_format[video_id]["download"]["url"],
                name,
                make_up_file_format[video_id]["cookie"],
                make_up_file_format[video_id]["download"]["num"]
            ):
                video_id_failed.append(video_id)
                write_log(
                    f"{make_up_file_format[video_id]['name']}|{video_id} \033[31m无法下载\033[0m"
                )

# 删除无法补全的媒体模块
def del_makeup_yt_format_fail(overall_rss):
    for video_id in make_up_file_format_fail.keys():
        pattern_video_fail_item = rf'<!-- {make_up_file_format_fail[video_id]} -->(?:(?!<!-- {make_up_file_format_fail[video_id]} -->).)+?<guid>{video_id}</guid>.+?<!-- {make_up_file_format_fail[video_id]} -->'
        replacement_video_fail_item = f'<!-- {make_up_file_format_fail[video_id]} -->'
        overall_rss = re.sub(pattern_video_fail_item, replacement_video_fail_item, overall_rss, flags=re.DOTALL)
    return overall_rss

# 获取配置文件config
config = get_config()
# 纠正配置信息config
correct_config()
# 从配置文件中获取YouTube的频道
channelid_youtube = get_channelid("youtube")
# 从配置文件中获取哔哩哔哩的频道
channelid_bilibili = get_channelid("bilibili")
# 构建文件夹channel_id
folder_build("channel_id")
# 构建文件夹channel_audiovisual
folder_build("channel_audiovisual")
# 构建文件夹channel_rss
folder_build("channel_rss")
# 修正channelid_youtube
channelid_youtube = correct_channelid(channelid_youtube, "youtube")
# 修正channelid_bilibili
channelid_bilibili = correct_channelid(channelid_bilibili, "bilibili")
# 读取youtube频道的id
channelid_youtube_ids = get_channelid_id(channelid_youtube, "youtube")
# 复制youtube频道id用于删除已抛弃的媒体文件夹
channelid_youtube_ids_original = channelid_youtube_ids.copy()
# 读取bilibili频道的id
channelid_bilibili_ids = get_channelid_id(channelid_bilibili, "bilibili")
# 复制bilibili频道id用于删除已抛弃的媒体文件夹
channelid_bilibili_ids_original = channelid_bilibili_ids.copy()

# 主流程
server_process_print_flag = ["keep"]  # 进程打印标志初始化

# 进程打印模块
def server_process_print():
    global httpserver_process, server_process_print_flag
    need_keep = ""
    output_replace_infos = ["channel_rss/", "channel_audiovisual/", "\"", " HTTP/1.1", " 200 -", " (http://[::]:8000/) ..."]
    while True:
        output = httpserver_process.stdout.readline().decode().strip()
        re1_output = re.search(r"(?<=\[[0-9]{2}/[a-zA-Z]{3}/[0-9]{4} )[0-2][0-9]:[0-6][0-9]:[0-6][0-9](?=\])", output)
        re2_output = re.search(r"(?<=\[[0-9]{2}/[a-zA-Z]{3}/[0-9]{4} [0-2][0-9]:[0-6][0-9]:[0-6][0-9]\] )\".+\".+", output)
        if re1_output and re2_output:
            output = re2_output.group(0)
            output_time = re1_output.group(0)
        else:
            output_time = datetime.now().strftime('%H:%M:%S')
        if output:
            for output_replace_info in output_replace_infos:
                output = output.replace(output_replace_info, "")
            for channelid_ids_original_key, channelid_ids_original_value in (channelid_youtube_ids_original | channelid_bilibili_ids_original).items():
                output = output.replace(channelid_ids_original_key, channelid_ids_original_value)
            if need_keep == "":
                need_keep = f"{output_time}|{output}"
            else:
                need_keep += f"\n{output_time}|{output}"
        if server_process_print_flag[0] == "keep":
            if need_keep:
                print(need_keep)
            need_keep = ""
        if server_process_print_flag[0] == "end" or output == "Keyboard interrupt received, exiting.":
            break

# 创建进程打印线程
prepare_print = threading.Thread(target=server_process_print)

# 启动 RangeHTTPServer
try:
    httpserver_process = subprocess.Popen(["python3", "-m", "RangeHTTPServer"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
except FileNotFoundError:
    httpserver_process = subprocess.Popen(["python", "-m", "RangeHTTPServer"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

# 启动进程打印线程
prepare_print.start()

# 循环主更新
while update_num > 0 or update_num == -1:
    # 暂停进程打印
    server_process_print_flag[0] = "pause"
    # 更新哔哩哔哩data
    channelid_bilibili_ids, bilibili_data = get_bilibili_data(channelid_bilibili_ids_original)
    # 恢复进程打印
    server_process_print_flag[0] = "keep"
    # 获取原始xml字典和rss文本
    xmls_original, hash_rss_original, xmls_original_fail = get_original_rss()
    # 更新Youtube和哔哩哔哩频道xml
    update_youtube_bilibili_rss()
    # 判断是否有更新内容
    if channelid_youtube_ids_update != {} or channelid_bilibili_ids_update != {}:
        update_generate_rss = True
    if update_generate_rss:
        # 根据日出日落修改封面(只适用原封面)
        channge_icon()
        # 输出需要更新的信息
        update_information_display(channelid_youtube_ids_update, youtube_content_ytid_update, youtube_content_ytid_backward_update, "YouTube")
        update_information_display(channelid_bilibili_ids_update, bilibili_content_bvid_update, bilibili_content_bvid_backward_update, "BiliBili")
        # 暂停进程打印
        server_process_print_flag[0] = "pause"
        # 获取视频格式信息
        get_video_format()
        # 恢复进程打印
        server_process_print_flag[0] = "keep"
        # 暂停进程打印
        server_process_print_flag[0] = "pause"
        # 下载YouTube和哔哩哔哩视频
        youtube_and_bilibili_download()
        # 恢复进程打印
        server_process_print_flag[0] = "keep"
        # 打印无法保留原节目信息
        original_rss_fail_print(xmls_original_fail)
        # 获取YouTube频道简介
        get_youtube_introduction()
        # 暂停进程打印
        server_process_print_flag[0] = "pause"
        # 生成分和主rss
        create_main_rss()
        # 恢复进程打印
        server_process_print_flag[0] = "keep"
        # 删除不在rss中的媒体文件
        remove_file()
        # 删除已抛弃的媒体文件夹
        remove_dir()
        # 补全缺失媒体文件到字典
        make_up_file()
        # 按参数获取需要补全的最大个数
        make_up_file_format = split_dict(make_up_file_format, config["completion_count"], True)[0]
        # 暂停进程打印
        server_process_print_flag[0] = "pause"
        # 补全在rss中缺失的媒体格式信息
        make_up_file_format_mod()
        # 恢复进程打印
        server_process_print_flag[0] = "keep"
        # 生成主rss
        overall_rss = xml_rss(
            config["title"],
            config["link"],
            config["description"],
            config["category"],
            config["icon"],
            "\n".join(all_items),
            )
        # 删除无法补全的媒体
        overall_rss = del_makeup_yt_format_fail(overall_rss)
        # 保存主rss
        file_save(overall_rss, f"{config['filename']}.xml")
        # 暂停进程打印
        server_process_print_flag[0] = "pause"
        write_log("总播客已更新", f"地址:\n\033[34m{config['url']}/{config['filename']}.xml\033[0m")
        if "main" not in displayed_QRcode:
            qr_code(f"{config['url']}/{config['filename']}.xml")
            displayed_QRcode.append("main")
        # 恢复进程打印
        server_process_print_flag[0] = "keep"
        # 备份主rss
        backup_zip_save(overall_rss)
        # 暂停进程打印
        server_process_print_flag[0] = "pause"
        # 下载补全Youtube和哔哩哔哩视频模块
        make_up_file_mod()
        # 恢复进程打印
        server_process_print_flag[0] = "keep"
    else:
        print(f"{datetime.now().strftime('%H:%M:%S')}|频道无更新内容")
    # 清空变量内数据
    channelid_youtube_ids_update.clear()  # 需更新的YouTube频道字典
    youtube_content_ytid_update.clear()  # 需下载YouTube视频字典
    youtube_content_ytid_backward_update.clear()  # 向后更新需下载YouTube视频字典
    channelid_youtube_rss.clear()  # YouTube频道最新Rss Response字典
    channelid_bilibili_ids_update.clear()  # 需更新的哔哩哔哩频道字典
    bilibili_content_bvid_update.clear()  # 需下载哔哩哔哩视频字典
    channelid_bilibili_rss.clear()  # 哔哩哔哩频道最新Rss Response字典
    bilibili_content_bvid_backward_update.clear()  # 向后更新需下载哔哩哔哩视频字典
    video_id_failed.clear()  # YouTube&哔哩哔哩视频下载失败列表
    video_id_update_format.clear()  # YouTube&哔哩哔哩视频下载的详细信息字典
    hash_rss_original = ""  # 原始rss哈希值文本
    xmls_original.clear()  # 原始xml信息字典
    xmls_original_fail.clear()  # 未获取原始xml频道列表
    youtube_xml_get_tree.clear()  # YouTube频道简介和图标字典
    all_youtube_content_ytid.clear()  # 所有YouTube视频id字典
    all_bilibili_content_bvid.clear()  # 所有哔哩哔哩视频id字典
    all_items.clear()  # 更新后所有item明细列表
    overall_rss = ""  # 更新后的rss文本
    make_up_file_format.clear()  # 补全缺失媒体字典
    make_up_file_format_fail.clear()  # 补全缺失媒体失败字典
    # 将需要更新转为否
    update_generate_rss = False
    if update_num != -1:
        update_num -= 1
    if argument == "a-shell":
        openserver_process = subprocess.Popen(
            ["open", f"shortcuts://run-shortcut?name=Podflow&input=text&text={urllib.parse.quote(json.dumps(shortcuts_url))}"]
        )
        # 延时
        time.sleep(60+len(shortcuts_url)*5)
        openserver_process.terminate()
        break
    elif update_num == 0:
        break
    else:
        # 延时
        time.sleep(time_delay)

# 停止 RangeHTTPServer
httpserver_process.terminate()
server_process_print_flag[0] = "end"
http_client("http://127.0.0.1:8000/", "", 1, 0)
prepare_print.join()
print(f"{datetime.now().strftime('%H:%M:%S')}|Podflow运行结束")