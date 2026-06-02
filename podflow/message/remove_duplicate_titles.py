# podflow/message/remove_duplicate_titles.py
# coding: utf-8

import re
from datetime import datetime
from podflow import gVar


def get_all_titles(output_dir):
    original_title = {}
    for channelid_key, get_xmls_original_key in gVar.xmls_original.items():
        if output_dir != channelid_key:
            title = re.findall(
                r"(?<=<title>).+(?=</title>)", get_xmls_original_key
            )
            pubdate = re.findall(
                r"(?<=<pubDate>).+(?=</pubDate>)", get_xmls_original_key
            )
            original_title.update(dict(zip(title, pubdate)))
    return original_title


def duplicate_titles(original_title, title, pubdate):
    if title in original_title:
        original_pubdate = original_title[title]
        time_format = "%a, %d %b %Y %H:%M:%S %z"
        time = datetime.strptime(pubdate, time_format)
        original_time = datetime.strptime(original_pubdate, time_format)
        if time >= original_time:
            return True
    return False
