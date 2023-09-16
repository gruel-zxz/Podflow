#!/usr/bin/env python
# coding: utf-8

# In[11]:


import os
import re
import sys
import html
import json
import time
import requests
import subprocess
from datetime import datetime, timedelta, timezone

#默认参数
default_config = {
    "retry_count": 3,
    "url": "http://127.0.0.1:8000",
    "title": "YouTube",
    "link": "https://m.youtube.com",
    "description": "在YouTube 上畅享您喜爱的视频和音乐，上传原创内容并与亲朋好友和全世界观众分享您的视频。",
    "icon": "https://static.vecteezy.com/system/resources/previews/003/399/771/original/youtube-icon-editorial-free-vector.jpg",
    "category": "TV &amp; Film",
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


# In[12]:


# 文件保存模块
def file_save(content, file_name, folder=None):
    # 如果指定了文件夹，则将文件保存到指定的文件夹中
    if folder:
        file_path = os.path.join(os.path.join(os.getcwd(), folder), file_name)
    else:
        # 如果没有指定文件夹，则将文件保存在当前工作目录中
        file_path = os.path.join(os.getcwd(), file_name)
    # 保存文件
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)


# In[13]:


#日志模块
def write_log(log, suffix=None):
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
    new_contents = f"{formatted_time} {log}\n{contents}"
    # 将新的日志内容写入文件
    file_save(new_contents, "log.txt")
    formatted_time_mini = current_time.strftime("%H:%M:%S")
    if suffix:
        print(f"{formatted_time_mini}|{log}|{suffix}")
    else:
        print(f"{formatted_time_mini}|{log}")


# In[14]:


# 安装库模块
def library_install(library):
    if version := re.search(
        r"(?<=Version\: ).+",
        subprocess.run(
            ["pip", "show", library], capture_output=True, text=True
        ).stdout
    ):
        write_log(f"{library}已安装")
        # 获取最新版本编号
        version_update = re.search(
            r"(?<=<h1 class=\"package-header__name\">).+?(?=</h1>)",
            requests.get(f"https://pypi.org/project/{library}/").text,
            flags=re.DOTALL
        )
                # 如果库已安装, 判断是否为最新
        if version_update is None or version.group() not in version_update.group():
            # 如果库已安装, 则尝试更新
            try:
                subprocess.run(['pip', 'install', '--upgrade', library], capture_output=True, text=True)
                write_log(f"{library}更新成功")
            except FileNotFoundError:
                write_log(f"{library}更新失败")
        else:
            write_log(f"{library}无需更新|版本：{version.group()}")
    else:
        write_log(f"{library}未安装")
        # 如果库未安装, 则尝试安装
        try:
            subprocess.run(['pip', 'install', library , '-U'], capture_output=True, text=True)
            write_log(f"{library}安装成功")
        except FileNotFoundError:
            write_log(f"{library}安装失败")


# In[15]:


# 安装/更新yt-dlp，并加载
library_install("yt-dlp")
import yt_dlp
# 安装/更新rangehttpserver
library_install("RangeHTTPServer")


# In[16]:


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

# 文本整形模块
def shap(text, text_size):
    if isinstance(text_size, int) and text_size> 0:
        text = text.strip()
        return text if len(text) > text_size else f"{text:>{text_size}}"
    else:
        text = text.strip()
        text_size = text_size.strip()
        bit = len(text_size)
        if len(text) > bit:
            return f"{text}/{text_size}"
        else:
            return f"{text:>{bit}}/{text_size}"

# 下载显示模块
def show_progress(data_stream):
    percent_str = shap(data_stream['_percent_str'], 5)
    if '_total_bytes_estimate_str' in data_stream:
        if '_downloaded_bytes_str' in data_stream:
            downloaded_bytes_str = shap(data_stream['_downloaded_bytes_str'], data_stream['_total_bytes_estimate_str'])
        else:
            downloaded_bytes_str = shap(data_stream['_total_bytes_estimate_str'], data_stream['_total_bytes_estimate_str'])
    else:
        downloaded_bytes_str = shap(data_stream['_total_bytes_str'], data_stream['_total_bytes_str'])
    speed_str = data_stream['_speed_str'].strip()
    if '_eta_str' in data_stream:
        eta_str = shap(data_stream['_eta_str'].strip(), 5)
        print((f"\r{f'{percent_str}|{downloaded_bytes_str}|{eta_str}|{speed_str}':<44}")[:44],end="")
    else:
        eta_str = data_stream['_elapsed_str'].strip()
        if eta_str[:3] == "00:":
            eta_str = eta_str[-5:]
        print((f"\r{f'{percent_str}|{downloaded_bytes_str}|{eta_str}|{speed_str}':<44}")[:44],end="")
        print("")

# 下载视频模块
def download_video(video_url, output_dir, output_format, video_website, format_code=480, output_dir_name=""):
    if output_dir_name:
        video_write_log = f"{output_dir_name}|{video_url}"
    else:
        video_write_log = video_url
    if output_format == 'm4a':
        format_out = "bestaudio[ext=m4a]/best"   # 音频编码
    else:
        format_out = f'bestvideo[ext=mp4][height<={format_code}]+bestaudio[ext=m4a]/best'  # 视频编码
    ydl_opts = {
        'outtmpl': f'{output_dir}/{video_url}.{output_format}',  # 输出文件路径和名称
        'format': f'{format_out}',  # 指定下载的最佳音频和视频格式
        "quiet": True,
        "noprogress": True,
        "progress_hooks": [show_progress]
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'{video_website}{video_url}'])  # 下载指定视频链接的视频
        write_log(f"{video_write_log}下载成功")  # 写入下载成功的日志信息
    except Exception as e:
        write_log((f"{video_write_log}下载失败, 错误信息：{str(e)}").replace("ERROR: ", "").replace(f"{video_url}: ", ""))  # 写入下载失败的日志信息
        return video_url


# In[41]:


# 测试
#def show_progress(data_stream):
#    putout = data_stream['_default_template']
#    pattern = r"( of ~ )|( at )|( ETA )|( in )|( of )"
#    pattern_space = r"\(.+\)"
#    putout = re.sub(pattern_space, '', re.sub(pattern, '|', putout))
#    print((f"\r{putout:<44}")[:44],end="")
#    if "in" in data_stream['_default_template']:
#        print("")


# In[18]:


# 视频完整下载模块
def dl_full_video(video_url, output_dir, output_format, video_website, format_code=480, output_dir_name=""):
    if not (id_duration := video_duration(video_website, video_url)):  # 获取视频时长
        return video_url
    if download_video(video_url, output_dir, output_format, video_website, format_code, output_dir_name):  # 下载视频
        return video_url
    duration_video = get_duration_ffprobe(f"{output_dir}/{video_url}.{output_format}")  # 获取已下载视频的实际时长
    if id_duration == duration_video:  # 检查实际时长与预计时长是否一致
        return None
    if duration_video:
        os.remove(f"{output_dir}/{video_url}.{output_format}")  #删除不完整的视频
    return video_url

# 视频重试下载模块
def dl_retry_video(video_url, output_dir, output_format, retry_count, video_website, format_code=480, output_dir_name=""):
    if output_dir_name:
        video_write_log = f"{output_dir_name}|{video_url}"
    else:
        video_write_log = video_url
    yt_id_failed = dl_full_video(video_url, output_dir, output_format, video_website, format_code, output_dir_name)
    # 下载失败后重复尝试下载视频
    yt_id_count = 0
    while yt_id_count < retry_count and yt_id_failed:
        yt_id_count += 1
        write_log(f"{video_write_log}第{yt_id_count}次重新下载")
        yt_id_failed = dl_full_video(video_url, output_dir, output_format, video_website, format_code, output_dir_name)
    return yt_id_failed


# In[19]:


# HTTP GET请求重试模块
def get_with_retry(url, name, max_retries=10, retry_delay=6):
    for _ in range(max_retries):
        try:
            response = requests.get(f"{url}")
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            write_log(f"{name}|发生请求异常: {e}")
        except requests.exceptions.HTTPError as e:
            write_log(f"{name}|HTTP错误: {e}")
        except requests.exceptions.ConnectionError as e:
            write_log(f"{name}|连接错误: {e}")
        except requests.exceptions.Timeout as e:
            write_log(f"{name}|请求超时: {e}")
        else:
            return response
        time.sleep(retry_delay)
    write_log(f"{name}|达到最大重试次数，无法获取响应，将不更新")
    return None


# In[20]:


# 构建文件夹模块
def folder_build(folder_name):
    folder_path = os.path.join(os.getcwd(), folder_name)
    if not os.path.exists(folder_path):  # 判断文件夹是否存在
        os.makedirs(folder_path)  # 创建文件夹
        write_log(f"文件夹{folder_name}创建成功")


# In[21]:


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


# In[22]:


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


# In[23]:


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


# In[24]:


# 构建文件夹channel_id
folder_build("channel_id")


# In[25]:


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


# In[26]:


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


# In[27]:


# 更新Youtube频道xml
channelid_youtube_ids_update = {}  #创建需更新的频道
youtube_content_ytid_update = {}  #创建需下载视频列表
# 判断频道id是否正确
pattern_youtube404 = r"Error 404"  # 设置要匹配的正则表达式模式
pattern_youtube_vary = r'([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-2][0-9]:[0-6][0-9]:[0-6][0-9]\+00:00)?(starRating count="[0-9]*")?(statistics views="[0-9]*")?(<id>yt:channel:(UC.{22})?</id>)?(<yt:channelId>(UC.{22})?</yt:channelId>)?'
for youtube_key, youtube_value in channelid_youtube_ids.items():
    # 构建 URL
    youtube_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={youtube_key}"
    if youtube_response := get_with_retry(youtube_url, youtube_value):
        youtube_content = youtube_response.text
        if re.search(pattern_youtube404, youtube_content):
            write_log(f"YouTube频道 {youtube_value} ID不正确无法获取")
            del channelid_youtube_ids[youtube_key]  # 删除错误ID
        else:
            youtube_content_clean = re.sub(pattern_youtube_vary, '', youtube_content)
            # 读取原Youtube频道xml文件并判断是否要更新
            try:
                with open(f"channel_id/{youtube_key}.txt", 'r', encoding='utf-8') as file:  # 打开文件进行读取
                    youtube_content_original = file.read()  # 读取文件内容
                    youtube_content_original_clean = re.sub(pattern_youtube_vary, '', youtube_content_original)
                if youtube_content_clean != youtube_content_original_clean :  #判断是否要更新
                    channelid_youtube_ids_update[youtube_key] = youtube_value
            except FileNotFoundError:  #文件不存在直接更新
                channelid_youtube_ids_update[youtube_key] = youtube_value
            # 构建文件
            file_save(youtube_content, f"{youtube_key}.txt", "channel_id")
            write_log(f"YouTube频道 {youtube_value} 已更新")
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
                youtube_content_ytid_update[youtube_key] = youtube_content_ytid
    elif not os.path.exists(os.path.join("channel_id", f"{youtube_key}.txt")):
        del channelid_youtube_ids[youtube_key]
if channelid_youtube_ids_update:
    write_log(f"需更新的YouTube频道:{', '.join(channelid_youtube_ids_update.values())}")


# In[28]:


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
            yt_id, ytid_key, yt_id_file, config['retry_count'], "https://www.youtube.com/watch?v=", yt_id_quality, channelid_youtube_ids[ytid_key]
        ):
            yt_id_failed.append(yt_id)
            write_log(f"{channelid_youtube_ids[ytid_key]}|{yt_id}无法下载")


# In[29]:


#生成XML模块
def xml_rss(title,link,description,category,icon,items):
    # 获取当前时间
    current_time_now = time.time()  # 获取当前时间的秒数
    # 获取当前时区和夏令时信息
    time_info_now = time.localtime(current_time_now)
    # 构造时间字符串
    formatted_time_now = time.strftime('%a, %d %b %Y %H:%M:%S %z', time_info_now)
    itunes_summary = description.replace("\n", "&#xA;")
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
        <itunes:author>{title}</itunes:author>
        <itunes:subtitle>{title}</itunes:subtitle>
        <itunes:summary><![CDATA[{itunes_summary}]]></itunes:summary>
        <itunes:image href="{icon}"></itunes:image>
        <itunes:explicit>no</itunes:explicit>
        <itunes:category text="{category}"></itunes:category>
{items}
    </channel>
</rss>'''


# In[30]:


# 生成item模块
def xml_item(video_url, output_dir, video_website, channelid_title,title, description, pubDate, image):
    # 查看标题中是否有频道名称，如无添加到描述中
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
    hours, remaining_seconds = divmod(get_duration_ffprobe(f"{output_dir}/{video_url}.{output_format}"), 3600)
    minutes = remaining_seconds // 60
    remaining_seconds = remaining_seconds % 60
    if hours > 1:
        duration = '{:02}:{:02}:{:02}'.format(hours, minutes, remaining_seconds)
    else:
        duration = '{:02}:{:02}'.format(minutes, remaining_seconds)
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


# In[31]:


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


# In[32]:


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


# In[33]:


# 获取原始xml文件
try:
    with open(f"{config['title']}.xml", 'r', encoding='utf-8') as file:  # 打开文件进行读取
        rss_original = file.read()  # 读取文件内容
        write_log("已获取原始rss文件")
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
    write_log("原始rss文件不存在, 无法保留原有节目")


# In[34]:


# 构建文件夹channel_rss
folder_build("channel_rss")


# In[35]:


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
    channel_about =requests.get(f"https://www.youtube.com/channel/{output_dir}/about").text
    title = re.search(r"(?<=<title>).+(?=</title>)", file_xml).group()
    link = f"https://www.youtube.com/channel/{output_dir}"
    category = config["category"]
    icon = re.sub(
        r"=s(0|[1-9]\d{0,3}|1[0-9]{1,3}|20[0-3][0-9]|204[0-8])-c-k",
        "=s2048-c-k",
        re.search(
            r"https?://yt3.googleusercontent.com/[^\s]*(?=\">)",
            channel_about,
        ).group(),
    )
    description = re.search(r"(?<=\<meta itemprop\=\"description\" content\=\").+?(?=\")", channel_about, flags=re.DOTALL).group()
    file_save(xml_rss(title,link,description,category,icon,items), f"{output_dir}.xml", "channel_rss")
    write_log(f"{channelid_youtube_ids[output_dir]} 播客已更新", f"地址: {config['url']}/channel_rss/{output_dir}.xml")
    return items


# In[36]:


# 生成主rss
all_youtube_content_ytid = {}
all_items = ""
for output_dir in channelid_youtube_ids:
    items = f'''<!-- {{{output_dir}}} -->
{youtube_xml_items(output_dir)}
<!-- {{{output_dir}}} -->'''
    all_items = items if all_items == "" else f'''{all_items}
{items}'''
    all_youtube_content_ytid[output_dir] = re.findall(r"(?<=UC.{22}/)(.+\.m4a|.+\.mp4)(?=\")", items)
file_save(xml_rss(config["title"], config["link"], config["description"], config["category"], config["icon"], all_items), f"{config['title']}.xml")
write_log("主播客已更新", f"地址: {config['url']}/{config['title']}.xml")


# In[37]:


# 删除多余媒体文件模块
def remove_file(output_dir):
    for file_name in os.listdir(output_dir):
        if file_name not in all_youtube_content_ytid[output_dir]:
            os.remove(f"{output_dir}/{file_name}")
            write_log(f"{channelid_youtube_ids[output_dir]}|{file_name}已删除")


# In[38]:


# 补全缺失的媒体文件模块
def make_up_file(output_dir):
    for file_name in all_youtube_content_ytid[output_dir]:
        if file_name not in os.listdir(output_dir):
            write_log(f"{channelid_youtube_ids[output_dir]}|{file_name}缺失并重新下载")
            # 如果为视频格式获取分辨率
            if file_name.split(".")[0] == "mp4":
                video_quality = channelid_youtube[channelid_youtube_ids[output_dir]]['quality']
            else:
                video_quality = 480
            if dl_retry_video(
                file_name.split(".")[0], output_dir, file_name.split(".")[1], config['retry_count'], "https://www.youtube.com/watch?v=", video_quality, channelid_youtube_ids[output_dir]
            ):
                write_log(f"{channelid_youtube_ids[file_name.split('.')[0]]}|{file_name.split('.')[0]}无法下载")


# In[39]:


# 删除不在rss中的媒体文件
for output_dir in channelid_youtube_ids:
    remove_file(output_dir)


# In[40]:


# 补全在rss中缺失的媒体文件
for output_dir in channelid_youtube_ids:
    make_up_file(output_dir)

