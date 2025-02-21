# Podflow/makeup/del_makeup_format_fail.py
# coding: utf-8

import re
from Podflow import gVar


# 删除无法补全的媒体模块
def del_makeup_format_fail():
    for video_id, id_value in gVar.make_up_file_format_fail.items():
        pattern_video_fail_item = rf"<!-- {id_value} -->(?:(?!<!-- {id_value} -->).)+?<guid>{video_id}</guid>.+?<!-- {id_value} -->"
        replacement_video_fail_item = f"<!-- {id_value} -->"
        gVar.all_items[id_value]["items"] = re.sub(
            pattern_video_fail_item,
            replacement_video_fail_item,
            gVar.all_items[id_value]["items"],
            flags=re.DOTALL,
        )
