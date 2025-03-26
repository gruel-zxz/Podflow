# podflow/message/want_retry.py
# coding: utf-8

import re


# 判断是否重试模块
def want_retry(video_url, num=1):
    # 定义正则表达式模式（不区分大小写）
    pattern = rf'\|{video_url}\|(试看|跳过更新|删除或受限|充电专属|直播预约\|a few moments\.)'
    # 读取 Podflow.log 文件
    try:
        with open('Podflow.log', 'r', encoding='utf-8') as file:
            content = file.read()  # 读取文件内容
        # 使用 re.findall() 查找所有匹配项
        matches = re.findall(pattern, content)
        # 计算匹配的个数
        count = len(matches)
    except Exception:
        count = 0
    return count < num or count % num == 0
