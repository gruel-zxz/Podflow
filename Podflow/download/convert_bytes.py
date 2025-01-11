# Podflow/download/convert_bytes.py
# coding: utf-8


# 格式化字节模块
def convert_bytes(byte_size, units=None, outweigh=1024):
    if units is None:
        units = [" B", "KB", "MB", "GB"]
    if byte_size is None:
        byte_size = 0
    # 初始单位是字节
    unit_index = 0
    # 将字节大小除以1024直到小于1024为止
    while byte_size > outweigh and unit_index < len(units) - 1:
        byte_size /= 1024.0
        unit_index += 1
    # 格式化结果并返回
    return f"{byte_size:.2f}{units[unit_index]}"
