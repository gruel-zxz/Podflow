# Podflow/message_get.py
# coding: utf-8

import os
import re
import threading
from Podflow import gVar
from Podflow.youtube_get import youtube_rss_update
from Podflow.bilibili_get import bilibili_rss_update
from Podflow.basis import folder_build, write_log, file_save

channelid_youtube_ids = gVar.channelid_youtube_ids
channelid_youtube_rss = gVar.channelid_youtube_rss
channelid_bilibili_ids = gVar.channelid_bilibili_ids
channelid_bilibili_rss = gVar.channelid_bilibili_rss

# 更新Youtube和哔哩哔哩频道xml多线程模块
def update_youtube_bilibili_rss():
    pattern_youtube404 = r"Error 404 \(Not Found\)"  # 设置要匹配的正则表达式模式
    pattern_youtube_error = {
        "This channel was removed because it violated our Community Guidelines.": "违反社区准则",
        "This channel does not exist.": "不存在（ID错误）",
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
    for youtube_key, youtube_value in channelid_youtube_ids.items():
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
    for bilibili_key, bilibili_value in channelid_bilibili_ids.items():
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
    for youtube_key, youtube_value in channelid_youtube_ids.copy().items():
        youtube_response = channelid_youtube_rss[youtube_key]["content"]
        youtube_response_type = channelid_youtube_rss[youtube_key]["type"]
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
                    del channelid_youtube_ids[youtube_key]  # 删除错误ID
                    write_log(f"YouTube频道 {youtube_value} ID不正确无法获取")
                elif youtube_error_message := youtube_error(
                    youtube_content, pattern_youtube_error
                ):
                    del channelid_youtube_ids[youtube_key]  # 删除错误ID
                    write_log(f"YouTube频道 {youtube_value} {youtube_error_message}")
                else:
                    # 构建文件
                    file_save(youtube_content, f"{youtube_key}.txt", "channel_id")
                    # 构建频道文件夹
                    folder_build(youtube_key, "channel_audiovisual")
        else:
            if youtube_response_type == "text":
                del channelid_youtube_ids[youtube_key]
            write_log(f"YouTube频道 {youtube_value} 无法更新")
    # 更新哔哩哔哩频道
    for bilibili_key, bilibili_value in channelid_bilibili_ids.copy().items():
        bilibili_space = channelid_bilibili_rss[bilibili_key]["content"]
        bilibili_space_type = channelid_bilibili_rss[bilibili_key]["type"]
        # xml分类及存储
        if bilibili_space_type == "int":
            del channelid_bilibili_ids[bilibili_key]  # 删除错误ID
            write_log(f"BiliBili频道 {bilibili_value} ID不正确无法获取")
        elif bilibili_space_type == "json":
            write_log(f"BiliBili频道 {youtube_value} 无法更新")
            if bilibili_space == {}:
                del channelid_bilibili_ids[bilibili_key]
        else:
            # 构建文件
            file_save(bilibili_space, f"{bilibili_key}.json", "channel_id")
            # 构建频道文件夹
            folder_build(bilibili_key, "channel_audiovisual")


# 判断是否重试模块
def want_retry(video_url, num=1):
    # 定义正则表达式模式（不区分大小写）
    pattern = (
        rf"\|{video_url}\|(试看|跳过更新|删除或受限|充电专属|直播预约\|a few moments\.)"
    )
    # 读取 Podflow.log 文件
    try:
        with open("Podflow.log", "r", encoding="utf-8") as file:
            content = file.read()  # 读取文件内容
        # 使用 re.findall() 查找所有匹配项
        matches = re.findall(pattern, content)
        # 计算匹配的个数
        count = len(matches)
    except (FileNotFoundError, Exception):
        count = 0
    if count < num or count % num == 0:
        return True
    else:
        return False


# 输出需要更新的信息模块
def update_information_display(
    channelid_ids_update, content_id_update, content_id_backward_update, name
):
    if channelid_ids_update:
        print_channelid_ids_update = f"需更新的{name}频道:\n"
        # 获取命令行字节宽度
        try:
            terminal_width = os.get_terminal_size().columns
        except OSError:
            terminal_width = 47
        # 尝试拆分输出
        try:
            for channelid_key, channelid_value in channelid_ids_update.items():
                if len(print_channelid_ids_update) != len(name) + 8:
                    if (
                        len(
                            re.sub(
                                r"\033\[[0-9;]+m",
                                "",
                                print_channelid_ids_update.split("\n")[-1],
                            ).encode("GBK")
                        )
                        + len(f" | {channelid_value}".encode("utf-8"))
                        <= terminal_width
                    ):
                        print_channelid_ids_update += " | "
                    else:
                        print_channelid_ids_update += "\n"
                if (
                    channelid_key in content_id_update
                    and channelid_key in content_id_backward_update
                ):
                    print_channelid_ids_update += f"\033[34m{channelid_value}\033[0m"
                elif channelid_key in content_id_update:
                    print_channelid_ids_update += f"\033[32m{channelid_value}\033[0m"
                elif channelid_key in content_id_backward_update:
                    print_channelid_ids_update += f"\033[36m{channelid_value}\033[0m"
                else:
                    print_channelid_ids_update += f"\033[33m{channelid_value}\033[0m"
        # 如果含有特殊字符将使用此输出
        except Exception:
            len_channelid_ids_update = len(channelid_ids_update)
            count_channelid_ids_update = 1
            for channelid_key, channelid_value in channelid_ids_update.items():
                if (
                    channelid_key in content_id_update
                    and channelid_key in content_id_backward_update
                ):
                    print_channelid_ids_update += f"\033[34m{channelid_value}\033[0m"
                elif channelid_key in content_id_update:
                    print_channelid_ids_update += f"\033[32m{channelid_value}\033[0m"
                elif channelid_key in content_id_backward_update:
                    print_channelid_ids_update += f"\033[36m{channelid_value}\033[0m"
                else:
                    print_channelid_ids_update += f"\033[33m{channelid_value}\033[0m"
                if count_channelid_ids_update != len_channelid_ids_update:
                    if count_channelid_ids_update % 2 != 0:
                        print_channelid_ids_update += " | "
                    else:
                        print_channelid_ids_update += "\n"
                    count_channelid_ids_update += 1
        write_log(print_channelid_ids_update)
