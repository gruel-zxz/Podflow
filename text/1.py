import qrcode
import math

# 创建一个QRCode对象
qr = qrcode.QRCode(version=1,error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=0,)
# 设置二维码的数据
data = " https://raw.githubusercontent.com/gruel-zxz/podflow/main/channel_rss/UC9RS8EzXdRJyYDkwtcsWOuA.xml"
qr.add_data(data)
# 创建二维码图像
qr.make(fit=True)
# 创建一个PIL图像对象
img = qr.make_image(fill_color="black", back_color="white")
# 获取图像的宽度和高度
width, height = img.size
height_double = math.ceil(height/2)
# 转换图像为ASCII字符
ascii_art = ""
for y in range(height_double):
    if (y+1)*2-1 >= height:
        for x in range(width):
            if img.getpixel((x, (y+1)*2-2)) == 0:
                ascii_art += "▀"
            else:
                ascii_art += " "
    else:
        for x in range(width):
            if img.getpixel((x, (y+1)*2-2)) == 0 and img.getpixel((x, (y+1)*2-1)) == 0:
                ascii_art += "█"
            elif img.getpixel((x, (y+1)*2-2)) == 0 and img.getpixel((x, (y+1)*2-1)) != 0:
                ascii_art += "▀"
            elif img.getpixel((x, (y+1)*2-2)) != 0 and img.getpixel((x, (y+1)*2-1)) == 0:
                ascii_art += "▄"
            else:
                ascii_art += " "
    ascii_art += "\n"
# 输出ASCII艺术
print(ascii_art)