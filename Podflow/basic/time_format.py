# Podflow/basic/time_format.py
# coding: utf-8


# 格式化时间模块
def time_format(duration):
    if duration is None:
        return "Unknown"
    duration = int(duration)
    hours, remaining_seconds = divmod(duration, 3600)
    minutes = remaining_seconds // 60
    remaining_seconds = remaining_seconds % 60
    if hours > 0:
        return "{:02}:{:02}:{:02}".format(hours, minutes, remaining_seconds)
    else:
        return "{:02}:{:02}".format(minutes, remaining_seconds)
