# podflow/httpfs/progress_bar.py
# coding: utf-8

import random
from podflow import gVar


def progress_update(
    ratio,
    added=False,
    refresh=0,
    num=0
):
    state = {
        1: "准备中",
        2: "构建中",
        3: "已完成",
    }
    if num != 0:
        ratio +=random.uniform(0, num)
    if added:
        ratio += gVar.index_message["schedule"][1]
    gVar.index_message["schedule"][1] = ratio
    if refresh != 0:
        gVar.index_message["schedule"][0] = state[refresh]


def progress_bar(ratio_part, maximum):
    ratio = gVar.index_message["schedule"][1] + ratio_part
    if ratio > maximum:
        ratio = maximum
    progress_update(ratio)
