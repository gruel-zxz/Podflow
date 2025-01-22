# Podflow/message/update_youtube_bilibili_rss.py
# coding: utf-8

import re
import threading
from Podflow import gVar
from Podflow.basic.file_save import file_save
from Podflow.basic.write_log import write_log
from Podflow.youtube.get import youtube_rss_update
from Podflow.basic.folder_build import folder_build
from Podflow.bilibili.get import bilibili_rss_update


# 更新Youtube和哔哩哔哩频道xml多线程模块
def update_youtube_bilibili_rss():
    pattern_youtube404 = r"Error 404 \(Not Found\)"  # 设置要匹配的正则表达式模式
    pattern_youtube_error = {
        "This channel was removed because it violated our Community Guidelines.": "违反社区准则",
        "This channel does not exist.": "不存在 (ID错误) ",
    }
    pattern_youtube_varys = [
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-2][0-9]:[0-6][0-9]:[0-6][0-9]\+00:00",
        r'starRating count="[0-9]*"',
        r'statistics views="[0-9]*"',
        r"<id>yt:channel:(UC)?(.{22})?</id>",
        r"<yt:channelId>(UC)?(.{22})?</yt:channelId>",
    ]
    youtube_bilibili_rss_update_threads = []  # 创建线程列表
    # Youtube多线程
    for youtube_key, youtube_value in gVar.channelid_youtube_ids.items():
        thread = threading.Thread(
            target=youtube_rss_update,
            args=(
                youtube_key,
                youtube_value,
                pattern_youtube_varys,
                pattern_youtube404,
                pattern_youtube_error,
            ),
        )
        youtube_bilibili_rss_update_threads.append(thread)
        # 开始多线程
        thread.start()
    # 哔哩哔哩多线程
    for bilibili_key, bilibili_value in gVar.channelid_bilibili_ids.items():
        thread = threading.Thread(
            target=bilibili_rss_update, args=(bilibili_key, bilibili_value)
        )
        youtube_bilibili_rss_update_threads.append(thread)
        # 开始多线程
        thread.start()
    # 等待所有线程完成
    for thread in youtube_bilibili_rss_update_threads:
        thread.join()

    # 寻找错误原因
    def youtube_error(youtube_content, pattern_youtube_error):
        for (
            pattern_youtube_error_key,
            pattern_youtube_error_value,
        ) in pattern_youtube_error.items():
            if pattern_youtube_error_key in youtube_content:
                return pattern_youtube_error_value

    # 更新Youtube频道
    for youtube_key, youtube_value in gVar.channelid_youtube_ids.copy().items():
        youtube_response = gVar.channelid_youtube_rss[youtube_key]["content"]
        youtube_response_type = gVar.channelid_youtube_rss[youtube_key]["type"]
        # xml分类及存储
        if youtube_response is not None:
            if youtube_response_type == "dict":
                # 构建频道文件夹
                folder_build(youtube_key, "channel_audiovisual")
            else:
                if youtube_response_type == "html":
                    youtube_content = youtube_response.text
                elif youtube_response_type == "text":
                    youtube_content = youtube_response
                    write_log(f"YouTube频道 {youtube_value} 无法更新")
                else:
                    youtube_content = ""
                # 判断频道id是否正确
                if re.search(pattern_youtube404, youtube_content, re.DOTALL):
                    del gVar.channelid_youtube_ids[youtube_key]  # 删除错误ID
                    write_log(f"YouTube频道 {youtube_value} ID不正确无法获取")
                elif youtube_error_message := youtube_error(
                    youtube_content, pattern_youtube_error
                ):
                    del gVar.channelid_youtube_ids[youtube_key]  # 删除错误ID
                    write_log(f"YouTube频道 {youtube_value} {youtube_error_message}")
                else:
                    # 构建文件
                    file_save(youtube_content, f"{youtube_key}.txt", "channel_id")
                    # 构建频道文件夹
                    folder_build(youtube_key, "channel_audiovisual")
        else:
            if youtube_response_type == "text":
                del gVar.channelid_youtube_ids[youtube_key]
            write_log(f"YouTube频道 {youtube_value} 无法更新")
    # 更新哔哩哔哩频道
    for bilibili_key, bilibili_value in gVar.channelid_bilibili_ids.copy().items():
        bilibili_space = gVar.channelid_bilibili_rss[bilibili_key]["content"]
        bilibili_space_type = gVar.channelid_bilibili_rss[bilibili_key]["type"]
        # xml分类及存储
        if bilibili_space_type == "int":
            del gVar.channelid_bilibili_ids[bilibili_key]  # 删除错误ID
            write_log(f"BiliBili频道 {bilibili_value} ID不正确无法获取")
        elif bilibili_space_type == "json":
            write_log(f"BiliBili频道 {youtube_value} 无法更新")
            if bilibili_space == {}:
                del gVar.channelid_bilibili_ids[bilibili_key]
        else:
            # 构建文件
            file_save(bilibili_space, f"{bilibili_key}.json", "channel_id")
            # 构建频道文件夹
            folder_build(bilibili_key, "channel_audiovisual")
