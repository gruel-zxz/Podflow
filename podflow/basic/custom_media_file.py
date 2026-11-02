# podflow/basic/custom_media_file.py
# coding: utf-8

import os
import json
import hashlib
from podflow.basic.file_save import file_save
from podflow.basic.folder_build import folder_build

# 自定义媒体列表的存放位置(channel_id文件夹下的custom_media.json)
custom_media_folder = "channel_id"
custom_media_file = "custom_media.json"


# 自定义媒体列表文件的完整路径
def get_custom_media_path():
    return os.path.join(os.getcwd(), custom_media_folder, custom_media_file)


# 计算列表的版本号, 使用文件内容的哈希值(文件系统时间戳精度不足, 且连续写入可能相同)
def build_rev(data):
    return hashlib.md5(data).hexdigest()


# 读取自定义媒体列表及其版本号(一次读取, 保证列表与版本号属于同一份内容)
def read_custom_media():
    try:
        with open(get_custom_media_path(), "rb") as file:
            original = file.read()
    except FileNotFoundError:  # 捕获文件不存在异常
        return [], ""  # 文件不存在，视为空列表, 版本号为空
    try:
        custom_media = json.loads(original.decode("utf-8"))
    except (UnicodeDecodeError, json.decoder.JSONDecodeError):
        # 捕获解码错误及json解码错误, 内容损坏时按空列表处理
        # 版本号仍取实际文件内容, 避免被误判为"文件未被改动"
        custom_media = []
    if not isinstance(custom_media, list):  # 非列表格式时同样初始化为空列表
        custom_media = []
    return custom_media, build_rev(original)


# 读取自定义媒体列表, 文件不存在或内容损坏时返回空列表
def get_custom_media():
    return read_custom_media()[0]


# 读取自定义媒体列表当前的版本号, 文件不存在时返回空字符串
def get_custom_media_rev():
    try:
        with open(get_custom_media_path(), "rb") as file:
            return build_rev(file.read())
    except FileNotFoundError:
        return ""


# 保存自定义媒体列表至channel_id文件夹
def save_custom_media(custom_media):
    # 确保channel_id文件夹存在
    folder_build(custom_media_folder)
    # file_save识别到json后缀时会自动序列化, 故直接传入列表(不可传字符串, 否则会被二次编码)
    file_save(
        custom_media,
        custom_media_file,
        custom_media_folder,
    )


# 以"读取-校验版本号-修改-写入"的方式更新列表
# 若读取之后文件被其他进程改动(网页或另一个后台), 则放弃本次写入并返回 None, 避免用旧内容覆盖新内容
def update_custom_media(modify):
    custom_media, original_rev = read_custom_media()
    # 交由调用方原地修改列表, 返回修改后的列表
    custom_media = modify(custom_media)
    # 写入前再次核对版本号, 与读取时不一致说明期间被改动
    if get_custom_media_rev() != original_rev:
        return None
    save_custom_media(custom_media)
    return custom_media
