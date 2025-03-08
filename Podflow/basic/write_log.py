# Podflow/basic/write_log.py
# coding: utf-8

import re
from datetime import datetime
from Podflow.basic.file_save import file_save


# 日志模块
def write_log(
    log,
    suffix=None,
    display=True,
    time_display=True,
    only_log="",
    file_name="Podflow.log",
):
    # 获取当前的具体时间
    current_time = datetime.now()
    # 格式化输出, 只保留年月日时分秒
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    # 打开文件, 并读取原有内容
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            contents = file.read()
    except FileNotFoundError:
        contents = ""
    # 将新的日志内容添加在原有内容之前
    log_in = re.sub(r"\033\[[0-9;]+m", "", log)
    log_in = re.sub(r"\n", "", log_in)
    if only_log:
        only_log = re.sub(r"\033\[[0-9;]+m", "", str(only_log))
    else:
        only_log = ""
    new_contents = (
        f"{formatted_time} {log_in}{only_log}\n{contents}"
        if only_log
        else f"{formatted_time} {log_in}\n{contents}"
    )
    # 将新的日志内容写入文件
    file_save(new_contents, file_name)
    if display:
        formatted_time_mini = current_time.strftime("%H:%M:%S")
        log_print = f"{formatted_time_mini}|{log}" if time_display else f"{log}"
        log_print = f"{log_print}|{suffix}" if suffix else f"{log_print}"
        print(log_print)
