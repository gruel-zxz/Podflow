# Podflow/basic/get_duration.py
# coding: utf-8

import math
import ffmpeg
from Podflow.basic.write_log import write_log


# 获取已下载视频时长模块
def get_duration(file_path):
    try:
        # 调用ffmpeg获取视频文件的时长信息
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        return math.ceil(duration)
    except ffmpeg.Error as e:
        error_note = e.stderr.decode('utf-8').splitlines()[-1]
        write_log(f"\033[31mError:\033[0m {error_note}")
