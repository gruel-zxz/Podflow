# podflow/basic/qr_code.py
# coding: utf-8

import math
import pyqrcode
from podflow.basic.time_print import time_print


# 网址二维码模块
def qr_code(
    data,
    to_html=False,
    num=None
):
    qr = pyqrcode.create(
        data,
        error='L',  # 对应于ERROR_CORRECT_L，可选值: 'L','M','Q','H'
    )
    # 获取QR码矩阵（作为二维数组）
    matrix = qr.code    # 获取图像的宽度和高度
    width, height = len(matrix), len(matrix)
    height_double = math.ceil(height / 2)
    # 转换图像为ASCII字符
    fonts = ["▀", "▄", "█", " "]
    ascii_art = ""
    for y in range(height_double):
        if (y + 1) * 2 - 1 >= height:
            for x in range(width):
                ascii_art += (
                    fonts[0] if matrix[(y + 1) * 2 - 2][x] == 1 else fonts[3]
                )
        else:
            for x in range(width):
                if (
                    matrix[(y + 1) * 2 - 2][x] == 1
                    and matrix[(y + 1) * 2 - 1][x] == 1
                ):
                    ascii_art += fonts[2]
                elif (
                    matrix[(y + 1) * 2 - 2][x] == 1
                    and matrix[(y + 1) * 2 - 1][x] == 0
                ):
                    ascii_art += fonts[0]
                elif (
                    matrix[(y + 1) * 2 - 2][x] == 0
                    and matrix[(y + 1) * 2 - 1][x] == 1
                ):
                    ascii_art += fonts[1]
                else:
                    ascii_art += fonts[3]
            ascii_art += "\n"
    Qrcode = data if to_html else ""
    time_print(
        ascii_art,
        Time=False,
        Qrcode=Qrcode,
        Number=num,
    )
    return height_double
