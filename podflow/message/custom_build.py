# podflow/message/custom_build.py
# coding: utf-8

import os
import re
import json
import html
from datetime import datetime, timezone

from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.basic.file_save import file_save
from podflow.message.xml_rss import xml_rss
from podflow.message.xml_item import xml_item
from podflow.message.format_time import format_time
from podflow.basic.custom_media_file import get_custom_media
from podflow.basic.custom_media_file import get_custom_media_rev


# 读取上次构建custom_media.xml时的custom_media.json版本号, 文件不存在时返回空字符串
def get_build_rev():
    custom_build_rev_file = "channel_data/custom_media_build.json"
    try:
        with open(custom_build_rev_file, "r", encoding="utf-8") as file:
            return json.load(file).get("rev", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


# 保存本次构建custom_media.xml时的custom_media.json版本号
def save_build_rev(rev):
    file_save({"rev": rev}, "custom_media_build.json", "channel_data")


# 生成自定义媒体的item模块
def custom_xml_item(media, entry):
    custom_media_output_dir = "custom_media"
    video_id = entry.get("id") or media.get("id", "")
    # 使用媒体的发布时间作为pubDate, 缺失时取当前时间
    if timestamp := entry.get("timestamp"):
        published = datetime.fromtimestamp(timestamp, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )
    else:
        published = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    # 与YouTube构建保持一致: 标题及描述转义, 缩略图去除查询参数
    title = html.escape(entry.get("title") or "")
    description = html.escape(re.sub(r"\n+", "\n", entry.get("description") or ""))
    image = re.sub(r"\?.*$", "", entry.get("image") or "")
    return xml_item(
        video_id,
        custom_media_output_dir,
        media.get("url", ""),
        "",  # 自定义媒体无频道名, 传空避免在描述前拼接『频道名』
        title,
        description,
        format_time(published),
        image,
    )


# 生成自定义媒体rss模块
def custom_build():
    custom_media_output_dir = "custom_media"
    custom_media_rss_file = "channel_rss/custom_media.xml"
    current_rev = get_custom_media_rev()
    # custom_media.json不存在或无内容时, 删除custom_media.xml(如有)并记录版本号
    if not get_custom_media():
        if os.path.exists(custom_media_rss_file):
            os.remove(custom_media_rss_file)
            write_log("custom_media.json无内容, 自定义媒体播客已删除")
        save_build_rev(current_rev)
        return
    # 与上次构建相比custom_media.json无变化且rss文件仍存在时, 跳过本次构建
    if get_build_rev() == current_rev and os.path.exists(custom_media_rss_file):
        return
    items_list = []
    for media in get_custom_media():
        # 仅已完成的媒体才生成item
        if media.get("status") != "completed":
            continue
        for entry in media.get("lists", []):
            video_id = entry.get("id") or media.get("id", "")
            # 媒体文件不存在时跳过, 避免生成无法下载的item
            if not any(
                os.path.exists(
                    f"channel_audiovisual/{custom_media_output_dir}/{video_id}.{output_format}"
                )
                for output_format in ("mp4", "m4a")
            ):
                continue
            items_list.append(custom_xml_item(media, entry))
    # 生成自定义媒体rss(频道信息沿用主配置)
    overall_rss = xml_rss(
        "自定义媒体",
        gVar.config["link"],
        gVar.config["description"],
        gVar.config["category"],
        "https://raw.githubusercontent.com/gruel-zxz/podflow/main/Custom.png",
        "\n".join(items_list),
    )
    # 保存自定义媒体rss, 并记录本次构建时的版本号
    file_save(overall_rss, "custom_media.xml", "channel_rss")
    save_build_rev(current_rev)
    # 输出rss地址
    address = gVar.config["address"]
    address = re.sub(r"(http://)([^/:]+):80(?=/|$)", r"\1\2", address)
    address = address.replace("http://", "podcast://")
    if token := gVar.config["token"]:
        rss_url = f"{address}/{custom_media_rss_file}?token={token}"
    else:
        rss_url = f"{address}/{custom_media_rss_file}"
    write_log("自定义媒体播客已更新", "地址:", url=rss_url)
