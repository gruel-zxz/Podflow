# podflow/basic/file_save.py
# coding: utf-8

import os
import json


# 文件保存模块
def file_save(content, file_name, folder=None, binary=False):
    # 如果指定了文件夹则将文件保存到指定的文件夹中
    if folder:
        file_path = os.path.join(os.getcwd(), folder, file_name)
    else:
        # 如果没有指定文件夹则将文件保存在当前工作目录中
        file_path = os.path.join(os.getcwd(), file_name)
    # 保存文件
    if binary:
        # 使用分块读取和写入的方式处理二进制文件
        with open(file_path, "wb") as dest_file:
            while True:
                chunk = content.read(8192)  # 每次读取 8KB 的数据
                if not chunk:
                    break  # 读取完毕
                dest_file.write(chunk)
    else:
        with open(file_path, "w", encoding="utf-8") as file:
            # 如果文件名中包含"."且文件类型为json，则将内容以json格式保存
            if "." in file_name and file_name.split(".")[-1] == "json":
                json.dump(content, file, ensure_ascii=False, indent=4)
            else:
                # 否则将内容以文本格式保存
                file.write(content)
