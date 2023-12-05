#!/usr/bin/env python
# coding: utf-8

import re
import os
from datetime import datetime

def get_txt_files_in_current_directory():
    current_directory = os.getcwd()  # 获取当前工作目录
    txt_files = [f for f in os.listdir(current_directory) if f.endswith('.txt')]
    return txt_files

txt_files = get_txt_files_in_current_directory()

current_time = datetime.now()

formatted_time = current_time.strftime("%Y%m%d")

pattern = r'[0-9]{8}20231205_A747\.txt'

matched_files = [f for f in txt_files if re.search(pattern, f)]

if matched_files:
    with open(matched_files[0], 'r') as file:
        text = file.read()
        #print(text)
else:
    print("文件不存在")

lines = text.strip().split('\n')

data = [line.split('|') for line in lines]

text_fails = ""
for row in data:
    text_fail = ""
    if row[4] == '1' and row[5] != '100.000000':
        if row[5] in ['0.010000', '0.020000', '0.050000', '0.100000', '0.500000', '0.500000', '2.000000']:
            text_fail = f"工号：{row[2]}，纸币{row[5][0:4]}不应存在"
        else:
            if (float(row[7]) * 100) / (float(row[5]) * 100) > 5000:
                text_fail = f"工号：{row[2]}，纸币{row[5][0:len(row[5]) - 4]}过多"
    if row[4] == '2':
        if (float(row[7]) * 100) / (float(row[5]) * 100) > 3000:
            text_fail = f"工号：{row[2]}，硬币{row[5][0:4]}过多"
    if text_fail != "":
        if text_fails == "":
            text_fails = text_fails + text_fail
        else:
            text_fails = text_fails + "\n" + text_fail
if text_fails == "":
    print("券别登记无异常")
else:
    print("券别登记异常信息:\n" + text_fails)
