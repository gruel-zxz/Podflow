# podflow/message/xml_item.py
# coding: utf-8

import os
import html
import hashlib
from podflow.message.title_correction import title_correction
from podflow.basic.time_format import time_format
from podflow.basic.get_duration import get_duration
from podflow import gVar


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
    title_change=None,
):
    if title_change is None:
        title_change = []
    channelid_title = html.escape(channelid_title)
    if title_change:
        title = title_correction(title, video_url, title_change)
    # 查看标题中是否有频道名称如无添加到描述中并去除空字符
    title = title.replace("\x00", "")
    if channelid_title not in title:
        if description == "":
            description = f"『{channelid_title}』{description}"
        else:
            description = f"『{channelid_title}』\n{description}".replace("\x00", "")
    # 更换描述换行符
    replacement_description = description.replace("\n", "&#xA;").replace("\t", "&#x9;")
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
        get_duration(f"channel_audiovisual/{output_dir}/{video_url}.{output_format}")
    )
    # 生成url
    if gVar.config["token"]:
        input_string = f"{gVar.config['token']}/channel_audiovisual/{output_dir}/{video_url}.{output_format}"
    else:
        input_string = f"channel_audiovisual/{output_dir}/{video_url}.{output_format}"
    sha256_hash = hashlib.sha256(input_string.encode()).hexdigest()
    url = f"{gVar.config['address']}/channel_audiovisual/{output_dir}/{video_url}.{output_format}?token={sha256_hash}"
    # 回显对应的item
    return f"""
        <item>
            <guid>{video_url}</guid>
            <title>{title}</title>
            <link>{video_website}</link>
            <description>{replacement_description}</description>
            <pubDate>{pubDate}</pubDate>
            <enclosure url="{url}" length="{video_length_bytes}" type="{video_type}"></enclosure>
            <itunes:author>{title}</itunes:author>
            <itunes:subtitle>{title}</itunes:subtitle>
            <itunes:summary><![CDATA[{description}]]></itunes:summary>
            <itunes:image href="{image}"></itunes:image>
            <itunes:duration>{duration}</itunes:duration>
            <itunes:explicit>no</itunes:explicit>
            <itunes:order>1</itunes:order>
        </item>
"""
