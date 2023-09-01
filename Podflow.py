#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import re
import sys
import json
import requests
import datetime
import subprocess
import xml.etree.ElementTree as ET

#默认参数
default_config = {
    "retry_count": 3,
    "channelid_youtube": {
        "youtube": {
            "update_size": 15,
            "id": "UCBR8-60-B28hp2BmDPdntcQ",
            "title": "YouTube",
            "quality": "480",
            "last_size": 50,
            "media": "m4a"
        }
    }
}


# In[ ]:


#日志模块
def write_log(log):
    # 获取当前的具体时间
    current_time = datetime.datetime.now()
    # 格式化输出, 只保留年月日时分秒
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    # 打开文件, 并读取原有内容
    try:
        with open("log.txt", "r") as file:
            contents = file.read()
    except FileNotFoundError:
        contents = ""
    # 将新的日志内容添加在原有内容之前
    new_contents = f"{formatted_time} {log}\n{contents}"
    # 将新的日志内容写入文件
    with open("log.txt", "w") as file:
        file.write(new_contents)
    formatted_time_mini = current_time.strftime("%H:%M:%S")
    print(f"{formatted_time_mini}|{log}")


# In[ ]:


# 安装库模块
def library_install(library):
    # 检查库是否已安装
    def is_library_installed():
        try:
            result = subprocess.run([library , '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    # 如果库未安装, 则尝试安装
    def install_library():
        try:
            result = subprocess.run(['pip', 'install', library , '-U'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    # 如果库已安装, 则尝试更新
    def update_library():
        try:
            result = subprocess.run(['pip', 'install', '--upgrade', library], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    # 检查库是否已安装
    if is_library_installed():
        write_log(f"{library}已安装")
    else:
        write_log(f"{library}未安装")
    # 如果库已安装, 则尝试更新
    if is_library_installed():
        if update_library():
            write_log(f"{library}更新成功")
        else:
            write_log(f"{library}更新失败")
    else:  # 如果库未安装, 则尝试安装
        if install_library():
            write_log(f"{library}安装成功")
        else:
            write_log(f"{library}安装失败")


# In[ ]:


# 安装/更新yt-dlp
library_install("yt-dlp")


# In[ ]:


import yt_dlp

# 获取视频时长模块
def video_duration(video_website, video_url):
    try:
        # 初始化 yt_dlp 实例, 并忽略错误
        ydl = yt_dlp.YoutubeDL({'ignoreerrors': True})
        # 使用提供的 URL 提取视频信息
        if info_dict := ydl.extract_info(
            f"{video_website}{video_url}", download=False
        ):
            # 获取视频时长并返回
            return info_dict.get('duration')
    except Exception as e:
        # 记录下载失败及错误详情
        write_log((f"{video_url} 下载失败, 错误信息：{str(e)}").replace("ERROR: ", "").replace(f"{video_url}: ", ""))
        return None

# 获取已下载视频时长模块
def get_duration_ffprobe(file_path):
    try:
        # 调用 ffprobe 命令获取视频文件的时长信息
        command = [
            "ffprobe",                       # ffprobe 命令
            "-i", file_path,                 # 输入文件路径
            "-show_entries", "format=duration",  # 显示时长信息
            "-v", "error",
            "-of", "default=noprint_wrappers=1:nokey=1"
        ]
        # 执行命令并获取输出
        output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode("utf-8")
        # 使用正则表达式提取时长值, 并将其转换为浮点数并四舍五入为整数
        return round(float(output))
    except subprocess.CalledProcessError as e:
        write_log(f"Error: {e.output}")
        return None

# 下载视频模块
def download_video(video_url, output_dir, output_format, video_website, format_code=480):
    if output_format == 'm4a':
        format_out = "bestaudio[ext=m4a]/best"   # 音频编码
    else:
        format_out = f'bestvideo[ext=mp4][height<={format_code}]+bestaudio[ext=m4a]/best'  # 视频编码
    ydl_opts = {
        'outtmpl': f'{output_dir}/{video_url}.{output_format}',  # 输出文件路径和名称
        'format': f'{format_out}'  # 指定下载的最佳音频和视频格式
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'{video_website}{video_url}'])  # 下载指定视频链接的视频
        write_log(f"{video_url}下载成功")  # 写入下载成功的日志信息
    except Exception as e:
        write_log((f"{video_url}下载失败, 错误信息：{str(e)}").replace("ERROR: ", "").replace(f"{video_url}: ", ""))  # 写入下载失败的日志信息
        return video_url


# In[ ]:


# 视频完整下载模块
def dl_full_video(video_url, output_dir, output_format, video_website, format_code=480):
    if not (id_duration := video_duration(video_website, video_url)):  # 获取视频时长
        return video_url
    if download_video(video_url, output_dir, output_format, video_website, format_code):  # 下载视频
        return video_url
    duration_video = get_duration_ffprobe(f"{output_dir}/{video_url}.{output_format}")  # 获取已下载视频的实际时长
    if id_duration == duration_video:  # 检查实际时长与预计时长是否一致
        return None
    if duration_video:
        os.remove(f"{output_dir}/{video_url}.{output_format}")  #删除不完整的视频
    return video_url

# 视频重试下载模块
def dl_retry_video(video_url, output_dir, output_format, retry_count, video_website, format_code=480):
    yt_id_failed = dl_full_video(video_url, output_dir, output_format, video_website, format_code)
    # 下载失败后重复尝试下载视频
    yt_id_count = 0
    while yt_id_count < retry_count and yt_id_failed:
        yt_id_count += 1
        write_log(f"{video_url}第{yt_id_count}次重新下载")
        yt_id_failed = dl_full_video(video_url, output_dir, output_format, video_website, format_code)
    return yt_id_failed


# In[2]:


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
    except Exception as e:
        write_log(f"配置文件有误, 请检查config.json, {str(e)}")
        sys.exit(0)


# In[ ]:


# 对retry_count进行纠正
if (
    'retry_count' not in config
    or not isinstance(config['retry_count'], int)
    or config['retry_count'] <= 0
):
    config['retry_count'] = default_config["retry_count"]


# In[ ]:


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


# In[ ]:


# 构建文件夹channel_id
folder_path_channel_ids = os.path.join(os.getcwd(), "channel_id")
if not os.path.exists(folder_path_channel_ids):  # 判断文件夹是否存在
    os.makedirs(folder_path_channel_ids)  # 创建文件夹
    write_log("文件夹channel_id创建成功")


# In[ ]:


# 视频分辨率变量
youtube_video_media = ["m4v", "mov", "qt", "avi", "flv", "wmv", "asf", "mpeg", "mpg", "vob", "mkv", "rm", "rmvb", "vob", "ts", "dat"]
youtube_dpi = ["144", "180", "216", "240", "360", "480", "720", "1080", "1440", "2160", "4320"]
youtube_media = ["m4a", "mp4"]
# 复制字典youtube-channelid, 遍历复制后的字典进行操作以避免在循环中删除元素导致的迭代错误
channelid_youtube_copy = channelid_youtube.copy()
# 对youtube-channelid的错误进行更正
for channelid_youtube_key, channelid_youtube_value in channelid_youtube_copy.items():
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


# In[ ]:


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


# In[ ]:


# 更新Youtube频道xml
channelid_youtube_ids_update = {}  #创建需更新的频道
youtube_content_ytid_update = {}  #创建需下载视频列表
# 判断频道id是否正确
pattern_youtube404 = r"Error 404"  # 设置要匹配的正则表达式模式
pattern_youtube_vary = r'([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-2][0-9]:[0-6][0-9]:[0-6][0-9]\+00:00)?(starRating count="[0-9]*")?(statistics views="[0-9]*")?(<id>yt:channel:(UC.{22})?</id>)?(<yt:channelId>(UC.{22})?</yt:channelId>)?'
for youtube_key, youtube_value in channelid_youtube_ids.items():
    # 构建 URL
    youtube_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={youtube_key}"
    # 发送请求并获取响应内容
    youtube_response = requests.get(youtube_url)
    youtube_content = youtube_response.text
    if not re.search(pattern_youtube404, youtube_content):
        youtube_content = re.sub(pattern_youtube_vary, '', youtube_content)
        # 读取原Youtube频道xml文件并判断是否要更新
        try:
            with open(f"channel_id/{youtube_key}.txt", 'r', encoding='utf-8') as file:  # 打开文件进行读取
                youtube_content_original = file.read()  # 读取文件内容
            if youtube_content != youtube_content_original:  #判断是否要更新
                channelid_youtube_ids_update[youtube_key] = youtube_value
        except FileNotFoundError:  #文件不存在直接更新
            channelid_youtube_ids_update[youtube_key] = youtube_value
        # 构建文件路径
        file_path = os.path.join(folder_path_channel_ids, f"{youtube_key}.txt")
        # 构建文件路径
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(youtube_content)
            write_log(f"YouTube频道 {youtube_value} 已更新")
        # 构建频道文件夹
        folder_path_channel_id = os.path.join(os.getcwd(), youtube_key)
        if not os.path.exists(folder_path_channel_id):  # 判断文件夹是否存在
            os.makedirs(folder_path_channel_id)  # 创建文件夹
            write_log(f"文件夹{youtube_key}创建成功")
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
            youtube_content_ytid_update[youtube_key] = youtube_content_ytid
    else:
        write_log(f"YouTube频道 {youtube_value} ID不正确无法获取")
        del channelid_youtube_ids[youtube_key]  # 删除错误ID
if channelid_youtube_ids_update:
    write_log(f"需更新的YouTube频道:{', '.join(channelid_youtube_ids_update.values())}")


# In[ ]:


# 下载YouTube视频
yt_id_failed = []
for ytid_key, ytid_value in youtube_content_ytid_update.items():
    # 获取对应文件类型
    yt_id_file = channelid_youtube[channelid_youtube_ids_update[ytid_key]]['media']
    # 如果为视频格式获取分辨率
    if yt_id_file == "mp4":
        yt_id_quality = channelid_youtube[channelid_youtube_ids_update[ytid_key]]['quality']
    else:
        yt_id_quality = None
    # 下载视频
    for yt_id in ytid_value:
        if dl_retry_video(
            yt_id, ytid_key, yt_id_file, config['retry_count'], "https://www.youtube.com/watch?v=", yt_id_quality
        ):
            yt_id_failed.append(yt_id)
            write_log(f"{yt_id}无法下载")

