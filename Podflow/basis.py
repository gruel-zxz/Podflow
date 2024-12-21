# Podflow/basis.py
# coding: utf-8

import os
import re
import json
import math
import time
import qrcode
import requests
import threading
from bs4 import BeautifulSoup
from datetime import datetime

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
def write_log(log, suffix=None, display=True, time_display=True, only_log=None, file_name="Podflow.log"):
    # 获取当前的具体时间
    current_time = datetime.now()
    # 格式化输出, 只保留年月日时分秒
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    # 打开文件, 并读取原有内容
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            contents = file.read()
    except FileNotFoundError:
        contents = ""
    # 将新的日志内容添加在原有内容之前
    log_in = re.sub(r"\033\[[0-9;]+m", "", log)
    log_in = re.sub(r"\n", "", log_in)
    new_contents = f"{formatted_time} {log_in}{only_log}\n{contents}" if only_log else f"{formatted_time} {log_in}\n{contents}"
    # 将新的日志内容写入文件
    file_save(new_contents, file_name)
    if display:
        formatted_time_mini = current_time.strftime("%H:%M:%S")
        log_print = f"{formatted_time_mini}|{log}" if time_display else f"{log}"
        log_print = f"{log_print}|{suffix}" if suffix else f"{log_print}"
        print(log_print)

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

# 时间戳模块
def time_stamp():
    time_stamps = []
    # 获取时间戳淘宝
    def time_stamp_taobao():
        if response := http_client("http://api.m.taobao.com/rest/api3.do?api=mtop.common.getTimestamp", '', 1, 0):
            response_json = response.json()
            try:
                time_stamps.append(int(response_json["data"]["t"]))
            except KeyError:
                pass
    # 获取时间戳美团
    def time_stamp_meituan():
        if response := http_client("https://cube.meituan.com/ipromotion/cube/toc/component/base/getServerCurrentTime", '', 1, 0):
            response_json = response.json()
            try:
                time_stamps.append(int(response_json["data"]))
            except KeyError:
                pass
    # 获取时间戳苏宁
    def time_stamp_suning():
        if response := http_client("https://f.m.suning.com/api/ct.do", '', 1, 0):
            response_json = response.json()
            try:
                time_stamps.append(int(response_json["currentTime"]))
            except KeyError:
                pass
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
    else:
        print(
            f"{datetime.now().strftime('%H:%M:%S')}|\033[31m获取时间戳api失败\033[0m"
            )
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
                f"\r{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation} \033[31m失败:\033[0m"
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

# 通过bs4获取html中字典模块
def get_html_dict(url, name, script_label):
    if response := http_client(url, name):
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
                return None
        else:
            return None
    else:
        return None

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



