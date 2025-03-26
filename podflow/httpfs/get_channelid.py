# podflow/httpfs/get_channelid.py
# coding: utf-8

import re
from podflow.basic.http_client import http_client


def get_response(
    text,
    name,
    re_ucid,
    mod_ucid,
    re_title,
):
    if response := http_client(
        url=text,
        name=name,
        headers_possess=True
    ):
        if mod_ucid == "text":
            ucid = re.search(re_ucid, response.text)
        elif mod_ucid == "url":
            ucid = re.search(re_ucid, response.url)
        else:
            ucid = ""
        title = re.search(re_title, response.text)
        if ucid and title :
            ucid = ucid.group(0)
            title = title.group(0)
            return f'''"{title}": "{ucid}"

"{title}": {{
            "id": "{ucid}",
            "quality": "1080",
            "media": "mp4",
            "InmainRSS": false,
            "update_size": 2
        }}'''
        else:
            return "Network Error"
    else:
        return "Network Error"


def get_channelid(text):
    if text in [None, ""]:
        return ""
    url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
    text_match = url_pattern.search(text)  # 使用 search() 而不是 match()
    if text_match:
        text = text_match.group(0)
        if "youtube" in text:
            return get_response(
                text,
                "youtube",
                r"(?<=https://www.youtube.com/channel/)UC.{22}",
                "text",
                r'(?<=<link itemprop="name" content=").+?(?=")',
            )
        elif "bilibili" in text or "b23.tv" in text:
            return get_response(
                text,
                "bilibili",
                r'(?<=https://space\.bilibili\.com/)([0-9]+)',
                "url",
                r'(?<=<title>).+(?=的个人空间-)',
            )
    else:
        text_match = re.search(r'(?<=UID:)([0-9]+)', text, re.IGNORECASE)
        if text_match:
            text = f"https://space.bilibili.com/{text_match.group(0)}"
            return get_response(
                text,
                "bilibili",
                r'(?<=https://space\.bilibili\.com/)([0-9]+)',
                "url",
                r'(?<=<title>).+(?=的个人空间-)',
            )
        else:
            return "Network Error"
    return "Network Error"
