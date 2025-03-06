# Podflow/youtube/build.py
# coding: utf-8

import re
import html
import threading
import contextlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from Podflow import gVar
from Podflow.message.xml_item import xml_item
from Podflow.basic.time_print import time_print
from Podflow.basic.http_client import http_client
from Podflow.message.format_time import format_time
from Podflow.basic.get_html_dict import get_html_dict
from Podflow.message.xml_original_item import xml_original_item


# 获取YouTube频道简介模块
def get_youtube_introduction():
    # 创建线程锁
    youtube_xml_get_lock = threading.Lock()

    # 使用http获取youtube频道简介和图标模块
    def youtube_xml_get(output_dir):
        if channel_about := http_client(
            url=f"https://www.youtube.com/channel/{output_dir}/about",
            max_retries=2,
            retry_delay=5,
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
        else:
            xml_tree = {"introduction": False}
            with youtube_xml_get_lock:
                gVar.youtube_xml_get_tree[output_dir] = xml_tree
    # 创建线程列表
    youtube_xml_get_threads = []
    for output_dir in gVar.channelid_youtube_ids_update:
        thread = threading.Thread(target=youtube_xml_get, args=(output_dir,))
        youtube_xml_get_threads.append(thread)
        thread.start()
    # 等待所有线程完成
    for thread in youtube_xml_get_threads:
        thread.join()


# 打印无法获取youtube信息模块
def print_fail_youtube():
    for output_dir, xml_tree in gVar.youtube_xml_get_tree.items():
        if "introduction" in xml_tree:
            time_print(f"{gVar.channelid_youtube_ids[output_dir]} 简介获取失败")
        if "playlist" in xml_tree:
            time_print(f"{gVar.channelid_youtube_ids[output_dir]} 播放列表获取失败") 


# 获取YouTube播放列表模块
def get_youtube_playlist(url):
    videoids = []
    ytInitialData = get_html_dict(url, "", "ytInitialData")
    with contextlib.suppress(KeyError):
        contents = ytInitialData["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][
            0
        ]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0][
            "itemSectionRenderer"
        ][
            "contents"
        ][
            0
        ][
            "playlistVideoListRenderer"
        ][
            "contents"
        ]
        videoids.extend(
            content["playlistVideoRenderer"]["videoId"] for content in contents
        )
    return videoids


# 从HTML获取YouTube媒体信息模块
def youtube_html_guid_message(guid):
    ytInitialPlayerResponse = get_html_dict(
        f"https://www.youtube.com/watch?v={guid}",
        f"{guid} HTML",
        "ytInitialPlayerResponse",
    )
    try:
        image = ytInitialPlayerResponse["microformat"]["playerMicroformatRenderer"][
            "thumbnail"
        ]["thumbnails"][0]["url"]
        title = ytInitialPlayerResponse["microformat"]["playerMicroformatRenderer"][
            "title"
        ]["simpleText"]
        description = ytInitialPlayerResponse["microformat"][
            "playerMicroformatRenderer"
        ]["description"]["simpleText"]
        published = ytInitialPlayerResponse["microformat"]["playerMicroformatRenderer"][
            "publishDate"
        ]
        return published, image, title, description
    except KeyError:
        return None


# 生成YouTube的item模块
def youtube_xml_item(entry, title_change=None):
    if title_change is None:
        title_change = {}

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
    ytid = re.search(r"(?<=<yt:videoId>).+(?=</yt:videoId>)", entry).group()
    return xml_item(
        ytid,
        output_dir,
        f"https://youtube.com/watch?v={ytid}",
        gVar.channelid_youtube[gVar.channelid_youtube_ids[output_dir]]["title"],
        re.search(r"(?<=<title>).+(?=</title>)", entry).group(),
        description,
        pubDate,
        re.search(r"(?<=<media:thumbnail url=\").+(?=\" width=\")", entry).group(),
        title_change,
    )


def get_xml_item(guid, item, channelid_title, title_change, output_dir):
    video_website = f"https://youtube.com/watch?v={guid}"
    if item["yt-dlp"]:
        guid_value = gVar.video_id_update_format[guid]
        if timestamp := guid_value["timestamp"]:
            published = datetime.fromtimestamp(timestamp, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S%z"
            )
            title = guid_value["title"]
            description = guid_value["description"]
            image = guid_value["image"]
        elif guid_message := youtube_html_guid_message(guid):
            published, image, title, description = guid_message
        else:
            return None
        title = html.escape(title)
        description = html.escape(re.sub(r"\n+", "\n", description))
        image = re.sub(r"\?.*$", "", image)
        pubDate = format_time(published)
    else:
        title = html.escape(item["title"])
        description = html.escape(re.sub(r"\n+", "\n", item["description"]))
        pubDate = format_time(item["pubDate"])
        image = re.sub(r"\?.*$", "", item["image"])
    return xml_item(
        guid,
        output_dir,
        video_website,
        channelid_title,
        title,
        description,
        pubDate,
        image,
        title_change,
    )


# 生成YouTube对应channel的需更新的items模块
def youtube_xml_items(output_dir):
    items_list = [f"<!-- {output_dir} -->"]
    entry_num = 0
    original_judgment = True
    channelid_youtube_value = gVar.channelid_youtube[
        gVar.channelid_youtube_ids[output_dir]
    ]
    channelid_title = channelid_youtube_value["title"]
    title_change = channelid_youtube_value.get("title_change", [])
    update_size = channelid_youtube_value["update_size"]
    if title_change:
        for title_index, title_value in enumerate(title_change):
            if "url" in title_value:
                title_index_table = get_youtube_playlist(title_value["url"])
                title_change[title_index]["table"] = title_index_table
                if not title_index_table:
                    if output_dir in gVar.youtube_xml_get_tree:
                        gVar.youtube_xml_get_tree[output_dir]["playlist"] = False
                    else:
                        gVar.youtube_xml_get_tree[output_dir] = {"playlist": False}
    output_dir_value = gVar.channelid_youtube_rss[output_dir]
    # 最新更新
    if output_dir_value["type"] == "dict":
        for guid in output_dir_value["content"]["list"]:
            if guid not in gVar.video_id_failed:
                item = output_dir_value["content"]["item"][guid]
                if xml_item_text := get_xml_item(
                    guid, item, channelid_title, title_change, output_dir
                ):
                    items_list.append(f"{xml_item_text}<!-- {output_dir} -->")
                    if (
                        gVar.video_id_update_format[guid]["description"]
                        and gVar.video_id_update_format[guid]["description"][0] == "『"
                    ):
                        original_judgment = False
    else:
        if output_dir_value["type"] == "html":  # 获取最新的rss信息
            file_xml = output_dir_value["content"].text
        else:
            file_xml = output_dir_value["content"]
        entrys = re.findall(r"<entry>.+?</entry>", file_xml, re.DOTALL)
        for entry in entrys:
            if (
                re.search(r"(?<=<yt:videoId>).+(?=</yt:videoId>)", entry).group()
                not in gVar.video_id_failed
            ):
                items_list.append(
                    f"{youtube_xml_item(entry, title_change)}<!-- {output_dir} -->"
                )
                if re.search(r"(?<=<media:description>)『", entry):
                    original_judgment = False
            entry_num += 1
            if entry_num >= update_size:
                break
    items_guid = re.findall(r"(?<=<guid>).+?(?=</guid>)", "".join(items_list))
    # 存量接入
    entry_count = channelid_youtube_value["last_size"] - len(items_guid)
    if gVar.xmls_original and output_dir in gVar.xmls_original and entry_count > 0:
        xml_num = 0
        for xml in gVar.xmls_original[output_dir].split(f"<!-- {output_dir} -->"):
            xml_guid = re.search(r"(?<=<guid>).+(?=</guid>)", xml)
            if (
                xml_guid
                and xml_guid.group() not in items_guid
                and xml_guid.group() not in gVar.video_id_failed
            ):
                items_list.append(
                    f"{xml_original_item(xml, channelid_title, original_judgment, title_change)}<!-- {output_dir} -->"
                )
                xml_num += 1
            if xml_num >= entry_count:
                break
    # 向后更新
    with contextlib.suppress(KeyError):
        backward = output_dir_value["backward"]
        for backward_guid in backward["list"]:
            if backward_guid not in gVar.video_id_failed:
                backward_item = backward["item"][backward_guid]
                if backward_xml_item_text := get_xml_item(
                    backward_guid,
                    backward_item,
                    channelid_title,
                    title_change,
                    output_dir,
                ):
                    items_list.append(f"{backward_xml_item_text}<!-- {output_dir} -->")
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
        description = gVar.config["description"]
        icon = gVar.config["icon"]
    youtube_xml_get_tree = gVar.youtube_xml_get_tree
    if (
        output_dir in gVar.channelid_youtube_ids_update
        and output_dir in youtube_xml_get_tree
        and "introduction" not in youtube_xml_get_tree[output_dir]
    ):
        description = youtube_xml_get_tree[output_dir]["description"]
        icon = youtube_xml_get_tree[output_dir]["icon"]
    category = gVar.config["category"]
    if output_dir_value["type"] == "dict":
        title = output_dir_value["content"]["title"]
    else:
        title = re.search(r"(?<=<title>).+(?=</title>)", file_xml).group()
    link = f"https://www.youtube.com/channel/{output_dir}"
    items = "".join(items_list)
    items = f"""<!-- {{{output_dir}}} -->
{items}
<!-- {{{output_dir}}} -->"""
    return {
        "title": title,
        "link": link,
        "description": description,
        "category": category,
        "icon": icon,
        "items": items,
    }
