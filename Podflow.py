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
import threading
import subprocess
import http.cookiejar
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

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
        }
    },
    "channelid_bilibili": {
        "哔哩哔哩漫画": {
            "update_size": 15,
            "id": "BL-------------326499679",
            "title": "哔哩哔哩漫画",
            "quality": "480",
            "last_size": 50,
            "media": "m4a",
            "DisplayRSSaddress": False,
            "InmainRSS": True,
            "QRcode": False,
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

server_process_print_flag = ["keep"]  # 进程打印标志列表

channelid_youtube_ids_update = {}  # 需更新的YouTube频道字典
youtube_content_ytid_update = {}  # 需下载YouTube视频字典
channelid_youtube_rss = {}  # YouTube频道最新Rss Response字典
yt_id_failed = []  # YouTube视频下载失败列表
youtube_content_ytid_update_format = {}  # YouTube视频下载的详细信息字典
hash_rss_original = ""  # 原始rss哈希值文本
xmls_original = {}  # 原始xml信息字典
youtube_xml_get_tree = {}  # YouTube频道简介和图标字典
all_youtube_content_ytid = {}  # 所有YouTube视频id字典
all_items = []  # 更新后所有item明细列表
overall_rss = ""  # 更新后的rss文本
make_up_file_format = {}  # 补全缺失媒体字典
make_up_file_format_fail = {}  # 补全缺失媒体失败字典

# 文件保存模块
def file_save(content, file_name, folder=None):
    # 如果指定了文件夹则将文件保存到指定的文件夹中
    if folder:
        file_path = os.path.join(os.path.join(os.getcwd(), folder), file_name)
    else:
        # 如果没有指定文件夹则将文件保存在当前工作目录中
        file_path = os.path.join(os.getcwd(), file_name)
    # 保存文件
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)

# 日志模块
def write_log(log, suffix=None, display=True, time_display=True):
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
    new_contents = f"{formatted_time} {log_in}\n{contents}"
    # 将新的日志内容写入文件
    file_save(new_contents, "log.txt")
    if display:
        formatted_time_mini = current_time.strftime("%H:%M:%S")
        log_print = f"{formatted_time_mini}|{log}" if time_display else f"{log}"
        log_print = f"{log_print}|{suffix}" if suffix else f"{log_print}"
        print(log_print)

# 查看requests模块是否安装
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
        sys.exit(0)
    except FileNotFoundError:
        write_log("\033[31mrequests安装失败请重试\033[0m")
        sys.exit(0)

# HTTP 请求重试模块
def http_client(url, name, max_retries=10, retry_delay=4, headers_possess=False, cookies=None, data=None, cookie_jar_name=None, mode="get"):
    user_agent = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    err = None  # 初始化 err 变量
    response = None  # 初始化 response 变量
    # 创建一个Session对象
    session = requests.Session()
    if cookie_jar_name:
        # 创建一个MozillaCookieJar对象，指定保存文件
        cookie_jar = http.cookiejar.MozillaCookieJar(f"{cookie_jar_name}.txt")
        # 将CookieJar对象绑定到Session对象
        session.cookies = cookie_jar
    if headers_possess:
        session.headers.update(user_agent)
    if cookies:
        session.cookies.update(cookies)
    if data:
        session.params.update(data)
    for num in range(max_retries):
        try:
            if mode == "get":
                response = session.get(url, timeout=8)
            else:
                response = session.post(url, timeout=8)
            response.raise_for_status()
        except Exception as http_get_error:
            if response is not None and response.status_code in {404}:
                return response
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
    if version := re.search(
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
    "RangeHTTPServer",
    "chardet",
    "requests",
    "astral",
    "qrcode",
    "pycryptodome",
]

library_import = False
today_library_log = read_today_library_log()

while library_import is False:
    try:
        import qrcode
        import yt_dlp
        from astral.sun import sun
        from astral import LocationInfo
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
            break

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
                    ascii_art += " "
            ascii_art += "\n"
    print(ascii_art)

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
def video_format(video_website, video_url, media="m4a", quality="480"):
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
        fail_message, duration, formats = None, None, None
        try:
            # 初始化 yt_dlp 实例, 并忽略错误
            ydl_opts = {
                "no_warnings": True,
                "quiet": True,  # 禁止非错误信息的输出
                "logger": MyLogger(),
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 使用提供的 URL 提取视频信息
                if info_dict := ydl.extract_info(
                    f"{video_website}{video_url}", download=False
                ):
                    # 获取视频时长并返回
                    duration = info_dict.get("duration")
                    formats = info_dict.get("formats")
        except Exception as message_error:
            fail_message = (
                (str(message_error))
                .replace("ERROR: ", "")
                .replace("\033[0;31mERROR:\033[0m ", "")
                .replace(f"{video_url}: ", "")
                .replace("[youtube] ", "")
            )
        return fail_message, duration, formats
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
    }
    def fail_message_initialize(fail_message, error_reason):
        for key in error_reason:
            if re.search(key, fail_message):
                return [key, error_reason[key]]
    yt_id_count, change_error, fail_message, duration, formats = 0, None, "", "", ""
    while (
        yt_id_count < 3
        and change_error is None
        and (fail_message is not None or duration is None or formats is None)
    ):
        yt_id_count += 1
        fail_message, duration, formats = duration_and_formats(video_website, video_url)
        if fail_message:
            change_error = fail_message_initialize(fail_message, error_reason)
    if change_error:
        fail_message = re.sub(rf"{change_error[0]}", change_error[1], fail_message)
    if fail_message is None:
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
                )
            else:
                return False
        # 获取最好质量媒体的id
        def best_format_id(formats):
            filesize_max = 0
            format_id_best = ""
            vcodec_best = ""
            for format in formats:
                if (
                    "filesize" in format
                    and (isinstance(format["filesize"], (float, int)))
                    and format["filesize"] > filesize_max
                ):
                    filesize_max = format["filesize"]
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
        return duration_and_id
    else:
        return fail_message

# 获取已下载视频时长模块
def get_duration_ffprobe(file_path):
    try:
        # 调用 ffprobe 命令获取视频文件的时长信息
        command = [
            "ffprobe",  # ffprobe 命令
            "-i",
            file_path,  # 输入文件路径
            "-show_entries",
            "format",  # 显示时长信息
            "-v",
            "error",
        ]
        # 执行命令并获取输出
        output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode(
            "utf-8"
        )
        if output := re.search(r"(?<=duration.)[0-9]+\.?[0-9]*", output):
            return math.ceil(float(output.group()))
        else:
            return None
    except subprocess.CalledProcessError as get_duration_ffprobe_error:
        write_log(f"Error: {get_duration_ffprobe_error.output}")
        return None

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
                f"\r{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation} \033[31m失败：\033[0m"
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
                msg.replace("ERROR: ", "")
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
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"{video_website}{video_url}"])  # 下载指定视频链接的视频
    except Exception as download_video_error:
        write_log(
            (f"{video_write_log} \033[31m下载失败\033[0m\n错误信息：{str(download_video_error)}")
            .replace("ERROR: ", "")
            .replace("\033[0;31mERROR:\033[0m ", "")
            .replace(f"{video_url}: ", "")
            .replace("[youtube] ", "")
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
):
    if download_video(
        video_url,
        output_dir,
        output_format,
        format_id,
        video_website,
        video_write_log,
        sesuffix,
    ):
        return video_url
    duration_video = get_duration_ffprobe(
        f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}"
    )  # 获取已下载视频的实际时长
    if abs(id_duration - duration_video) <= 1:  # 检查实际时长与预计时长是否一致
        return None
    if duration_video:
        write_log(
            f"{video_write_log} \033[31m下载失败\033[0m\n错误信息：不完整({id_duration}|{duration_video})"
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
):
    yt_id_failed = dl_full_video(
        video_url,
        output_dir,
        output_format,
        format_id,
        id_duration,
        video_website,
        video_write_log,
        sesuffix,
    )
    # 下载失败后重复尝试下载视频
    yt_id_count = 0
    while yt_id_count < retry_count and yt_id_failed:
        yt_id_count += 1
        write_log(f"{video_write_log}第\033[34m{yt_id_count}\033[0m次重新下载")
        yt_id_failed = dl_full_video(
            video_url,
            output_dir,
            output_format,
            format_id,
            id_duration,
            video_website,
            video_write_log,
            sesuffix,
        )
    return yt_id_failed

# 音视频总下载模块
def dl_aideo_video(
    video_url,
    output_dir,
    output_format,
    video_format,
    retry_count,
    video_website,
    output_dir_name="",
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
        if video_format[1] != "140":
            print(f" \033[97m{video_format[1]}\033[0m")
        else:
            print("")
        yt_id_failed = dl_retry_video(
            video_url,
            output_dir,
            "m4a",
            video_format[1],
            id_duration,
            retry_count,
            video_website,
            video_write_log,
            "",
        )
    else:
        print(
            f"\n{datetime.now().strftime('%H:%M:%S')}|\033[34m开始视频部分下载\033[0m\033[97m{video_format[2]}\033[0m"
        )
        yt_id_failed = dl_retry_video(
            video_url,
            output_dir,
            "mp4",
            video_format[2],
            id_duration,
            retry_count,
            video_website,
            video_write_log,
            ".part",
        )
        if yt_id_failed is None:
            print(
                f"{datetime.now().strftime('%H:%M:%S')}|\033[34m开始音频部分下载\033[0m\033[97m{video_format[1]}\033[0m"
            )
            yt_id_failed = dl_retry_video(
                video_url,
                output_dir,
                "m4a",
                video_format[1],
                id_duration,
                retry_count,
                video_website,
                video_write_log,
                ".part",
            )
        if yt_id_failed is None:
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
                yt_id_failed = video_url
                write_log(f"\n{video_write_log} \033[31m下载失败\033[0m\n错误信息：合成失败:{dl_aideo_video_error}")
    if yt_id_failed is None:
        write_log(f"{video_write_log} \033[32m下载成功\033[0m")  # 写入下载成功的日志信息
    return yt_id_failed

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
            write_log("已读取配置文件")
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
        # 获取公网IP地址
        response = http_client("https://ipinfo.io", "日出日落信息", 10, 6)
        if response:
            data = response.json()
            # 提取经度和纬度
            coordinates = data["loc"].split(",")
            latitude = coordinates[0]
            longitude = coordinates[1]
            picture_name = f"Podflow_{judging_day_and_night(latitude, longitude)}"
            config["icon"] = f"https://raw.githubusercontent.com/gruel-zxz/podflow/main/{picture_name}.png"

# 从配置文件中获取频道模块
def get_channelid(name):
    if f"channelid_{name}" in config:
        write_log(f"已读取{name}频道信息")
        return config[f"channelid_{name}"]
    else:
        write_log(f"{name}频道信息不存在")
        return None

# channelid修正模块
def correct_channelid(channelid, website):
    # 音视频格式及分辨率长量
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
        if isinstance(channeli_value, str) and re.search(r"UC.{22}", channeli_value):
            channeli_value = {"id": channeli_value}
            channelid[channelid_key] = channeli_value
        # 判断id是否正确
        if "id" not in channeli_value or not re.search(
            r"UC.{22}", channeli_value["id"]
        ):
            # 删除错误的
            del channelid[channelid_key]
            write_log(f"{website}频道 {channelid_key} ID不正确")
        else:
            # 对update_size进行纠正
            if (
                "update_size" not in channeli_value
                or not isinstance(channeli_value["update_size"], int)
                or channeli_value["update_size"] <= 0
            ):
                channelid[channelid_key]["update_size"] = default_config[
                    f"channelid_{website}"
                ]["youtube"]["update_size"]
            # 对id进行纠正
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
                ]["youtube"]["last_size"]
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
                ]["youtube"]["quality"]
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
    return channelid

# 读取频道ID模块
def get_channelid_id(channelid):
    if channelid is not None:
        channelid_ids = dict(
            {channel["id"]: key for key, channel in channelid.items()}
        )
        write_log("读取youtube频道的channelid成功")
    else:
        channelid_ids = None
    return channelid_ids

# 更新Youtube频道xml模块
def youtube_rss_update(youtube_key, youtube_value, pattern_youtube_varys):
    # 构建 URL
    youtube_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={youtube_key}"
    youtube_response = http_client(youtube_url, youtube_value)
    channelid_youtube_rss[youtube_key] = youtube_response
    if youtube_response:
        youtube_content = youtube_response.text
        youtube_content_clean = vary_replace(pattern_youtube_varys, youtube_content)
        # 读取原Youtube频道xml文件并判断是否要更新
        try:
            with open(
                f"channel_id/{youtube_key}.txt", "r", encoding="utf-8"
            ) as file:  # 打开文件进行读取
                youtube_content_original = file.read()  # 读取文件内容
                youtube_content_original_clean = vary_replace(
                    pattern_youtube_varys, youtube_content_original
                )
            if youtube_content_clean != youtube_content_original_clean:  # 判断是否要更新
                channelid_youtube_ids_update[youtube_key] = youtube_value
                channelid_youtube[channelid_youtube_ids[youtube_key]][
                    "DisplayRSSaddress"
                ] = True
        except FileNotFoundError:  # 文件不存在直接更新
            channelid_youtube_ids_update[youtube_key] = youtube_value
            channelid_youtube[channelid_youtube_ids[youtube_key]][
                "DisplayRSSaddress"
            ] = True
        # 获取Youtube视频ID列表
        youtube_content_ytid = re.findall(
            r"(?<=<id>yt:video:).{11}(?=</id>)", youtube_content
        )
        youtube_content_ytid = youtube_content_ytid[
            : channelid_youtube[youtube_value]["update_size"]
        ]
        # 获取已下载媒体名称
        youtube_media = (
            ("m4a", "mp4")
            if channelid_youtube[youtube_value]["media"] == "m4a"
            else ("mp4")
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
        if youtube_content_ytid := [
            exclude
            for exclude in youtube_content_ytid
            if exclude not in youtube_content_ytid_original
        ]:
            channelid_youtube_ids_update[youtube_key] = youtube_value
            channelid_youtube[channelid_youtube_ids[youtube_key]][
                "DisplayRSSaddress"
            ] = True
            youtube_content_ytid_update[youtube_key] = youtube_content_ytid

# 更新Youtube频道xml多线程模块
def update_youtube_rss():
    pattern_youtube404 = r"Error 404 \(Not Found\)"  # 设置要匹配的正则表达式模式
    pattern_youtube_varys = [
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-2][0-9]:[0-6][0-9]:[0-6][0-9]\+00:00",
        r'starRating count="[0-9]*"',
        r'statistics views="[0-9]*"',
        r"<id>yt:channel:(UC)?(.{22})?</id>",
        r"<yt:channelId>(UC)?(.{22})?</yt:channelId>",
    ]
    youtube_rss_update_threads = []  # 创建线程列表
    for youtube_key, youtube_value in channelid_youtube_ids.items():
        thread = threading.Thread(
            target=youtube_rss_update, args=(youtube_key, youtube_value, pattern_youtube_varys)
        )
        youtube_rss_update_threads.append(thread)
        thread.start()
    # 等待所有线程完成
    for thread in youtube_rss_update_threads:
        thread.join()
    for youtube_key, youtube_value in channelid_youtube_ids.copy().items():
        youtube_response = channelid_youtube_rss[youtube_key]
        # 异常xml排查及重新获取
        num_try_update = 0
        while youtube_response is not None and ((re.search(pattern_youtube404, youtube_response.text, re.DOTALL) and num_try_update < 3) or not re.search(rf"{youtube_key}", youtube_response.text, re.DOTALL)):
            print(f"{datetime.now().strftime('%H:%M:%S')}|YouTube频道 {youtube_value}|\033[31m获取异常重试中...\033[97m{num_try_update + 1}\033[0m")
            youtube_rss_update(youtube_key, youtube_value, pattern_youtube_varys)
            num_try_update += 1
            youtube_response = channelid_youtube_rss[youtube_key]
        # xml分类及存储
        if youtube_response is not None:
            youtube_content = youtube_response.text
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
            if not os.path.exists(os.path.join("channel_id", f"{youtube_key}.txt")):
                del channelid_youtube_ids[youtube_key]
            write_log(f"YouTube频道 {youtube_value} 无法更新")

# 输出需要更新的信息模块
def update_information_display():
    if channelid_youtube_ids_update:
        print_channelid_youtube_ids_update = "需更新的YouTube频道:\n"
        # 获取命令行字节宽度
        try:
            terminal_width = os.get_terminal_size().columns
        except OSError:
            terminal_width = 47
        # 尝试拆分输出
        try:
            for channelid_key, channelid_value in channelid_youtube_ids_update.items():
                if len(print_channelid_youtube_ids_update) != 15:
                    if (
                        len(
                            re.sub(
                                r"\033\[[0-9;]+m",
                                "",
                                print_channelid_youtube_ids_update.split("\n")[-1],
                            ).encode("GBK")
                        )
                        + len(f" | {channelid_value}".encode("utf-8"))
                        <= terminal_width
                    ):
                        print_channelid_youtube_ids_update += " | "
                    else:
                        print_channelid_youtube_ids_update += "\n"
                if channelid_key in youtube_content_ytid_update:
                    print_channelid_youtube_ids_update += (
                        f"\033[32m{channelid_value}\033[0m"
                    )
                else:
                    print_channelid_youtube_ids_update += (
                        f"\033[33m{channelid_value}\033[0m"
                    )
        # 如果含有特殊字符将使用此输出
        except Exception:
            len_channelid_youtube_ids_update = len(channelid_youtube_ids_update)
            count_channelid_youtube_ids_update = 1
            for channelid_key, channelid_value in channelid_youtube_ids_update.items():
                if channelid_key in youtube_content_ytid_update:
                    print_channelid_youtube_ids_update += (
                        f"\033[32m{channelid_value}\033[0m"
                    )
                else:
                    print_channelid_youtube_ids_update += (
                        f"\033[33m{channelid_value}\033[0m"
                    )
                if count_channelid_youtube_ids_update != len_channelid_youtube_ids_update:
                    if count_channelid_youtube_ids_update % 2 != 0:
                        print_channelid_youtube_ids_update += " | "
                    else:
                        print_channelid_youtube_ids_update += "\n"
                    count_channelid_youtube_ids_update += 1
        write_log(print_channelid_youtube_ids_update)

# YouTube视频信息模块
def get_youtube_video_format(yt_id, stop_flag, youtube_video_format_lock):
    ytid_update_format = video_format(
        "https://www.youtube.com/watch?v=",
        yt_id,
        youtube_content_ytid_update_format[yt_id]["media"],
        youtube_content_ytid_update_format[yt_id]["quality"],
    )
    if isinstance(ytid_update_format, list):
        youtube_content_ytid_update_format[yt_id]["format"] = ytid_update_format
    else:
        with youtube_video_format_lock:
            stop_flag[0] = "error"
            time.sleep(0.5)
            yt_id_failed.append(yt_id)
            write_log(
                f"{channelid_youtube_ids[youtube_content_ytid_update_format[yt_id]['id']]}|{yt_id}|{ytid_update_format}",
                None,
                True,
                False,
            )
            del youtube_content_ytid_update_format[yt_id]

# YouTube获取视频信息多线程模块
def get_youtube_video_format_multithreading(youtube_content_ytid_update_format_item, wait_animation_display_info):
    def before_youtube_video_format(stop_flag):
        # 创建线程锁
        youtube_video_format_lock = threading.Lock()
        # 创建线程列表
        youtube_content_ytid_update_threads = []
        for yt_id in youtube_content_ytid_update_format_item.keys():
            thread = threading.Thread(target=get_youtube_video_format, args=(yt_id, stop_flag, youtube_video_format_lock))
            youtube_content_ytid_update_threads.append(thread)
            thread.start()
        # 等待所有线程完成
        for thread in youtube_content_ytid_update_threads:
            thread.join()
        stop_flag[0] = "end"

    # 创建共享的标志变量
    stop_flag = ["keep"]  # 使用列表来存储标志变量
    # 创建两个线程分别运行等待动画和其他代码，并传递共享的标志变量
    prepare_youtube_animation = threading.Thread(target=wait_animation, args=(stop_flag, wait_animation_display_info,))
    prepare_youtube_get = threading.Thread(target=before_youtube_video_format, args=(stop_flag,))
    # 启动两个线程
    prepare_youtube_animation.start()
    prepare_youtube_get.start()
    # 等待两个线程结束
    prepare_youtube_animation.join()
    prepare_youtube_get.join()

# 获取YouTube视频格式信息模块
def get_youtube_format():
    for ytid_key, ytid_value in youtube_content_ytid_update.items():
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
            yt_id_format = {"id": ytid_key, "media": yt_id_file, "quality": yt_id_quality}
            youtube_content_ytid_update_format[yt_id] = yt_id_format
    # 按参数拆分获取量
    if len(youtube_content_ytid_update_format) != 0:
        youtube_content_ytid_update_format_list = split_dict(youtube_content_ytid_update_format, config["preparation_per_count"])
        wait_animation_num = 1
        for youtube_content_ytid_update_format_item in youtube_content_ytid_update_format_list:
            if len(youtube_content_ytid_update_format_list) == 1:
                wait_animation_display_info = "YouTube视频 "
            else:
                wait_animation_display_info = f"YouTube视频|No.{str(wait_animation_num).zfill(2)} "
            wait_animation_num += 1
            # 获取视频信息多线程模块
            get_youtube_video_format_multithreading(youtube_content_ytid_update_format_item, wait_animation_display_info)

# 下载YouTube视频
def youtube_download():
    for yt_id in youtube_content_ytid_update_format.keys():
        if dl_aideo_video(
            yt_id,
            youtube_content_ytid_update_format[yt_id]["id"],
            youtube_content_ytid_update_format[yt_id]["media"],
            youtube_content_ytid_update_format[yt_id]["format"],
            config["retry_count"],
            "https://www.youtube.com/watch?v=",
            channelid_youtube_ids[youtube_content_ytid_update_format[yt_id]["id"]],
        ):
            yt_id_failed.append(yt_id)
            write_log(
                f"{channelid_youtube_ids[youtube_content_ytid_update_format[yt_id]['id']]}|{yt_id} \033[31m无法下载\033[0m"
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
    # 查看标题中是否有频道名称如无添加到描述中
    if channelid_title not in html.unescape(title):
        if description == "":
            description = f"『{html.escape(channelid_title)}』{description}"
        else:
            description = f"『{html.escape(channelid_title)}』\n{description}"
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
        get_duration_ffprobe(
            f"channel_audiovisual/{output_dir}/{video_url}.{output_format}"
        )
    )
    # 回显对应的item
    return f"""
        <item>
            <guid>{video_url}</guid>
            <title>{title}</title>
            <link>{video_website}{video_url}</link>
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

# 生成YouTube的item模块
def youtube_xml_item(entry):
    # 输入时间字符串和原始时区
    time_str = re.search(r"(?<=<published>).+(?=</published>)", entry).group()
    original_tz = timezone.utc  # 原始时区为UTC
    # 解析时间字符串并转换为datetime对象
    dt = datetime.fromisoformat(time_str[:-6]).replace(tzinfo=original_tz)
    # 转换为目标时区
    target_tz = timezone(timedelta(seconds=-(time.timezone + time.daylight)))
    dt_target = dt.astimezone(target_tz)
    # 格式化为目标时间字符串
    target_format = "%a, %d %b %Y %H:%M:%S %z"
    pubDate = dt_target.strftime(target_format)
    output_dir = re.search(r"(?<=<yt:channelId>).+(?=</yt:channelId>)", entry).group()
    description = re.search(
        r"(?<=<media:description>).+(?=</media:description>)",
        re.sub(r"\n+", "\n", entry),
        flags=re.DOTALL,
    )
    description = description.group() if description else ""
    return xml_item(
        re.search(r"(?<=<yt:videoId>).+(?=</yt:videoId>)", entry).group(),
        output_dir,
        "https://youtube.com/watch?v=",
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
    url = re.search(r"UC.{22}/.{11}\.(m4a|mp4)", url).group()
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
    for youtube_key in channelid_youtube_ids.keys():
        if youtube_key not in get_xmls_original.keys():
            try:
                with open(
                    f"channel_rss/{youtube_key}.xml", "r", encoding="utf-8"
                ) as file:  # 打开文件进行读取
                    youtube_rss_original = file.read()  # 读取文件内容
                    get_xmls_original[youtube_key] = youtube_rss_original.split(
                        f"<!-- {{{youtube_key}}} -->\n"
                    )[1]
            except FileNotFoundError:  # 文件不存在直接更新
                write_log(f"RSS文件中不存在 {channelid_youtube_ids[youtube_key]} 无法保留原节目")
    # 生成原始rss的哈希值
    hash_rss_original = rss_create_hash(rss_original)
    return get_xmls_original, hash_rss_original

# 获取youtube频道简介模块
def get_youtube_introduction():
    # 创建线程锁
    youtube_xml_get_lock = threading.Lock()

    # 使用http获取youtube频道简介和图标模块
    def youtube_xml_get(output_dir):
        if channel_about := http_client(
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
    file_xml = channelid_youtube_rss[output_dir].text  # 获取最新的rss信息
    entrys = re.findall(r"<entry>.+?</entry>", file_xml, re.DOTALL)
    entry_num = 0
    for entry in entrys:
        if (
            re.search(r"(?<=<yt:videoId>).+(?=</yt:videoId>)", entry).group()
            not in yt_id_failed
        ):
            items_list.append(f"{youtube_xml_item(entry)}<!-- {output_dir} -->")
        entry_num += 1
        if (
            entry_num
            >= channelid_youtube[channelid_youtube_ids[output_dir]]["update_size"]
        ):
            break
    items_guid = re.findall(r"(?<=<guid>).+?(?=</guid>)", "".join(items_list))
    entry_count = channelid_youtube[channelid_youtube_ids[output_dir]][
        "last_size"
    ] - len(items_guid)
    if xmls_original and output_dir in xmls_original and entry_count > 0:
        xml_num = 0
        for xml in xmls_original[output_dir].split(f"<!-- {output_dir} -->"):
            xml_guid = re.search(r"(?<=<guid>).+(?=</guid>)", xml)
            if xml_guid and xml_guid.group() not in items_guid and xml_guid.group() not in yt_id_failed:
                items_list.append(f"{xml_original_item(xml)}<!-- {output_dir} -->")
                xml_num += 1
            if xml_num >= entry_count:
                break
    update_text = "无更新"
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
        update_text = "已更新"
    category = config["category"]
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
    if channelid_youtube[channelid_youtube_ids[output_dir]]["DisplayRSSaddress"]:
        print(f"{datetime.now().strftime('%H:%M:%S')}|{channelid_youtube_ids[output_dir]} 播客{update_text}|地址:\n\033[34m{config['url']}/channel_rss/{output_dir}.xml\033[0m")
    if (
        channelid_youtube[channelid_youtube_ids[output_dir]]["DisplayRSSaddress"]
        and channelid_youtube[channelid_youtube_ids[output_dir]]["QRcode"]
    ):
        qr_code(f"{config['url']}/channel_rss/{output_dir}.xml")
    return items

# 生成主rss模块
def create_main_rss():
    for output_dir in channelid_youtube_ids:
        items = youtube_xml_items(output_dir)
        if channelid_youtube[channelid_youtube_ids[output_dir]]["InmainRSS"]:
            all_items.append(items)
        all_youtube_content_ytid[output_dir] = re.findall(
            r"(?<=UC.{22}/)(.+\.m4a|.+\.mp4)(?=\")", items
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
        write_log("无更新内容将不进行备份")
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

# 删除已抛弃的媒体文件夹模块
def remove_dir():
    folder_names = [
        folder
        for folder in os.listdir("channel_audiovisual")
        if os.path.isdir(f"channel_audiovisual/{folder}")
    ]
    folder_names = [name for name in folder_names if re.match(r"UC.{22}", name)]
    for name in folder_names:
        if name not in channelid_youtube_ids_original:
            os.system(f"rm -r channel_audiovisual/{name}")
            write_log(f"{name}文件夹已删除")

# 补全缺失媒体文件到字典模块
def make_up_file():
    for output_dir in channelid_youtube_ids:
        for file_name in all_youtube_content_ytid[output_dir]:
            if file_name not in os.listdir(f"channel_audiovisual/{output_dir}"):
                video_id_format = {"id": output_dir, "media": file_name.split(".")[1]}
                if file_name.split(".")[0] == "mp4":
                    video_quality = channelid_youtube[channelid_youtube_ids[output_dir]][
                        "quality"
                    ]
                else:
                    video_quality = 480
                video_id_format["quality"] = video_quality
                make_up_file_format[file_name.split(".")[0]] = video_id_format

# 补全在rss中缺失的媒体格式信息模块
def make_up_file_format_mod():
    # 判断是否补全
    if len(make_up_file_format) != 0:
        print(f"{datetime.now().strftime('%H:%M:%S')}|补全缺失媒体 \033[34m下载准备中...\033[0m")
    # 创建线程锁
    makeup_yt_format_lock = threading.Lock()

    def makeup_yt_format(yt_id):
        makeup_ytid_format = video_format(
            "https://www.youtube.com/watch?v=",
            yt_id,
            make_up_file_format[yt_id]["media"],
            make_up_file_format[yt_id]["quality"],
        )
        if isinstance(makeup_ytid_format, list):
            make_up_file_format[yt_id]["format"] = makeup_ytid_format
        else:
            with makeup_yt_format_lock:
                write_log(
                    f"{channelid_youtube_ids[make_up_file_format[yt_id]['id']]}|{yt_id}|{makeup_ytid_format}"
                )
                make_up_file_format_fail[yt_id] = make_up_file_format[yt_id]['id']  # 将无法补全的媒体添加到失败字典中
                del make_up_file_format[yt_id]

    # 创建线程列表
    makeup_yt_format_threads = []
    for yt_id in make_up_file_format.keys():
        thread = threading.Thread(target=makeup_yt_format, args=(yt_id,))
        makeup_yt_format_threads.append(thread)
        thread.start()
    # 等待所有线程完成
    for thread in makeup_yt_format_threads:
        thread.join()

# 下载补全YouTube视频模块
def make_up_file_mod():
    for yt_id in make_up_file_format.keys():
        write_log(
            f"{channelid_youtube_ids[make_up_file_format[yt_id]['id']]}|{yt_id} 缺失并重新下载"
        )
        if dl_aideo_video(
            yt_id,
            make_up_file_format[yt_id]["id"],
            make_up_file_format[yt_id]["media"],
            make_up_file_format[yt_id]["format"],
            config["retry_count"],
            "https://www.youtube.com/watch?v=",
            channelid_youtube_ids[make_up_file_format[yt_id]["id"]],
        ):
            yt_id_failed.append(yt_id)
            write_log(
                f"{channelid_youtube_ids[make_up_file_format[yt_id]['id']]}|{yt_id} \033[31m无法下载\033[0m"
            )

# 删除无法补全的媒体模块
def del_makeup_yt_format_fail(overall_rss):
    for yt_id in make_up_file_format_fail.keys():
        pattern_youtube_fail_item = rf'<!-- {make_up_file_format_fail[yt_id]} -->(?:(?!<!-- {make_up_file_format_fail[yt_id]} -->).)+?<guid>{yt_id}</guid>.+?<!-- {make_up_file_format_fail[yt_id]} -->'
        replacement_youtube_fail_item = f'<!-- {make_up_file_format_fail[yt_id]} -->'
        overall_rss = re.sub(pattern_youtube_fail_item, replacement_youtube_fail_item, overall_rss, flags=re.DOTALL)
    return overall_rss

# 主更新模块
def main_update():
    # 设置全局变量
    global channelid_youtube_ids_update, youtube_content_ytid_update, channelid_youtube_rss, yt_id_failed, youtube_content_ytid_update_format, hash_rss_original, xmls_original, youtube_xml_get_tree, all_youtube_content_ytid, all_items, overall_rss, make_up_file_format, make_up_file_format_fail, server_process_print_flag
    # 根据日出日落修改封面(只适用原封面)
    channge_icon()
    # 更新Youtube频道xml
    update_youtube_rss()
    # 输出需要更新的信息
    update_information_display()
    # 暂停进程打印
    server_process_print_flag[0] = "pause"
    # 获取YouTube视频格式信息
    get_youtube_format()
    # 恢复进程打印
    server_process_print_flag[0] = "keep"
    # 暂停进程打印
    server_process_print_flag[0] = "pause"
    # 下载YouTube视频
    youtube_download()
    # 恢复进程打印
    server_process_print_flag[0] = "keep"
    # 获取原始xml字典和rss文本
    xmls_original, hash_rss_original = get_original_rss()
    # 获取youtube频道简介
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
    qr_code(f"{config['url']}/{config['filename']}.xml")
    # 恢复进程打印
    server_process_print_flag[0] = "keep"
    # 备份主rss
    backup_zip_save(overall_rss)
    # 暂停进程打印
    server_process_print_flag[0] = "pause"
    # 下载补全YouTube视频模块
    make_up_file_mod()
    # 恢复进程打印
    server_process_print_flag[0] = "keep"

    # 清空变量内数据
    channelid_youtube_ids_update.clear()  # 需更新的YouTube频道字典
    youtube_content_ytid_update.clear()  # 需下载YouTube视频字典
    channelid_youtube_rss.clear()  # YouTube频道最新Rss Response字典
    yt_id_failed.clear()  # YouTube视频下载失败列表
    youtube_content_ytid_update_format.clear()  # YouTube视频下载的详细信息字典
    hash_rss_original = ""  # 原始rss哈希值文本
    xmls_original.clear()  # 原始xml信息字典
    youtube_xml_get_tree.clear()  # YouTube频道简介和图标字典
    all_youtube_content_ytid.clear()  # 所有YouTube视频id字典
    all_items.clear()  # 更新后所有item明细列表
    overall_rss = ""  # 更新后的rss文本
    make_up_file_format.clear()  # 补全缺失媒体字典
    make_up_file_format_fail.clear()  # 补全缺失媒体失败字典

#获取配置文件config
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
# 读取youtube频道的id
channelid_youtube_ids = get_channelid_id(channelid_youtube)
# 复制youtube频道id用于删除已抛弃的媒体文件夹
channelid_youtube_ids_original = channelid_youtube_ids.copy()
# 读取bilibili频道的id
channelid_bilibili_ids = get_channelid_id(channelid_bilibili)

# 尝试获取命令行参数
try:
    argument = sys.argv[1]
except IndexError:
    argument = None
# 判断命令行参数
if argument == "a-shell" or ".json" in argument:
    update_num = 1
else:
    try:
        argument = int(argument)
        update_num = argument if isinstance(argument, int) and argument > 0 else 1
    except ValueError:
        update_num = -1
# 启动 RangeHTTPServer
httpserver_process = subprocess.Popen(["python3", "-m", "RangeHTTPServer"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
# 进程打印标志初始化
server_process_print_flag = ["keep"]

# 进程打印模块
def server_process_print():
    global httpserver_process, server_process_print_flag
    need_keep = ""
    while True:
        output = httpserver_process.stdout.readline().decode().strip()
        if need_keep == "":
            need_keep = output
        elif output != "" and output != "\n":
            need_keep += f"\n{output}"
        if server_process_print_flag[0] == "keep":
            print(need_keep)
            need_keep = ""
        if server_process_print_flag[0] == "end":
            break
        time.sleep(0.1)

# 循环主更新模块
def circulate_main_update(num):
    global httpserver_process, argument, server_process_print_flag
    while num > 0 or num == -1:
        main_update()
        if num != -1:
            num -= 1
        if argument == "a-shell":
            openserver_process = subprocess.Popen(
                ["open", "shortcuts://run-shortcut?name=Podflow&input=text&text=http"]
            )
            # 延时
            time.sleep(60)
            openserver_process.terminate()
            break
        elif num == 0:
            break
        else:
            # 延时
            time.sleep(30)
    httpserver_process.terminate()
    server_process_print_flag[0] = "end"

# 创建两个线程分别执行输出和终止操作
prepare_print = threading.Thread(target=server_process_print)
prepare_update = threading.Thread(target=circulate_main_update, args=(update_num,))

# 启动两个线程
prepare_print.start()
prepare_update.start()

# 等待两个线程结束
prepare_print.join()
prepare_update.join()