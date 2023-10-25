#!/usr/bin/env python
# coding: utf-8

# In[2]:


import os
import re
import sys
import html
import json
import math
import time
import threading
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

#默认参数
default_config = {
    "retry_count": 5,
    "url": "http://127.0.0.1:8000",
    "title": "Podflow",
    "filename": "YouTube",
    "link": "https://m.youtube.com",
    "description": "在YouTube 上畅享您喜爱的视频和音乐上传原创内容并与亲朋好友和全世界观众分享您的视频。",
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
            "QRcode": False
        }
    }
}
# 如果InmainRSS为False或频道有更新则无视DisplayRSSaddress的状态, 都会变为True。


# In[3]:


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


# In[4]:


#日志模块
def write_log(log, suffix = None, display = True):
    # 获取当前的具体时间
    current_time = datetime.now()
    # 格式化输出, 只保留年月日时分秒
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    # 打开文件, 并读取原有内容
    try:
        with open("log.txt", "r") as file:
            contents = file.read()
    except FileNotFoundError:
        contents = ""
    # 将新的日志内容添加在原有内容之前
    log_in = re.sub(r"\033\[[0-9;]+m", "", log)
    new_contents = f"{formatted_time} {log_in}\n{contents}"
    # 将新的日志内容写入文件
    file_save(new_contents, "log.txt")
    if display:
        formatted_time_mini = current_time.strftime("%H:%M:%S")
        if suffix:
            print(f"{formatted_time_mini}|{log}|{suffix}")
        else:
            print(f"{formatted_time_mini}|{log}")


# In[5]:


# 查看requests模块是否安装
ffmpeg_worry = '''\033[0mFFmpeg安装方法:
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
\033[32mffmpeg -version\033[0m'''
try:
    # 执行 ffmpeg 命令获取版本信息
    result = subprocess.run(['ffmpeg', '-version'], capture_output = True, text = True)
    output = result.stdout.lower()
    # 检查输出中是否包含 ffmpeg 版本信息
    if 'ffmpeg version' not in output:
        write_log("FFmpeg 未安装, 请安装后重试")
        print(ffmpeg_worry)
        sys.exit(0)
except FileNotFoundError:
        write_log("FFmpeg 未安装, 请安装后重试")
        print(ffmpeg_worry)
        sys.exit(0)

# 查看requests模块是否安装并安装
try:
    import requests
    # 如果导入成功你可以在这里使用requests库
except ImportError:
    try:
        subprocess.run(['pip', 'install', 'chardet' , '-U'], capture_output = True, text = True)
        subprocess.run(['pip', 'install', 'requests' , '-U'], capture_output = True, text = True)
        write_log("\033[31mrequests安装成功, 请重新运行\033[0m")
        sys.exit(0)
    except FileNotFoundError:
        write_log("\033[31mrequests安装失败请重试\033[0m")
        sys.exit(0)


# In[6]:


# HTTP GET请求重试模块
def get_with_retry(url, name, max_retries = 10, retry_delay = 6):
    for num in range(max_retries):
        try:
            response = requests.get(f"{url}")
            response.raise_for_status()
        except Exception:
            print(f"{datetime.now().strftime('%H:%M:%S')}|{name}|\033[31m连接异常重试中...\033[97m{num + 1}\033[0m")
        else:
            return response
        time.sleep(retry_delay)
    print(f"{datetime.now().strftime('%H:%M:%S')}|{name}|\033[31m达到最大重试次数\033[97m{max_retries}\033[0m")
    return None

#批量正则表达式替换删除模块
def vary_replace(varys, text):
    for vary in varys:
        text = re.sub(vary, '', text)
    return text


# In[7]:


# 安装库模块
def library_install(library ,library_install_dic = None):
    if version := re.search(
        r"(?<=Version\: ).+",
        subprocess.run(
            ["pip", "show", library], capture_output = True, text = True
        ).stdout
    ):
        write_log(f"{library}已安装")
        if library in library_install_dic:
            version_update = library_install_dic[library]
        else:
            # 获取最新版本编号
            version_update = get_with_retry(f"https://pypi.org/project/{library}/", f"{library}", 2, 2)
            if version_update:
                version_update = re.search(
                    r"(?<=<h1 class=\"package-header__name\">).+?(?=</h1>)",
                    version_update.text,
                    flags=re.DOTALL
                )
        # 如果库已安装, 判断是否为最新
        if version_update is None or version.group() not in version_update.group():
            # 如果库已安装, 则尝试更新
            try:
                subprocess.run(['pip', 'install', '--upgrade', library], capture_output = True, text = True)
                write_log(f"{library}更新成功")
            except FileNotFoundError:
                write_log(f"{library}更新失败")
        else:
            write_log(f"{library}无需更新|版本：\033[32m{version.group()}\033[0m")
    else:
        write_log(f"{library}未安装")
        # 如果库未安装, 则尝试安装
        try:
            subprocess.run(['pip', 'install', library , '-U'], capture_output = True, text = True)
            write_log(f"{library}安装成功")
        except FileNotFoundError:
            write_log(f"{library}安装失败")
            sys.exit(0)


# In[8]:


# 安装/更新并加载三方库
library_install_list = ["yt-dlp", "RangeHTTPServer", "chardet", "requests", "astral", "qrcode"]
library_install_dic = {}
def library_install_get(library):
    # 获取最新版本编号
    version_update = get_with_retry(f"https://pypi.org/project/{library}/", f"{library}", 2, 2)
    if version_update:
        version_update = re.search(
            r"(?<=<h1 class=\"package-header__name\">).+?(?=</h1>)",
            version_update.text,
            flags=re.DOTALL
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
for library in library_install_list:
    library_install(library ,library_install_dic)

import qrcode
import yt_dlp
from astral.sun import sun
from astral import LocationInfo


# In[9]:


# 格式化时间模块
def time_format(duration):
    if duration is None:
        return "Unknown"
    duration = int(duration)
    hours, remaining_seconds = divmod(duration, 3600)
    minutes = remaining_seconds // 60
    remaining_seconds = remaining_seconds % 60
    if hours > 0:
        return '{:02}:{:02}:{:02}'.format(hours, minutes, remaining_seconds)
    else:
        return '{:02}:{:02}'.format(minutes, remaining_seconds)

# 格式化字节模块
def convert_bytes(byte_size, units = None, outweigh = 1024):
    if units is None:
        units = [' B', 'KB', 'MB', 'GB']
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

#网址二维码模块
def qr_code(data):
    # 创建一个QRCode对象
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=0)
    # 设置二维码的数据
    qr.add_data(data)
    # 获取QR Code矩阵
    qr.make(fit=True)
    matrix = qr.make_image(fill_color="black", back_color="white").modules
    # 获取图像的宽度和高度
    width, height = len(matrix), len(matrix)
    height_double = math.ceil(height/2)
    # 转换图像为ASCII字符
    fonts = ["▀", "▄", "█", " "]
    ascii_art = ""
    for y in range(height_double):
        if (y+1)*2-1 >= height:
            for x in range(width):
                if matrix[(y+1)*2-2][x] is True:
                    ascii_art += fonts[0]
                else:
                    ascii_art += fonts[3]
        else:
            for x in range(width):
                if matrix[(y+1)*2-2][x] is True and matrix[(y+1)*2-1][x] is True:
                    ascii_art += fonts[2]
                elif matrix[(y+1)*2-2][x] is True and matrix[(y+1)*2-1][x] is False:
                    ascii_art += fonts[0]
                elif matrix[(y+1)*2-2][x] is False and matrix[(y+1)*2-1][x] is True:
                    ascii_art += fonts[1]
                else:
                    ascii_art += " "
            ascii_art += "\n"
    print(ascii_art)


# In[10]:


# 下载显示模块
def show_progress(stream):
    stream = dict(stream)
    if "downloaded_bytes" in stream:
        downloaded_bytes = convert_bytes(stream['downloaded_bytes']).rjust(9)
    else:
        downloaded_bytes = " Unknow B"
    if "total_bytes" in stream:
        total_bytes = convert_bytes(stream['total_bytes'])
    else:
        total_bytes = "Unknow B"
    if stream['speed'] is None:
        speed = " Unknow B"
    else:
        speed = convert_bytes(stream['speed'], [' B', 'KiB', 'MiB', 'GiB'], 1000).rjust(9)
    if stream['status'] in ["downloading", "error"]:
        if "total_bytes" in stream:
            bar = stream['downloaded_bytes'] / stream['total_bytes'] * 100
        else:
            bar = 0
        bar = f"{bar:.1f}" if bar == 100 else f"{bar:.2f}"
        bar = bar.rjust(5)
        eta = time_format(stream['eta']).ljust(8)
        print((f"\r\033[94m{bar}%\033[0m|{downloaded_bytes}\{total_bytes}|\033[32m{speed}/s\033[0m|\033[93m{eta}\033[0m"),end = "")
    if stream['status'] == "finished":
        if "elapsed" in stream:
            elapsed = time_format(stream['elapsed']).ljust(8)
        else:
            elapsed = "Unknown "
        print((f"\r100.0%|{downloaded_bytes}\{total_bytes}|\033[32m{speed}/s\033[0m|\033[97m{elapsed}\033[0m"))


# In[11]:


# 获取媒体时长和ID模块
def video_format(video_website, video_url, media = "m4a", quality = "480"):
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
                'no_warnings': True, 
                'quiet': True,  # 禁止非错误信息的输出
                'logger': MyLogger()
            }
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            # 使用提供的 URL 提取视频信息
            if info_dict := ydl.extract_info(
                f"{video_website}{video_url}", download = False
            ):
                # 获取视频时长并返回
                duration = info_dict.get('duration')
                formats = info_dict.get('formats')
        except Exception as e:
            fail_message = (f"\033[31m获取信息失败\033[0m\n错误信息：{str(e)}").replace("ERROR: ", "").replace(f"{video_url}: ", "").replace("[youtube] ","")
        return fail_message, duration, formats
    error_reason = {
        "Premieres in ": "预播节目|",
        "Premieres ": "预播节目|"
    }
    yt_id_count, change_error= 0, None
    fail_message, duration, formats = duration_and_formats(video_website, video_url)
    if fail_message:
        for key in error_reason.keys():
            if key in fail_message:
                change_error = [key, error_reason[key]]
                break
    if change_error:
        fail_message = fail_message.replace(change_error[0], change_error[1])
    else:
        while yt_id_count < 2 and (fail_message is not None or duration is None or formats is None):
            yt_id_count += 1
            print(f"{datetime.now().strftime('%H:%M:%S')}|{video_url} 无法获取媒体信息\n开始第\033[34m{yt_id_count}\033[0m次重试")
            fail_message, duration, formats = duration_and_formats(video_website, video_url)
    if fail_message is None:
        if duration == "" or duration is None:
            return f"\033[31m获取信息失败\033[0m\n错误信息：无法获取媒体时长"
        if formats == "" or formats is None:
            return f"\033[31m获取信息失败\033[0m\n错误信息：无法获取媒体格式"
        duration_and_id = []
        duration_and_id.append(duration)
        # 定义条件判断函数
        def check_resolution(item):
            if "aspect_ratio" in item and (isinstance(item["aspect_ratio"], float) or isinstance(item["aspect_ratio"], int)):
                if item["aspect_ratio"] >= 1:
                    return item["height"] <= int(quality)
                else:
                    return item["width"] <= int(quality)
            else:
                return False
        def check_ext(item, media):
            if "ext" in item:
                return item["ext"] == media
            else:
                return False
        def check_vcodec(item):
            if "vcodec" in item:
                return "vp" not in item["vcodec"].lower() and "av01" not in item["vcodec"].lower()
            else:
                return False
        #获取最好质量媒体的id
        def best_format_id(formats):
            filesize_max = 0
            format_id_best = ""
            vcodec_best = ""
            for format in formats:
                if "filesize" in format and (isinstance(format["filesize"], float) or isinstance(format["filesize"], int)) and format["filesize"] > filesize_max:
                    filesize_max = format["filesize"]
                    format_id_best = format["format_id"]
                    vcodec_best = format["vcodec"]
            return format_id_best, vcodec_best
        # 进行筛选
        formats_m4a = list(filter(lambda item: check_ext(item, "m4a") and check_vcodec(item), formats))
        (best_formats_m4a, vcodec_best) = best_format_id(formats_m4a)
        if best_formats_m4a == "" or best_formats_m4a is None:
            return f"\033[31m获取信息失败\033[0m, \n错误信息：无法获取音频格式ID"
        else:
            duration_and_id.append(best_formats_m4a)
            if media == "mp4":
                formats_mp4 = list(filter(lambda item: check_resolution(item) and check_ext(item, "mp4") and check_vcodec(item), formats))
                (best_formats_mp4, vcodec_best) = best_format_id(formats_mp4)
                if best_formats_mp4 == ""or best_formats_mp4 is None:
                    return f"\033[31m获取信息失败\033[0m, \n错误信息：无法获取视频格式ID"
                else:
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
            "ffprobe",                       # ffprobe 命令
            "-i", file_path,                 # 输入文件路径
            "-show_entries", "format",  # 显示时长信息
            "-v", "error",
        ]
        # 执行命令并获取输出
        output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode("utf-8")
        output = re.search(r"(?<=duration.)[0-9]+\.?[0-9]*", output)
        if output:
            return math.ceil(float(output.group()))
        else:
            return None
    except subprocess.CalledProcessError as e:
        write_log(f"Error: {e.output}")
        return None

# 下载视频模块
def download_video(video_url, output_dir, output_format, format_id, video_website, video_write_log, format_code = "480", sesuffix = ""):
    class MyLogger:
        def debug(self, msg):
            pass
        def warning(self, msg):
            pass
        def info(self, msg):
            pass
        def error(self, msg):
            print(msg.replace("ERROR: ", "").replace(f"{video_url}: ", "").replace("[youtube] ",""))
    ydl_opts = {
        'outtmpl': f'{output_dir}/{video_url}{sesuffix}.{output_format}',  # 输出文件路径和名称
        'format': f'{format_id}',  # 指定下载的最佳音频和视频格式
        "noprogress": True,
        'quiet': True,
        "progress_hooks": [show_progress],
        'logger': MyLogger()
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'{video_website}{video_url}'])  # 下载指定视频链接的视频
    except Exception as e:
        write_log((f"{video_write_log} \033[31m下载失败\033[0m\n错误信息：{str(e)}").replace("ERROR: ", "").replace(f"{video_url}: ", "")).replace("[youtube] ","")  # 写入下载失败的日志信息
        return video_url


# In[12]:


# 视频完整下载模块
def dl_full_video(video_url, output_dir, output_format, format_id, id_duration, video_website, video_write_log, format_code = "480", sesuffix = ""):
    if download_video(video_url, output_dir, output_format, format_id, video_website, video_write_log, format_code, sesuffix):
        return video_url
    duration_video = get_duration_ffprobe(f"{output_dir}/{video_url}{sesuffix}.{output_format}")  # 获取已下载视频的实际时长
    if abs(id_duration - duration_video) <= 1:  # 检查实际时长与预计时长是否一致
        return None
    if duration_video:
        write_log(f"{video_write_log} \033[31m下载失败\033[0m\n错误信息：视频不完整({id_duration}|{duration_video})")
        os.remove(f"{output_dir}/{video_url}{sesuffix}.{output_format}")  #删除不完整的视频
    return video_url

# 视频重试下载模块
def dl_retry_video(video_url, output_dir, output_format, format_id, id_duration, retry_count, video_website, video_write_log, format_code = "480", sesuffix = ""):
    yt_id_failed = dl_full_video(video_url, output_dir, output_format, format_id, id_duration, video_website, video_write_log, format_code, sesuffix)
    # 下载失败后重复尝试下载视频
    yt_id_count = 0
    while yt_id_count < retry_count and yt_id_failed:
        yt_id_count += 1
        write_log(f"{video_write_log}第\033[34m{yt_id_count}\033[0m次重新下载")
        yt_id_failed = dl_full_video(video_url, output_dir, output_format, format_id, id_duration, video_website, video_write_log, format_code, sesuffix)
    return yt_id_failed

# 音视频总下载模块
def dl_aideo_video(video_url, output_dir, output_format, video_format, retry_count, video_website, format_code = "480", output_dir_name=""):
    if output_dir_name:
        video_write_log = f"\033[95m{output_dir_name}\033[0m|{video_url}"
    else:
        video_write_log = video_url
    id_duration = video_format[0]
    print(f"{datetime.now().strftime('%H:%M:%S')}|{video_write_log} \033[34m开始下载\033[0m", end = "")
    if output_format == "m4a":
        print(f" \033[97m{video_format[1]}\033[0m")
        yt_id_failed = dl_retry_video(video_url, output_dir, "m4a", video_format[1], id_duration, retry_count, video_website, video_write_log, format_code, "")
    else:
        print(f"\n{datetime.now().strftime('%H:%M:%S')}|\033[34m开始视频部分下载\033[0m\033[97m{video_format[2]}\033[0m")
        yt_id_failed = dl_retry_video(video_url, output_dir, "mp4", video_format[2], id_duration, retry_count, video_website, video_write_log, format_code, ".part")
        if yt_id_failed is None:
            print(f"{datetime.now().strftime('%H:%M:%S')}|\033[34m开始音频部分下载\033[0m\033[97m{video_format[1]}\033[0m")
            yt_id_failed = dl_retry_video(video_url, output_dir, "m4a", video_format[1], id_duration, retry_count, video_website, video_write_log, format_code, ".part")
            if yt_id_failed is None:
                print(f"{datetime.now().strftime('%H:%M:%S')}|\033[34m开始合成...\033[0m", end = "")
                # 构建FFmpeg命令
                ffmpeg_cmd = [
                    'ffmpeg',
                    "-v", "error",
                    '-i', f'{output_dir}/{video_url}.part.mp4',
                    '-i', f'{output_dir}/{video_url}.part.m4a',
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    f'{output_dir}/{video_url}.mp4'
                ]
                # 执行FFmpeg命令
                try:
                    subprocess.run(ffmpeg_cmd, check=True, capture_output = True, text = True)
                    print(f" \033[32m合成成功\033[0m")
                    os.remove(f"{output_dir}/{video_url}.part.mp4")
                    os.remove(f"{output_dir}/{video_url}.part.m4a")
                except subprocess.CalledProcessError as e:
                    yt_id_failed = video_url
                    write_log(f"\n{video_write_log} \033[31m下载失败\033[0m\n错误信息：合成失败:{e}") 
    if yt_id_failed is None:
        write_log(f"{video_write_log} \033[32m下载成功\033[0m")  # 写入下载成功的日志信息
    return yt_id_failed


# In[13]:


# 构建文件夹模块
def folder_build(folder_name):
    folder_path = os.path.join(os.getcwd(), folder_name)
    if not os.path.exists(folder_path):  # 判断文件夹是否存在
        os.makedirs(folder_path)  # 创建文件夹
        write_log(f"文件夹{folder_name}创建成功")


# In[14]:


# 检查当前文件夹中是否存在config.json文件
if not os.path.exists('config.json'):
    # 如果文件不存在, 创建并写入默认字典
    with open('config.json', 'w') as file:
        json.dump(default_config, file, indent=4)
    write_log("不存在配置文件, 已新建, 默认频道")
    config = default_config
else:
    # 如果文件存在, 读取字典并保存到config变量中
    try:
        with open('config.json', 'r') as file:
            config = json.load(file)
        write_log("已读取配置文件")
    # 如果config格式有问题, 停止运行并报错
    except Exception as e:
        write_log(f"配置文件有误, 请检查config.json, {str(e)}")
        sys.exit(0)


# In[15]:


# 对retry_count进行纠正
if (
    'retry_count' not in config
    or not isinstance(config['retry_count'], int)
    or config['retry_count'] <= 0
):
    config['retry_count'] = default_config["retry_count"]
# 对url进行纠正
if (
    'url' not in config
    or not re.search(r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", config['url'])
    ):
    config['url'] = default_config["url"]
# 对title进行纠正
if ('title' not in config):
    config['title'] = default_config["title"]
# 对filename进行纠正
if ('filename' not in config):
    config['filename'] = default_config["filename"]
# 对link进行纠正
if (
    'link' not in config
    or not re.search(r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", config['link'])
    ):
    config['link'] = default_config["link"]
# 对description进行纠正
if ('description' not in config):
    config['description'] = default_config["description"]
# 对icon进行纠正
if (
    'icon' not in config
    or not re.search(r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", config['icon'])
    ):
    config['icon'] = default_config["icon"]
# 对category进行纠正
if ('category' not in config):
    config['category'] = default_config["category"]

# 根据日出日落修改封面(只适用原封面)
if config["icon"] == default_config["icon"]:
    # 获取公网IP地址
    response = get_with_retry("https://ipinfo.io", "日出日落信息")
    if response:
        data = response.json()
        # 提取经度和纬度
        coordinates = data['loc'].split(',')
        latitude = coordinates[0]
        longitude = coordinates[1]
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
            sunrise = sun_time['sunrise']
            sunset = sun_time['sunset']
            sunrise_minus_one_hour = sunrise # - timedelta(hours=1)
            sunset_plus_one_hour = sunset # + timedelta(hours=1)
            return sunrise_minus_one_hour, sunset_plus_one_hour
        sunrise_now, sunset_now = sunrise_sunset(now)
        sunrise_yesterday, sunset_yesterday = sunrise_sunset(yesterday)
        sunrise_tommorrow, sunset_tommorrow = sunrise_sunset(tommorrow)
        # 判断现在是白天还是晚上
        if sunrise_now < sunset_now:
            if sunrise_now < now < sunset_now or sunrise_yesterday < now < sunset_yesterday  or sunrise_tommorrow < now < sunset_tommorrow:
                picture_name = "Podflow_light"
            else:
                picture_name = "Podflow_dark"
        else:
            if sunrise_now > now > sunset_now or sunrise_yesterday > now > sunset_yesterday  or sunrise_tommorrow > now > sunset_tommorrow:
                picture_name = "Podflow_dark"
            else:
                picture_name = "Podflow_light"
        print(picture_name)
        config["icon"] = f"https://raw.githubusercontent.com/gruel-zxz/podflow/main/{picture_name}.png"


# In[16]:


# 从配置文件中获取YouTube的频道
if 'channelid_youtube' in config:
    channelid_youtube = config["channelid_youtube"]
    write_log("已读取youtube频道信息")
else:
    channelid_youtube = None
    write_log("youtube频道信息不存在")
# 从配置文件中获取bilibili的频道
if 'channelid_bilibili' in config:
    channelid_bilibili = config["channelid_bilibili"]
    write_log("已读取bilibili频道信息")
else:
    channelid_bilibili = None
    write_log("bilibili频道信息不存在")


# In[17]:


# 构建文件夹channel_id
folder_build("channel_id")


# In[18]:


# 视频分辨率变量
youtube_video_media = ["m4v", "mov", "qt", "avi", "flv", "wmv", "asf", "mpeg", "mpg", "vob", "mkv", "rm", "rmvb", "vob", "ts", "dat"]
youtube_dpi = ["144", "180", "216", "240", "360", "480", "720", "1080", "1440", "2160", "4320"]
youtube_media = ["m4a", "mp4"]
# 复制字典youtube-channelid, 遍历复制后的字典进行操作以避免在循环中删除元素导致的迭代错误
channelid_youtube_copy = channelid_youtube.copy()
# 对youtube-channelid的错误进行更正
for channelid_youtube_key, channelid_youtube_value in channelid_youtube_copy.items():
    # 判断是否为字典
    if isinstance(channelid_youtube_value, str) and re.search(r"UC.{22}",channelid_youtube_value):
        channelid_youtube_value ={"id" : channelid_youtube_value}
        channelid_youtube[channelid_youtube_key] = channelid_youtube_value
    # 判断id是否正确
    if 'id' not in channelid_youtube_value or not re.search(r"UC.{22}", channelid_youtube_value['id']):
        # 删除错误的
        del channelid_youtube[channelid_youtube_key]
        write_log(f"YouTube频道 {channelid_youtube_key} ID不正确")
    else:
        # 对update_size进行纠正
        if (
            'update_size' not in channelid_youtube_value
            or not isinstance(channelid_youtube_value['update_size'], int)
            or channelid_youtube_value['update_size'] <= 0
        ):
            channelid_youtube[channelid_youtube_key]['update_size'] = default_config["channelid_youtube"]["youtube"]["update_size"]
        # 对id进行纠正
        channelid_youtube[channelid_youtube_key]['id'] = re.search(r"UC.{22}", channelid_youtube_value['id']).group()
        # 对last_size进行纠正
        if (
            'last_size' not in channelid_youtube_value
            or not isinstance(channelid_youtube_value['last_size'], int)
            or channelid_youtube_value['last_size'] <= 0
        ):
            channelid_youtube[channelid_youtube_key]['last_size'] = default_config["channelid_youtube"]["youtube"]["last_size"]
        channelid_youtube[channelid_youtube_key]['last_size'] = max(
            channelid_youtube[channelid_youtube_key]['last_size'],
            channelid_youtube[channelid_youtube_key]['update_size'],
        )
        # 对title进行纠正
        if 'title' not in channelid_youtube_value:
            channelid_youtube[channelid_youtube_key]['title'] = channelid_youtube_key
        # 对quality进行纠正
        if (
            (
                'quality' not in channelid_youtube_value
                or channelid_youtube_value['quality'] not in youtube_dpi
            )
            and 'media' in channelid_youtube_value
            and channelid_youtube_value['media'] == "mp4"
        ):
            channelid_youtube[channelid_youtube_key]['quality'] = default_config["channelid_youtube"]["youtube"]["quality"]
        # 对media进行纠正
        if (
            'media' in channelid_youtube_value
            and channelid_youtube_value['media'] not in youtube_media
            and channelid_youtube_value['media'] in youtube_video_media
        ):
            channelid_youtube[channelid_youtube_key]['media'] = "mp4"
        elif (
            'media' in channelid_youtube_value
            and channelid_youtube_value['media'] not in youtube_media
            or 'media' not in channelid_youtube_value
        ):
            channelid_youtube[channelid_youtube_key]['media'] = "m4a"
        # 对DisplayRSSaddress进行纠正
        if 'DisplayRSSaddress' not in channelid_youtube_value or not isinstance(channelid_youtube_value['DisplayRSSaddress'], bool):
            channelid_youtube[channelid_youtube_key]['DisplayRSSaddress'] = False
        # 对InmainRSS进行纠正
        if 'InmainRSS' in channelid_youtube_value and isinstance(channelid_youtube_value['InmainRSS'], bool):
            if channelid_youtube_value['InmainRSS'] is False:
                channelid_youtube[channelid_youtube_key]['DisplayRSSaddress'] = True
        else:
            channelid_youtube[channelid_youtube_key]['InmainRSS'] = True
        # 对QRcode进行纠正
        if 'QRcode' not in channelid_youtube_value or not isinstance(channelid_youtube_value['QRcode'], bool):
            channelid_youtube[channelid_youtube_key]['QRcode'] = False


# In[19]:


# 读取youtube频道的id
if channelid_youtube is not None:
    channelid_youtube_ids = dict({channel["id"]: key for key, channel in channelid_youtube.items()})
    write_log("读取youtube频道的channelid成功")
else:
    channelid_youtube_ids = None
# 读取bilibili频道的id
if channelid_bilibili is not None:
    channelid_bilibili_ids = [channelid_bilibili[key]['id'] for key in channelid_bilibili]
    write_log("读取bilibili频道的channelid成功")
else:
    channelid_bilibili_ids = None


# In[20]:


# 更新Youtube频道xml
channelid_youtube_ids_update = {}  #创建需更新的频道
youtube_content_ytid_update = {}  #创建需下载视频列表
# 判断频道id是否正确
pattern_youtube404 = r"Error 404"  # 设置要匹配的正则表达式模式
pattern_youtube_varys = [r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-2][0-9]:[0-6][0-9]:[0-6][0-9]\+00:00',
                        r'starRating count="[0-9]*"',
                        r'statistics views="[0-9]*"',
                        r'<id>yt:channel:(UC)?(.{22})?</id>',
                        r'<yt:channelId>(UC)?(.{22})?</yt:channelId>']
# 创建线程锁
youtube_need_update_lock = threading.Lock()
def youtube_need_update(youtube_key, youtube_value):
    # 构建 URL
    youtube_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={youtube_key}"
    youtube_response = get_with_retry(youtube_url, youtube_value)
    with youtube_need_update_lock:
        if youtube_response:
            youtube_content = youtube_response.text
            if re.search(pattern_youtube404, youtube_content):
                write_log(f"YouTube频道 {youtube_value} ID不正确无法获取")
                del channelid_youtube_ids[youtube_key]  # 删除错误ID
            else:
                youtube_content_clean = vary_replace(pattern_youtube_varys, youtube_content)
                # 读取原Youtube频道xml文件并判断是否要更新
                try:
                    with open(f"channel_id/{youtube_key}.txt", 'r', encoding='utf-8') as file:  # 打开文件进行读取
                        youtube_content_original = file.read()  # 读取文件内容
                        youtube_content_original_clean = vary_replace(pattern_youtube_varys, youtube_content_original)
                    if youtube_content_clean != youtube_content_original_clean :  #判断是否要更新
                        channelid_youtube_ids_update[youtube_key] = youtube_value
                        channelid_youtube[channelid_youtube_ids[youtube_key]]['DisplayRSSaddress'] = True
                except FileNotFoundError:  #文件不存在直接更新
                    channelid_youtube_ids_update[youtube_key] = youtube_value
                    channelid_youtube[channelid_youtube_ids[youtube_key]]['DisplayRSSaddress'] = True
                # 构建文件
                file_save(youtube_content, f"{youtube_key}.txt", "channel_id")
                # 构建频道文件夹
                folder_build(youtube_key)
                #获取Youtube视频ID列表
                youtube_content_ytid = re.findall(r"(?<=<id>yt:video:).{11}(?=</id>)", youtube_content)
                youtube_content_ytid = youtube_content_ytid[:channelid_youtube[youtube_value]['update_size']]
                #获取已下载媒体名称
                youtube_media = ("m4a", "mp4") if channelid_youtube[youtube_value]['media'] == "m4a" else ("mp4")
                youtube_content_ytid_original = [os.path.splitext(file)[0] for file in os.listdir(youtube_key) if file.endswith(youtube_media)]
                if youtube_content_ytid := [
                    exclude
                    for exclude in youtube_content_ytid
                    if exclude not in youtube_content_ytid_original
                ]:
                    channelid_youtube_ids_update[youtube_key] = youtube_value
                    channelid_youtube[channelid_youtube_ids[youtube_key]]['DisplayRSSaddress'] = True
                    youtube_content_ytid_update[youtube_key] = youtube_content_ytid
        else:
            write_log(f"频道 {youtube_value} 无法更新")
            if not os.path.exists(os.path.join("channel_id", f"{youtube_key}.txt")):
                del channelid_youtube_ids[youtube_key]
# 创建线程列表
youtube_need_update_threads = []
for youtube_key, youtube_value in channelid_youtube_ids.items():
    thread = threading.Thread(target=youtube_need_update, args=(youtube_key, youtube_value))
    youtube_need_update_threads.append(thread)
    thread.start()
# 等待所有线程完成
for thread in youtube_need_update_threads:
    thread.join()
if channelid_youtube_ids_update:
    write_log(f"需更新的YouTube频道:\n\033[32m{' '.join(channelid_youtube_ids_update.values())}\033[0m")


# In[37]:


# 获取YouTube视频格式信息
yt_id_failed = []
youtube_content_ytid_update_format = {}
for ytid_key, ytid_value in youtube_content_ytid_update.items():
    # 获取对应文件类型
    yt_id_file = channelid_youtube[channelid_youtube_ids_update[ytid_key]]['media']
    # 如果为视频格式获取分辨率
    if yt_id_file == "mp4":
        yt_id_quality = channelid_youtube[channelid_youtube_ids_update[ytid_key]]['quality']
    else:
        yt_id_quality = None
    for yt_id in ytid_value:
        yt_id_format ={}
        yt_id_format["id"] = ytid_key
        yt_id_format["media"] = yt_id_file
        yt_id_format["quality"] = yt_id_quality
        youtube_content_ytid_update_format[yt_id] = yt_id_format
if len(youtube_content_ytid_update_format) != 0:
    print(f"{datetime.now().strftime('%H:%M:%S')}|YouTube视频 \033[34m下载准备中...\033[0m")
# 创建线程锁
youtube_video_format_lock = threading.Lock()
def youtube_video_format(yt_id):
    ytid_update_format = video_format("https://www.youtube.com/watch?v=", yt_id, youtube_content_ytid_update_format[yt_id]["media"], youtube_content_ytid_update_format[yt_id]["quality"])
    if isinstance(ytid_update_format, list):
        youtube_content_ytid_update_format[yt_id]["format"] = ytid_update_format
    else:
        with youtube_video_format_lock:
            yt_id_failed.append(yt_id)
            write_log(f"{channelid_youtube_ids[youtube_content_ytid_update_format[yt_id]['id']]}|{yt_id} {ytid_update_format}")
            del youtube_content_ytid_update_format[yt_id]
# 创建线程列表
youtube_content_ytid_update_threads = []
for yt_id in youtube_content_ytid_update_format.keys():
    thread = threading.Thread(target=youtube_video_format, args=(yt_id,))
    youtube_content_ytid_update_threads.append(thread)
    thread.start()
# 等待所有线程完成
for thread in youtube_content_ytid_update_threads:
    thread.join()
# 下载YouTube视频
for yt_id in youtube_content_ytid_update_format.keys():
    if dl_aideo_video(
            yt_id,
            youtube_content_ytid_update_format[yt_id]['id'],
            youtube_content_ytid_update_format[yt_id]['media'],
            youtube_content_ytid_update_format[yt_id]['format'],
            config['retry_count'],
            "https://www.youtube.com/watch?v=",
            youtube_content_ytid_update_format[yt_id]['quality'],
            channelid_youtube_ids[youtube_content_ytid_update_format[yt_id]['id']]
        ):
            yt_id_failed.append(yt_id)
            write_log(f"{channelid_youtube_ids[youtube_content_ytid_update_format[yt_id]['id']]}|{yt_id} \033[31m无法下载\033[0m")


# In[22]:


#生成XML模块
def xml_rss(title,link,description,category,icon,items):
    # 获取当前时间
    current_time_now = time.time()  # 获取当前时间的秒数
    # 获取当前时区和夏令时信息
    time_info_now = time.localtime(current_time_now)
    # 构造时间字符串
    formatted_time_now = time.strftime('%a, %d %b %Y %H:%M:%S %z', time_info_now)
    itunes_summary = description.replace("\n", "&#xA;")
    if title == "Podflow":
        author = "gruel-zxz"
        subtitle = "gruel-zxz-podflow"
    else:
        author = title
        subtitle = title
    # 创建主XML信息
    return f'''<?xml version="1.0" encoding="UTF-8"?>
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
</rss>'''


# In[23]:


# 生成item模块
def xml_item(video_url, output_dir, video_website, channelid_title,title, description, pubDate, image):
    # 查看标题中是否有频道名称如无添加到描述中
    if channelid_title not in html.unescape(title):
        if description == "":
            description = f"『{html.escape(channelid_title)}』{description}"
        else:
            description = f"『{html.escape(channelid_title)}』\n{description}"
    # 更换描述换行符
    replacement_description = description.replace("\n", "&#xA;")
    # 获取文件后缀和文件字节大小
    if os.path.exists(f"{output_dir}/{video_url}.mp4"):
        video_length_bytes = os.path.getsize(f"{output_dir}/{video_url}.mp4")
        output_format = "mp4"
        video_type = "video/mp4"
    else:
        if os.path.exists(f"{output_dir}/{video_url}.m4a"):
            video_length_bytes = os.path.getsize(f"{output_dir}/{video_url}.m4a")
        else:
            video_length_bytes = 0
        output_format = "m4a"
        video_type = "audio/x-m4a"
    # 获取文件时长
    duration = time_format(get_duration_ffprobe(f"{output_dir}/{video_url}.{output_format}"))
    # 回显对应的item
    return f'''
        <item>
            <guid>{video_url}</guid>
            <title>{title}</title>
            <link>{video_website}{video_url}</link>
            <description>{replacement_description}</description>
            <pubDate>{pubDate}</pubDate>
            <enclosure url="{config["url"]}/{output_dir}/{video_url}.{output_format}" length="{video_length_bytes}" type="{video_type}"></enclosure>
            <itunes:author>{title}</itunes:author>
            <itunes:subtitle>{title}</itunes:subtitle>
            <itunes:summary><![CDATA[{description}]]></itunes:summary>
            <itunes:image href="{image}"></itunes:image>
            <itunes:duration>{duration}</itunes:duration>
            <itunes:explicit>no</itunes:explicit>
            <itunes:order>1</itunes:order>
        </item>
'''


# In[24]:


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
    target_format = '%a, %d %b %Y %H:%M:%S %z'
    pubDate = dt_target.strftime(target_format)
    output_dir = re.search(r"(?<=<yt:channelId>).+(?=</yt:channelId>)", entry).group()
    description = re.search(r"(?<=<media:description>).+(?=</media:description>)", re.sub(r"\n+", "\n", entry), flags=re.DOTALL)
    description = description.group() if description else ""
    return xml_item(
        re.search(r"(?<=<yt:videoId>).+(?=</yt:videoId>)", entry).group(),
        output_dir ,
        "https://youtube.com/watch?v=",
        channelid_youtube[channelid_youtube_ids[output_dir ]]["title"],
        re.search(r"(?<=<title>).+(?=</title>)", entry).group(),
        description,
        pubDate,
        re.search(r"(?<=<media:thumbnail url=\").+(?=\" width=\")", entry).group()
    )


# In[25]:


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
    url = f"{config['url']}/{url}"
    length = re.search(r"(?<=length\=\")[0-9]+(?=\")", original_item).group()
    type_video = re.search(r"(?<=type\=\")(video/mp4|audio/x-m4a|audio/mpeg)(?=\")", original_item).group()
    if type_video == "audio/mpeg":
        type_video = "audio/x-m4a"
    itunes_author =  re.search(r"(?<=<itunes:author>).+(?=</itunes:author>)", original_item).group()
    itunes_subtitle = re.search(r"(?<=<itunes:subtitle>).+(?=</itunes:subtitle>)", original_item).group()
    itunes_summary = re.search(r"(?<=<itunes:summary><\!\[CDATA\[).+(?=\]\]></itunes:summary>)", original_item, flags=re.DOTALL)
    itunes_summary = itunes_summary.group() if itunes_summary else ""
    itunes_image = re.search(r"(?<=<itunes:image href\=\").+(?=\"></itunes:image>)", original_item)
    itunes_image = itunes_image.group() if itunes_image else ""
    itunes_duration = re.search(r"(?<=<itunes:duration>).+(?=</itunes:duration>)", original_item).group()
    itunes_explicit = re.search(r"(?<=<itunes:explicit>).+(?=</itunes:explicit>)", original_item).group()
    itunes_order = re.search(r"(?<=<itunes:order>).+(?=</itunes:order>)", original_item).group()
    return f'''
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
'''


# In[26]:


# 获取原始xml文件
try:
    with open(f"{config['filename']}.xml", 'r', encoding='utf-8') as file:  # 打开文件进行读取
        rss_original = file.read()  # 读取文件内容
        xmls_original = {
            rss_original_channel: rss_original.split(
                f'<!-- {{{rss_original_channel}}} -->\n'
            )[1]
            for rss_original_channel in list(
                set(re.findall(r"(?<=<!-- \{).+?(?=\} -->)", rss_original))
            )
        }
except FileNotFoundError:  #文件不存在直接更新
    xmls_original = None

# 如原始xml无对应的原频道items, 将尝试从对应频道的xml中获取
for youtube_key in channelid_youtube_ids.keys():
    if xmls_original is None or youtube_key not in xmls_original.keys():
        try:
            with open(f"channel_rss/{youtube_key}.xml", 'r', encoding='utf-8') as file:  # 打开文件进行读取
                youtube_rss_original = file.read()  # 读取文件内容
                xmls_original[youtube_key] = youtube_rss_original.split(f'<!-- {{{youtube_key}}} -->\n')[1]
        except FileNotFoundError:  #文件不存在直接更新
            write_log(f"RSS文件中不存在 {channelid_youtube_ids[youtube_key]} 无法保留原节目")


# In[27]:


# 构建文件夹channel_rss
folder_build("channel_rss")


# In[28]:


# 创建线程锁
youtube_xml_get_lock = threading.Lock()
youtube_xml_get_tree = {}
# 使用http获取youtube频道简介和图标模块
def youtube_xml_get(output_dir):
    xml_tree = {}
    if channel_about := get_with_retry(
        f"https://www.youtube.com/channel/{output_dir}/about",
        f"{channelid_youtube_ids[output_dir]} 简介",
        2,
        5,
    ):
        channel_about = channel_about.text
        xml_tree['icon'] = re.sub(
            r"=s(0|[1-9]\d{0,3}|1[0-9]{1,3}|20[0-3][0-9]|204[0-8])-c-k",
            "=s2048-c-k",
            re.search(
                r"https?://yt3.googleusercontent.com/[^\s]*(?=\">)",
                channel_about,
            ).group(),
        )
        xml_tree['description'] = re.search(r"(?<=\<meta itemprop\=\"description\" content\=\").*?(?=\")", channel_about, flags=re.DOTALL).group()
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


# In[29]:


# 生成YouTube对应channel的需更新的items模块
def youtube_xml_items(output_dir):
    items = f"<!-- {output_dir} -->"
    with open(f"channel_id/{output_dir}.txt", 'r', encoding='utf-8') as file:  # 打开文件进行读取
        file_xml = file.read()
    entrys = re.findall(r"<entry>.+?</entry>", file_xml, re.DOTALL)
    entry_num = 0
    for entry in entrys:
        if re.search(r"(?<=<yt:videoId>).+(?=</yt:videoId>)", entry).group() not in yt_id_failed :
            items = f"{items}{youtube_xml_item(entry)}<!-- {output_dir} -->"
        entry_num += 1
        if entry_num >= channelid_youtube[channelid_youtube_ids[output_dir ]]["update_size"]:
            break
    items_guid = re.findall(r"(?<=<guid>).+?(?=</guid>)", items)
    entry_count = channelid_youtube[channelid_youtube_ids[output_dir]]["last_size"] - len(items_guid)
    if xmls_original and output_dir in xmls_original and entry_count > 0:
        xml_num = 0
        for xml in xmls_original[output_dir].split(f"<!-- {output_dir} -->"):
            xml_guid = re.search(r"(?<=<guid>).+(?=</guid>)", xml)
            if xml_guid and xml_guid.group() not in items_guid:
                items = f"{items}{xml_original_item(xml)}<!-- {output_dir} -->"
                xml_num += 1
            if xml_num >= entry_count:
                break
    update_text = "无更新"
    try:
        with open(f"channel_rss/{output_dir}.xml", 'r', encoding='utf-8') as file:  # 打开文件进行读取
            root = ET.parse(file).getroot()
            description = (root.findall('.//description')[0]).text
            description = "" if description is None else html.escape(description)
            icon = (root.findall('.//url')[0]).text
    except FileNotFoundError:  #文件不存在直接更新
        description = config["description"]
        icon = config["icon"]
    if output_dir in channelid_youtube_ids_update and output_dir in youtube_xml_get_tree:
        description = youtube_xml_get_tree[output_dir]["description"]
        icon = youtube_xml_get_tree[output_dir]["icon"]
        update_text = "已更新"
    category = config["category"]
    title = re.search(r"(?<=<title>).+(?=</title>)", file_xml).group()
    link = f"https://www.youtube.com/channel/{output_dir}"
    items = f'''<!-- {{{output_dir}}} -->
{items}
<!-- {{{output_dir}}} -->'''
    file_save(xml_rss(title,link,description,category,icon,items), f"{output_dir}.xml", "channel_rss")
    write_log(f"{channelid_youtube_ids[output_dir]} 播客{update_text}", f"地址:\n\033[34m{config['url']}/channel_rss/{output_dir}.xml\033[0m", channelid_youtube[channelid_youtube_ids[output_dir]]['DisplayRSSaddress'])
    if channelid_youtube[channelid_youtube_ids[output_dir]]['DisplayRSSaddress'] and channelid_youtube[channelid_youtube_ids[output_dir]]['QRcode']:
        qr_code(f"{config['url']}/channel_rss/{output_dir}.xml")
    return items


# In[30]:


# 生成主rss
all_youtube_content_ytid = {}
all_items = ""
for output_dir in channelid_youtube_ids:
    items = youtube_xml_items(output_dir)
    if channelid_youtube[channelid_youtube_ids[output_dir]]["InmainRSS"]:
        all_items = items if all_items == "" else f'''{all_items}
{items}'''
    all_youtube_content_ytid[output_dir] = re.findall(r"(?<=UC.{22}/)(.+\.m4a|.+\.mp4)(?=\")", items)
file_save(xml_rss(config["title"], config["link"], config["description"], config["category"], config["icon"], all_items), f"{config['filename']}.xml")
write_log("总播客已更新", f"地址:\n\033[34m{config['url']}/{config['filename']}.xml\033[0m")
qr_code(f"{config['url']}/{config['filename']}.xml")


# In[31]:


# 删除多余媒体文件模块
def remove_file(output_dir):
    for file_name in os.listdir(output_dir):
        if file_name not in all_youtube_content_ytid[output_dir]:
            os.remove(f"{output_dir}/{file_name}")
            write_log(f"{channelid_youtube_ids[output_dir]}|{file_name}已删除")


# In[32]:


# 删除不在rss中的媒体文件
for output_dir in channelid_youtube_ids:
    remove_file(output_dir)


# In[33]:


# 删除已抛弃的媒体文件夹
def remove_dir():
    folder_names = [folder for folder in os.listdir() if os.path.isdir(folder)]
    folder_names = [name for name in folder_names if re.match(r'UC.{22}', name)]
    for name in folder_names:
        if name not in channelid_youtube_ids:
            os.system(f"rm -r {name}")
            write_log(f"{name}文件夹已删除")
remove_dir()


# In[34]:


# 补全缺失的媒体文件到字典模块
make_up_file_format = {}
def make_up_file(output_dir):
    for file_name in all_youtube_content_ytid[output_dir]:
        if file_name not in os.listdir(output_dir):
            video_id_format = {}
            # 如果为视频格式获取分辨率
            video_id_format["id"] = output_dir
            video_id_format["media"] = file_name.split(".")[1]
            if file_name.split(".")[0] == "mp4":
                video_quality = channelid_youtube[channelid_youtube_ids[output_dir]]['quality']
            else:
                video_quality = 480
            video_id_format["quality"] = video_quality
            make_up_file_format[file_name.split(".")[0]] = video_id_format


# In[35]:


# 补全在rss中缺失的媒体格式信息
for output_dir in channelid_youtube_ids:
    make_up_file(output_dir)
if len(make_up_file_format) != 0:
    print(f"{datetime.now().strftime('%H:%M:%S')}|补全缺失媒体 \033[34m下载准备中...\033[0m")
# 创建线程锁
makeup_yt_format_lock = threading.Lock()
def makeup_yt_format(yt_id):
    makeup_ytid_format = video_format("https://www.youtube.com/watch?v=", yt_id, make_up_file_format[yt_id]["media"], make_up_file_format[yt_id]["quality"])
    if isinstance(makeup_ytid_format, list):
        make_up_file_format[yt_id]["format"] = makeup_ytid_format
    else:
        with makeup_yt_format_lock:
            del make_up_file_format[yt_id]
            write_log(f"{channelid_youtube_ids[make_up_file_format[yt_id]['id']]}|{yt_id} {makeup_ytid_format}")
# 创建线程列表
makeup_yt_format_threads = []
for yt_id in make_up_file_format.keys():
    thread = threading.Thread(target=makeup_yt_format, args=(yt_id,))
    makeup_yt_format_threads.append(thread)
    thread.start()
# 等待所有线程完成
for thread in makeup_yt_format_threads:
    thread.join()
# 下载YouTube视频
for yt_id in make_up_file_format.keys():
    write_log(f"{channelid_youtube_ids[make_up_file_format[yt_id]['id']]}|{yt_id} 缺失并重新下载")
    if dl_aideo_video(
            yt_id,
            make_up_file_format[yt_id]['id'],
            make_up_file_format[yt_id]['media'],
            make_up_file_format[yt_id]['format'],
            config['retry_count'],
            "https://www.youtube.com/watch?v=",
            make_up_file_format[yt_id]['quality'],
            channelid_youtube_ids[make_up_file_format[yt_id]['id']]
        ):
            yt_id_failed.append(yt_id)
            write_log(f"{channelid_youtube_ids[make_up_file_format[yt_id]['id']]}|{yt_id} \033[31m无法下载\033[0m")


# In[36]:


if sys.argv[1] == "a-shell":
    # 启动 RangeHTTPServer
    server_process = subprocess.Popen(["open", "shortcuts://run-shortcut?name=Podflow&input=text&text=http"])
    server_process = subprocess.Popen(["python3", "-m", "RangeHTTPServer"])
    # 延时
    time.sleep(60)
    # 关闭服务器
    server_process.terminate()

