# Podflow/basic/get_file_list.py
# coding: utf-8

import os
import re
from Podflow.basic.list_merge_tidy import list_merge_tidy


# 获取文件列表和分P列表
def get_file_list(video_key, video_media="m4a", length=12):
    media = ("m4a", "mp4", "part") if video_media == "m4a" else ("mp4", "part")
    try:
        content_id = [
            file  # 获取文件名（包括扩展名）
            for file in os.listdir(
                f"channel_audiovisual/{video_key}"
            )  # 遍历指定目录下的所有文件
            if file.endswith(media)  # 筛选出以 media 结尾的文件
        ]
        content_id_items = []
        items_counts = {}
        for id in content_id:
            if len(id) > length + 4:
                content_id_items.append(id)
            if ".part" in id:
                items_counts[id[:length]] = 0
        content_id_items = [id[:length] for id in content_id_items]
        for id in content_id_items:
            if id not in items_counts:
                qtys = content_id_items.count(id)
                if video_media == "m4a":
                    pattern = re.compile(rf"{id}_[0-9]*\.(m4a|mp4)")
                else:
                    pattern = re.compile(rf"{id}_[0-9]*\.(mp4)")
                if len([item for item in content_id if pattern.search(item)]) == qtys:
                    items_counts[id] = qtys
                else:
                    fail = False
                    for qty in range(qtys):
                        if video_media == "m4a":
                            if (
                                f"{id}_p{qty + 1}.m4a" not in content_id
                                and f"{id}_p{qty + 1}.mp4" not in content_id
                            ):
                                fail = True
                        elif f"{id}_p{qty + 1}.mp4" not in content_id:
                            fail = True
                    items_counts[id] = 0 if fail else qtys
        content_id = list_merge_tidy(content_id, [], length)
        for id, num in items_counts.copy().items():
            if num in [1, 0] and id in content_id:
                content_id.remove(id)
                del items_counts[id]
    except Exception:
        content_id = []
        items_counts = {}
    return content_id, items_counts
