# podflow/upload/find_media_index.py
# coding: utf-8


# 查找位置模块
def find_media_index(upload_original, target_media_id):
    for index, item in enumerate(upload_original):
        if item.get("media_id") == target_media_id:
            return index  # 返回找到的索引
    return -1
