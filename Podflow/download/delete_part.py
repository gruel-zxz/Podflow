# podflow/download/delete_part.py
# coding: utf-8

import os
import fnmatch
from podflow.basic.write_log import write_log


# 删除下载失败媒体模块
def delete_part(channelid_ids):
    relative_path = "channel_audiovisual"
    parent_folder_path = os.path.abspath(relative_path)
    for root, _, filenames in os.walk(parent_folder_path):
        for filename in fnmatch.filter(filenames, '*.part'):
            file_path = os.path.join(root, filename)
            os.remove(file_path)
            ids = os.path.basename(root).split('/')[-1]
            if ids in channelid_ids:
                ids = channelid_ids[ids]
            write_log(f"{ids}|{filename}已删除")
