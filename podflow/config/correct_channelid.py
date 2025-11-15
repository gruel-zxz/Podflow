# podflow/config/correct_channelid.py
# coding: utf-8

import re
from podflow import gVar, default_config, parse
from podflow.basic.write_log import write_log


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
    languages = [
        "af",  # Afrikaans
        "ar",  # Arabic
        "az",  # Azerbaijani
        "be",  # Belarusian
        "bg",  # Bulgarian
        "bn",  # Bengali
        "bs",  # Bosnian
        "ca",  # Catalan
        "cs",  # Czech
        "cy",  # Welsh
        "da",  # Danish
        "de",  # German
        "el",  # Greek
        "en",  # English
        "eo",  # Esperanto
        "es",  # Spanish
        "et",  # Estonian
        "eu",  # Basque
        "fa",  # Persian
        "fi",  # Finnish
        "fr",  # French
        "ga",  # Irish
        "gl",  # Galician
        "gu",  # Gujarati
        "he",  # Hebrew
        "hi",  # Hindi
        "hr",  # Croatian
        "ht",  # Haitian
        "hu",  # Hungarian
        "hy",  # Armenian
        "id",  # Indonesian
        "is",  # Icelandic
        "it",  # Italian
        "ja",  # Japanese
        "ka",  # Georgian
        "kk",  # Kazakh
        "km",  # Khmer
        "kn",  # Kannada
        "ko",  # Korean
        "ku",  # Kurdish
        "ky",  # Kyrgyz
        "la",  # Latin
        "lb",  # Luxembourgish
        "lo",  # Lao
        "lt",  # Lithuanian
        "lv",  # Latvian
        "mk",  # Macedonian
        "ml",  # Malayalam
        "mn",  # Mongolian
        "mr",  # Marathi
        "ms",  # Malay
        "mt",  # Maltese
        "nb",  # Norwegian Bokmål
        "ne",  # Nepali
        "nl",  # Dutch
        "nn",  # Norwegian Nynorsk
        "no",  # Norwegian
        "pa",  # Punjabi
        "pl",  # Polish
        "pt",  # Portuguese
        "ro",  # Romanian
        "ru",  # Russian
        "si",  # Sinhala
        "sk",  # Slovak
        "sl",  # Slovenian
        "sq",  # Albanian
        "sr",  # Serbian
        "sv",  # Swedish
        "sw",  # Swahili
        "ta",  # Tamil
        "te",  # Telugu
        "th",  # Thai
        "tl",  # Tagalog
        "tr",  # Turkish
        "uk",  # Ukrainian
        "ur",  # Urdu
        "uz",  # Uzbek
        "vi",  # Vietnamese
        "xh",  # Xhosa
        "yi",  # Yiddish
        "zh",  # Chinese
        "zu",  # Zulu
    ]

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
    for channelid_key, channelid_value in channelid_copy.items():
        # 判断是否为字典
        if not isinstance(channelid_value, dict):
            channelid_value = {"id": channelid_value}
            channelid[channelid_key] = channelid_value
        # 判断id是否正确
        if (
            "id" not in channelid_value
            or (
                website == "youtube"
                and not re.search(r"^UC.{22}", channelid_value["id"])
            )
            or (website == "bilibili" and not channelid_value["id"].isdigit())
        ):
            # 删除错误的
            del channelid[channelid_key]
            write_log(f"{output_name}频道 {channelid_key} ID不正确")
        else:
            # 对update_size进行纠正
            if (
                "update_size" not in channelid_value
                or not isinstance(channelid_value["update_size"], int)
                or channelid_value["update_size"] <= 0
            ):
                channelid[channelid_key]["update_size"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["update_size"]
            # 对id进行纠正
            if website == "youtube":
                channelid[channelid_key]["id"] = re.search(
                    r"UC.{22}", channelid_value["id"]
                ).group()
            # 对last_size进行纠正
            if (
                "last_size" not in channelid_value
                or not isinstance(channelid_value["last_size"], int)
                or channelid_value["last_size"] <= 0
            ):
                channelid[channelid_key]["last_size"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["last_size"]
            channelid[channelid_key]["last_size"] = max(
                channelid[channelid_key]["last_size"],
                channelid[channelid_key]["update_size"],
            )
            # 对title进行纠正
            if "title" not in channelid_value:
                channelid[channelid_key]["title"] = channelid_key
            # 对quality进行纠正
            if (
                (
                    "quality" not in channelid_value
                    or channelid_value["quality"] not in dpi
                )
                and "media" in channelid_value
                and channelid_value["media"] == "mp4"
            ):
                channelid[channelid_key]["quality"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["quality"]
            # 对media进行纠正
            if (
                "media" in channelid_value
                and channelid_value["media"] not in media
                and channelid_value["media"] in video_media
            ):
                channelid[channelid_key]["media"] = "mp4"
            elif (
                "media" in channelid_value
                and channelid_value["media"] not in media
                or "media" not in channelid_value
            ):
                channelid[channelid_key]["media"] = "m4a"
            # 对DisplayRSSaddress进行纠正
            if "DisplayRSSaddress" not in channelid_value or not isinstance(
                channelid_value["DisplayRSSaddress"], bool
            ):
                channelid[channelid_key]["DisplayRSSaddress"] = False
            # 对InmainRSS进行纠正
            if "InmainRSS" in channelid_value and isinstance(
                channelid_value["InmainRSS"], bool
            ):
                if channelid_value["InmainRSS"] is False:
                    channelid[channelid_key]["DisplayRSSaddress"] = True
            else:
                channelid[channelid_key]["InmainRSS"] = True
            # 对QRcode进行纠正
            if "QRcode" not in channelid_value or not isinstance(
                channelid_value["QRcode"], bool
            ):
                channelid[channelid_key]["QRcode"] = False
            # 对BackwardUpdate进行纠正
            if "BackwardUpdate" not in channelid_value or not isinstance(
                channelid_value["BackwardUpdate"], bool
            ):
                channelid[channelid_key]["BackwardUpdate"] = False
            # 对BackwardUpdate_size进行纠正
            if channelid[channelid_key]["BackwardUpdate"] and (
                "BackwardUpdate_size" not in channelid_value
                or not isinstance(channelid_value["BackwardUpdate_size"], int)
                or channelid_value["BackwardUpdate_size"] <= 0
            ):
                channelid[channelid_key]["BackwardUpdate_size"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["BackwardUpdate_size"]
            # 对want_retry_count进行纠正
            if (
                "want_retry_count" not in channelid_value
                or not isinstance(channelid_value["want_retry_count"], int)
                or channelid_value["want_retry_count"] <= 0
            ):
                channelid[channelid_key]["want_retry_count"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["want_retry_count"]
            # 对title_change进行纠正
            if "title_change" in channelid_value:
                title_changes = channelid_value["title_change"]
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
            # 对AllPartGet进行纠正
            if website == "bilibili" and (
                "AllPartGet" not in channelid_value
                or not isinstance(channelid_value["AllPartGet"], bool)
            ):
                channelid[channelid_key]["AllPartGet"] = (
                    channelid[channelid_key]["update_size"] > 5
                )
            # 对NoShorts进行纠正
            if website == "youtube" and (
                "NoShorts" not in channelid_value
                or not isinstance(channelid_value["NoShorts"], bool)
            ):
                channelid[channelid_key]["NoShorts"] = False
            # 对audio_track_language进行纠正
            if website == "youtube" and (
                "audio_track_language" not in channelid_value
                or channelid_value["audio_track_language"] not in languages
            ):
                channelid[channelid_key]["audio_track_language"] = default_config[
                    f"channelid_{website}"
                ][channelid_name]["audio_track_language"]
        if (
            channelid[channelid_key]["InmainRSS"] is False
            and f"{config['address']}/channel_rss/{channelid_value['id']}.xml"
            not in parse.shortcuts_url_original
        ):
            gVar.shortcuts_url[channelid_key] = (
                f"{config['address']}/channel_rss/{channelid_value['id']}.xml"
            )
    return channelid
