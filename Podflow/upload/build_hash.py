# podflow/upload/build_hash.py
# coding: utf-8

import hashlib


# 定义一个函数，用于计算文件的哈希值
def build_hash(file):
    # 获取hashlib模块中的sha256函数
    hash_func = getattr(hashlib, "sha256")()
    # 循环读取文件内容，每次读取4096字节
    for chunk in iter(lambda: file.read(4096), b''):
        # 更新哈希值
        hash_func.update(chunk)
    # 返回哈希值的十六进制表示
    return hash_func.hexdigest()
