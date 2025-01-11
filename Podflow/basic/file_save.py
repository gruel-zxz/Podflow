# Podflow/basic/file_save.py
# coding: utf-8

import os
import json


# 文件保存模块
def file_save(content, file_name, folder=None):
    # 如果指定了文件夹则将文件保存到指定的文件夹中
    if folder:
        file_path = os.path.join(os.getcwd(), folder, file_name)
    else:
        # 如果没有指定文件夹则将文件保存在当前工作目录中
        file_path = os.path.join(os.getcwd(), file_name)
    # 保存文件
    with open(file_path, "w", encoding="utf-8") as file:
        if "." in file_name and file_name.split(".")[-1] == "json":
            json.dump(content, file, ensure_ascii=False, indent=4)
        else:
            file.write(content)
