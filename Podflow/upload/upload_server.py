# podflow/upload/upload_server.py
# coding: utf-8

import json


def get_uploads_original():
    try:
        # 尝试打开并读取 JSON 文件
        with open("channel_data/upload_server.json", "r") as file:
            uploads_original = file.read()  # 读取原始上传数据
        uploads_original = json.loads(
            uploads_original
        )  # 将读取的字符串转换为 Python 对象（列表或字典）
    except Exception:
        # 如果读取或解析失败，将 upload_original 初始化为空列表
        uploads_original = []
