# Podflow/bilibili/build.py
# coding: utf-8

import re
import html
import contextlib
from datetime import datetime, timezone
from Podflow import gVar
from Podflow.message.xml_rss import xml_rss
from Podflow.basic.file_save import file_save
from Podflow.message.xml_item import xml_item
from Podflow.bilibili.get import get_bilibili_cid
from Podflow.message.format_time import format_time
from Podflow.basic.get_file_list import get_file_list
from Podflow.message.xml_original_item import xml_original_item


def get_items_list(
    guid,
    item,
    channelid_title,
    title_change,
    items_counts,
    output_dir,
    items_list,
):
    pubDate = datetime.fromtimestamp(item["created"], timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S%z"
    )
    if guid in items_counts:
        guid_parts = []
        guid_edgeinfos = []
        if "cid" in item:
            pass
        elif "part" in item:
            guid_parts = item["part"]
        elif "edgeinfo" in item:
            guid_edgeinfos = item["edgeinfo"]
        elif "error" in item:
            pass  # 需要添加错误处理
        else:
            guid_cid, guid_type, _ = get_bilibili_cid(
                guid, gVar.channelid_bilibili_ids[output_dir]
            )
            if guid_type == "part":
                guid_parts = guid_cid
            elif guid_type == "edgeinfo":
                guid_edgeinfos = guid_cid
        if guid_parts and items_counts[guid] == len(guid_parts):
            for guid_part in guid_parts:
                guid_part_text = f"{item['title']} Part{guid_part['page']:0{len(str(len(guid_parts)))}}"
                if item["title"] != guid_part["part"]:
                    guid_part_text += f" {guid_part['part']}"
                xml_item_text = xml_item(
                    f"{item['bvid']}_p{guid_part['page']}",
                    output_dir,
                    f"https://www.bilibili.com/video/{guid}?p={guid_part['page']}",
                    channelid_title,
                    html.escape(guid_part_text),
                    html.escape(re.sub(r"\n+", "\n", item["description"])),
                    format_time(pubDate),
                    guid_part["first_frame"],
                    title_change,
                )
                items_list.append(f"{xml_item_text}<!-- {output_dir} -->")
        elif guid_edgeinfos and items_counts[guid] == len(guid_edgeinfos):
            cid_edgeinfos = {
                guid_edgeinfo["cid"]: guid_edgeinfo["title"]
                for guid_edgeinfo in guid_edgeinfos
            }
            for guid_edgeinfo in guid_edgeinfos:
                if guid_edgeinfo["options"]:
                    description = (
                        "〖互动视频〗\n"
                        + "\n".join(
                            f"{option}\t✪{cid_edgeinfos[option_cid]}"
                            for option, option_cid in zip(
                                guid_edgeinfo["options"], guid_edgeinfo["options_cid"]
                            )
                        )
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
                    channelid_title,
                    html.escape(guid_edgeinfo_text),
                    html.escape(re.sub(r"\n+", "\n", description)),
                    format_time(pubDate),
                    guid_edgeinfo["first_frame"],
                    title_change,
                )
                items_list.append(f"{xml_item_text}<!-- {output_dir} -->")
    else:
        xml_item_text = xml_item(
            item["bvid"],
            output_dir,
            f"https://www.bilibili.com/video/{guid}",
            channelid_title,
            html.escape(item["title"]),
            html.escape(re.sub(r"\n+", "\n", item["description"])),
            format_time(pubDate),
            item["pic"],
            title_change,
        )
        items_list.append(f"{xml_item_text}<!-- {output_dir} -->")


# 生成哔哩哔哩对应channel的需更新的items模块
def bilibili_xml_items(output_dir):
    channelid_bilibili_value = gVar.channelid_bilibili[
        gVar.channelid_bilibili_ids[output_dir]
    ]
    content_id, items_counts = get_file_list(
        output_dir, channelid_bilibili_value["media"]
    )
    items_list = [f"<!-- {output_dir} -->"]
    entry_num = 0
    original_judgment = True
    channelid_title = channelid_bilibili_value["title"]
    title_change = channelid_bilibili_value.get("title_change", [])
    output_dir_value = gVar.channelid_bilibili_rss[output_dir]
    # 最新更新
    for guid in output_dir_value["content"]["list"]:
        if guid not in gVar.video_id_failed and guid in content_id:
            item = output_dir_value["content"]["entry"][guid]
            get_items_list(
                guid,
                item,
                channelid_title,
                title_change,
                items_counts,
                output_dir,
                items_list,
            )
            if item["description"] and item["description"][0] == "『":
                original_judgment = False
        entry_num += 1
        if entry_num >= channelid_bilibili_value["update_size"]:
            break
    items_guid = re.findall(r"(?<=<guid>).+?(?=</guid>)", "".join(items_list))
    # 存量接入
    entry_count = channelid_bilibili_value["last_size"] - len(items_guid)
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
            if (
                backward_guid not in gVar.video_id_failed
                and backward_guid in content_id
            ):
                backward_item = backward["entry"][backward_guid]
                get_items_list(
                    backward_guid,
                    backward_item,
                    channelid_title,
                    title_change,
                    items_counts,
                    output_dir,
                    items_list,
                )
    # 生成对应xml
    description = html.escape(output_dir_value["content"]["sign"])
    icon = output_dir_value["content"]["face"]
    category = gVar.config["category"]
    title = html.escape(output_dir_value["content"]["name"])
    link = f"https://space.bilibili.com/{output_dir}"
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
