# Podflow/config.py
# coding: utf-8

import os
import re
import sys
import json
from datetime import datetime
from Podflow.basis import write_log
from Podflow import gVar, default_config
from Podflow.main import parse_app

# 获取配置信息config模块
def get_config(file_name="config.json"):
    # 检查当前文件夹中是否存在config文件
    if file_name != "config.json" and not os.path.exists(file_name):
        if os.path.exists("config.json"):
            write_log(f"不存在配置文件{file_name}, 将使用原始配置文件")
            file_name = "config.json"
        else:
            # 如果文件不存在, 创建并写入默认字典
            with open("config.json", "w") as file:
                json.dump(default_config, file, indent=4)
            write_log("不存在配置文件, 已新建, 默认频道")
            return default_config
    # 如果文件存在, 读取字典并保存到config变量中
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            config = json.load(file)
        print(f"{datetime.now().strftime('%H:%M:%S')}|已读取配置文件")
        return config
    # 如果config格式有问题, 停止运行并报错
    except Exception as config_error:
        write_log(f"配置文件有误, 请检查{file_name}, {str(config_error)}")
        sys.exit(0)

# 纠正配置信息config模块
def correct_config():
    config = gVar.config
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
    match_url = re.search(
        r"^(https?|ftp)://([^/\s:]+)", config["url"]
    )
    if "url" in config and match_url:
        config["url"] = match_url.group()
    else:
        config["url"] = default_config["url"]
    # 对port进行纠正
    if (
        "port" not in config
        or not isinstance(config["port"], int)
        or config["port"] < 0
        or config["port"] > 65535
    ):
        config["port"] = default_config["port"]
    # 对port_in_url进行纠正
    if "port_in_url" not in config or not isinstance(
        config["port_in_url"], bool
    ):
        config["port_in_url"] = default_config["port_in_url"]
    # 合并地址和端口
    if config["port_in_url"]:
        config["address"] = f"{config['url']}:{config['port']}"
    else:
        config["address"] = config['url']
    # 对httpfs进行纠正
    if "httpfs" not in config or not isinstance(
        config["httpfs"], bool
    ):
        config["httpfs"] = default_config["httpfs"]
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
    # 对IOS中shortcuts自动关注进行纠正
    if f"{config['address']}/{config['filename']}.xml" not in parse_app.shortcuts_url_original:
        gVar.shortcuts_url[f"{config['filename']}(Main RSS)"] = f"{config['address']}/{config['filename']}.xml"
    # 对token进行纠正
    if "token" not in config:
        config["token"] = default_config["token"]
    if config["token"] in [None, ""]:
        config["token"] = ""
    else:
        config["token"] = str(config["token"])


# 从配置文件中获取频道模块
def get_channelid(name):
    config = gVar.config
    output_name = ""
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
    channelid_name = ""
    output_name = ""
    config = gVar.config
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
            # 对want_retry_count进行纠正
            if (
                "want_retry_count" not in channeli_value
                or not isinstance(channeli_value["want_retry_count"], int)
                or channeli_value["want_retry_count"] <= 0
            ):
                channelid[channelid_key]["want_retry_count"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["want_retry_count"]
            if website == "bilibili":
                # 对AllPartGet进行纠正
                if "AllPartGet" not in channeli_value or not isinstance(
                    channeli_value["AllPartGet"], bool
                ):
                    if channelid[channelid_key]["update_size"] > 5:
                        channelid[channelid_key]["AllPartGet"] = True
                    else:
                        channelid[channelid_key]["AllPartGet"] = False
            if website == "youtube":
                # 对NoShorts进行纠正
                if "NoShorts" not in channeli_value or not isinstance(
                    channeli_value["NoShorts"], bool
                ):
                    channelid[channelid_key]["NoShorts"] = False
        if channelid[channelid_key]["InmainRSS"] is False and f"{config['address']}/channel_rss/{channeli_value['id']}.xml" not in parse_app.shortcuts_url_original:
            gVar.shortcuts_url[channelid_key] = f"{config['address']}/channel_rss/{channeli_value['id']}.xml"
    return channelid

# 读取频道ID模块
def get_channelid_id(channelid, idname):
    output_name = ""
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