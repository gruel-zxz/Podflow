# Podflow/upload/add_upload.py
# coding: utf-8

import time
from Podflow import gVar


# 添加新媒体至上传列表模块
def add_upload():
    # 获取video_id_update_format和video_id_failed的值
    video_id_update_format = gVar.video_id_update_format
    video_id_failed = gVar.video_id_failed
    # 遍历video_id_update_format的键值对
    for video_id, video_id_value in video_id_update_format.items():
        # 判断video_id_value是否为字典，并且main不在video_id_failed中
        if (
            isinstance(video_id_value, dict)
            and video_id_value["main"] not in video_id_failed
        ):
            # 构造media_id
            media_id = f"{video_id}.{video_id_value['media']}"
            # 判断gVar.upload_original中是否存在media_id
            if not any(
                item.get("media_id") == media_id for item in gVar.upload_original
            ):
                # 如果不存在，则将media_id、channel_id、media_time、upload、remove、hash添加到gVar.upload_original中
                gVar.upload_original.append(
                    {
                        "media_id": media_id,
                        "channel_id": video_id_value["id"],
                        "media_time": int(time.time()),
                        "upload": False,
                        "remove": False,
                        "hash": None,
                    }
                )
