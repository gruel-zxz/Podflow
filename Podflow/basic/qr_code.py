# Podflow/basic/qr_code.py
# coding: utf-8

import math
import qrcode


# 网址二维码模块
def qr_code(data):
    # 创建一个QRCode对象
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=0,
    )
    # 设置二维码的数据
    qr.add_data(data)
    # 获取QR Code矩阵
    qr.make(fit=True)
    matrix = qr.make_image(fill_color="black", back_color="white").modules
    # 获取图像的宽度和高度
    width, height = len(matrix), len(matrix)
    height_double = math.ceil(height / 2)
    # 转换图像为ASCII字符
    fonts = ["▀", "▄", "█", " "]
    ascii_art = ""
    for y in range(height_double):
        if (y + 1) * 2 - 1 >= height:
            for x in range(width):
                ascii_art += (
                    fonts[0] if matrix[(y + 1) * 2 - 2][x] is True else fonts[3]
                )
        else:
            for x in range(width):
                if (
                    matrix[(y + 1) * 2 - 2][x] is True
                    and matrix[(y + 1) * 2 - 1][x] is True
                ):
                    ascii_art += fonts[2]
                elif (
                    matrix[(y + 1) * 2 - 2][x] is True
                    and matrix[(y + 1) * 2 - 1][x] is False
                ):
                    ascii_art += fonts[0]
                elif (
                    matrix[(y + 1) * 2 - 2][x] is False
                    and matrix[(y + 1) * 2 - 1][x] is True
                ):
                    ascii_art += fonts[1]
                else:
                    ascii_art += fonts[3]
            ascii_art += "\n"
    print(ascii_art)
    return height_double
