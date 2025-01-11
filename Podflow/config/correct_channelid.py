# Podflow/config/correct_channelid.py
# coding: utf-8

import re
from Podflow import gVar, default_config, parse
from Podflow.basic.write_log import write_log


# channelid修正模块
def correct_channelid(channelid, website):
    config = gVar.config
    channelid_name = ""
    output_name = ""
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

    # 判断正则表达式是否有效
    def is_valid_regex(pattern):
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False

    # 复制字典channelid, 遍历复制后的字典进行操作以避免在循环中删除元素导致的迭代错误
    channelid_copy = channelid.copy()
    # 对channelid的错误进行更正
    for channelid_key, channeli_value in channelid_copy.items():
        # 判断是否为字典
        if not isinstance(channeli_value, dict):
            channeli_value = {"id": channeli_value}
            channelid[channelid_key] = channeli_value
        # 判断id是否正确
        if (
            "id" not in channeli_value
            or (
                website == "youtube"
                and not re.search(r"^UC.{22}", channeli_value["id"])
            )
            or (website == "bilibili" and not channeli_value["id"].isdigit())
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
            # 对title_change进行纠正
            if "title_change" in channeli_value:
                title_changes = channeli_value["title_change"]
                uphold_title_changes = []
                if isinstance(title_changes, list):
                    for title_change in title_changes:
                        if website == "bilibli" and "url" in title_change:
                            del title_change["url"]
                        if (
                            isinstance(title_change, dict)
                            and "mode" in title_change
                            and "text" in title_change
                            and ("url" in title_change or "match" in title_change)
                        ):
                            mode = title_change["mode"]
                            match_url_pattern = r"https://www\.youtube\.com/playlist\?list=PL[0-9a-zA-Z_-]{32}"
                            if "url" in title_change and (
                                mode not in ["add-left", "add-right"]
                                or not re.match(match_url_pattern, title_change["url"])
                            ):
                                break
                            if "match" in title_change and (
                                mode not in ["add-left", "add-right", "replace"]
                                or not is_valid_regex(title_change["match"])
                            ):
                                break
                            uphold_title_changes.append(title_change)
                if uphold_title_changes:
                    channelid[channelid_key]["title_change"] = uphold_title_changes
                else:
                    del channelid[channelid_key]["title_change"]
            if website == "bilibili" and (
                "AllPartGet" not in channeli_value
                or not isinstance(channeli_value["AllPartGet"], bool)
            ):
                channelid[channelid_key]["AllPartGet"] = (
                    channelid[channelid_key]["update_size"] > 5
                )
            if website == "youtube" and (
                "NoShorts" not in channeli_value
                or not isinstance(channeli_value["NoShorts"], bool)
            ):
                channelid[channelid_key]["NoShorts"] = False
        if (
            channelid[channelid_key]["InmainRSS"] is False
            and f"{config['address']}/channel_rss/{channeli_value['id']}.xml"
            not in parse.shortcuts_url_original
        ):
            gVar.shortcuts_url[channelid_key] = (
                f"{config['address']}/channel_rss/{channeli_value['id']}.xml"
            )
    return channelid
