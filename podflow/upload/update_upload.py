# podflow/upload/update_upload.py
# coding: utf-8

import re
import time
from email.utils import parsedate_tz, mktime_tz
from podflow import gVar
from podflow.basic.file_save import file_save
from podflow.message.get_media_name import get_media_name


# 更新并保存上传列表模块
def update_upload():
    # 如果没有开启上传功能，则直接返回
    if not gVar.config["upload"]:
        return
    # 初始化一个字典，用于存储每个输出目录的媒体名称
    media_name = {}
    # 初始化一个列表，用于存储需要上传的媒体部分
    main_upload = []
    # 获取原始上传列表
    upload_original = gVar.upload_original
    # 获取所有项目
    all_items = gVar.all_items
    # 遍历所有项目，获取每个输出目录的媒体名称
    for output_dir, items_dict in all_items.items():
        media_name[output_dir] = get_media_name(items_dict["type"], items_dict["items"])
    # 遍历原始上传列表，筛选出需要上传的媒体部分
    for upload_part in upload_original:
        if (
            upload_part["channel_id"] in media_name
            and upload_part["media_id"] in media_name[upload_part["channel_id"]]
        ):
            main_upload.append(upload_part)

    # 获取需要上传的媒体部分的ID
    media_ids = [item["media_id"] for item in main_upload if "media_id" in item]
    # 遍历每个输出目录的媒体部分，筛选出需要上传的媒体部分
    for output_dir, media_parts in media_name.items():
        for part in media_parts:
            if part not in media_ids:
                # 构造正则表达式，用于匹配媒体部分
                pattern = rf"<!-- {output_dir} -->(?:(?!<!-- {output_dir} -->).)+channel_audiovisual/{output_dir}/{part}.+?<!-- {output_dir} -->"
                pubdate_text = ""
                # 在所有项目中匹配媒体部分
                if match := re.search(
                    pattern, all_items[output_dir]["items"], flags=re.DOTALL
                ):
                    date_text = match.group()
                    # 在匹配的媒体部分中提取发布日期
                    pattern = r"(?<=<pubDate>).+(?=</pubDate>)"
                    if match := re.search(pattern, date_text):
                        pubdate_text = match.group()
                # 如果发布日期存在，则转换为时间戳；否则，使用当前时间戳
                pubdate_text = (
                    mktime_tz(parsedate_tz(pubdate_text))
                    if parsedate_tz(pubdate_text)
                    else int(time.time())
                )

                # 将需要上传的媒体部分添加到列表中
                main_upload.append(
                    {
                        "media_id": part,
                        "channel_id": output_dir,
                        "media_time": pubdate_text,
                        "upload": False,
                        "remove": False,
                        "hash": None,
                    }
                )

    # 将需要上传的媒体部分保存到文件中
    file_save(main_upload, "upload.json", "channel_data")  # 保存到文件
