# Podflow/makeup/del_makeup_yt_format_fail.py
# coding: utf-8

import re
from Podflow import gVar


# 删除无法补全的媒体模块
def del_makeup_yt_format_fail(overall_rss):
    for video_id, id_value in gVar.make_up_file_format_fail.items():
        pattern_video_fail_item = rf"<!-- {id_value} -->(?:(?!<!-- {id_value} -->).)+?<guid>{video_id}</guid>.+?<!-- {id_value} -->"
        replacement_video_fail_item = f"<!-- {id_value} -->"
        overall_rss = re.sub(
            pattern_video_fail_item,
            replacement_video_fail_item,
            overall_rss,
            flags=re.DOTALL,
        )
    return overall_rss
