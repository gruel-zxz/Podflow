# Podflow/message/get_media_name.py
# coding: utf-8

import re


# 定义一个函数，用于获取媒体名称
def get_media_name(id_type, items):
    # 如果id_type为youtube
    if id_type == "youtube":
        # 使用正则表达式匹配items中的youtube链接，返回匹配结果
        return re.findall(
            r"(?:/UC.{22}/)(.{11}\.m4a|.{11}\.mp4)(?=\"|\?)",
            items,
        )
    # 如果id_type为bilibili
    elif id_type == "bilibili":
        # 使用正则表达式匹配items中的bilibili链接，返回匹配结果
        return re.findall(
            r"(?:/[0-9]+/)(BV.{10}\.m4a|BV.{10}\.mp4|BV.{10}_p[0-9]+\.m4a|BV.{10}_p[0-9]+\.mp4|BV.{10}_[0-9]{9}\.m4a|BV.{10}_[0-9]{9}\.mp4)(?=\"|\?)",
            items,
        )
    # 如果id_type不是youtube或bilibili
    else:
        # 返回空列表
        return []
