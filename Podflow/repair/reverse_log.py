# Podflow/repair/reverse_log.py
# coding: utf-8

import re
from itertools import islice
from Podflow.basic.time_print import time_print


def reverse_log(filename):
    try:
        with open(f"{filename}.log", "r", encoding="utf-8") as file:
            lines = list(islice(file, 10))
    except Exception:
        return
    num = 0
    end_num = len(lines) - 1

    def date_time(num):
        pattern = r"^([0-9]{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])\s(0[0-9]|1[0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])$"
        date_str = lines[num][:19]
        return re.match(pattern, date_str)

    while not date_time(num):
        num += 1
    while not date_time(end_num):
        end_num -= 1
    if end_num > num and lines[num][:19] > lines[end_num][:19]:
        with open(f"{filename}.log", "r", encoding="utf-8") as file:
            lines = file.readlines()
            # 反转行的顺序
            reversed_lines = lines[::-1]
        with open(f"{filename}.log", "w", encoding="utf-8") as file:
            file.writelines(reversed_lines)
            time_print(f"{filename}.log反转成功")
