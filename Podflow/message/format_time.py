# Podflow/message/format_time.py
# coding: utf-8

import time
from datetime import datetime, timedelta, timezone


# 格式化时间及时区模块
def format_time(time_str):
    original_tz = timezone.utc  # 原始时区为UTC
    # 解析时间字符串并转换为datetime对象
    dt = datetime.fromisoformat(
        time_str[:-6] if time_str[-3] == ":" else time_str[:-5]
    ).replace(tzinfo=original_tz)
    # 转换为目标时区
    if time_str[-3] == ":":
        tz = timedelta(
            hours=int(time_str[-6:-3]), minutes=int(f"{time_str[-6]}{time_str[-2:]}")
        )
    else:
        tz = timedelta(
            hours=int(time_str[-5:-2]), minutes=int(f"{time_str[-5]}{time_str[-2:]}")
        )
    dt -= tz
    target_tz = timezone(timedelta(seconds=-(time.timezone + time.daylight)))
    dt_target = dt.astimezone(target_tz)
    return dt_target.strftime("%a, %d %b %Y %H:%M:%S %z")
