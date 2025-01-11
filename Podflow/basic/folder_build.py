# Podflow/basic/folder_build.py
# coding: utf-8

import os
from Podflow.basic.write_log import write_log


# 构建文件夹模块
def folder_build(folder_name, parent_folder_name=None):
    if parent_folder_name:
        folder_path = os.path.join(os.getcwd(), parent_folder_name, folder_name)
    else:
        folder_path = os.path.join(os.getcwd(), folder_name)
    if not os.path.exists(folder_path):  # 判断文件夹是否存在
        os.makedirs(folder_path)  # 创建文件夹
        write_log(f"文件夹{folder_name}创建成功")
