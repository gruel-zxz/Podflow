# podflow/download/dl_aideo_video.py
# coding: utf-8

import os
import re
import time
import ffmpeg
import yt_dlp
from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.basic.time_print import time_print
from podflow.basic.get_duration import get_duration
from podflow.httpfs.download_bar import download_bar
from podflow.message.media_format import media_format
from podflow.download.show_progress import show_progress
from podflow.message.fail_message_initialize import fail_message_initialize
from podflow.message.get_youtube_and_bilibili_video_format import one_format


# 下载视频模块
def download_video(
    video_url,
    output_dir,
    output_format,
    format_id,
    video_website,
    video_write_log,
    sesuffix="",
    cookies=None,
    playlist_num=None,
):
    class MyLogger:
        def debug(self, msg):
            pass

        def warning(self, msg):
            pass

        def info(self, msg):
            pass

        def error(self, msg):
            msg = fail_message_initialize(msg, video_url).ljust(48)
            time_print(msg, Top=True, Time=False)

    outtmpl = f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}"
    ydl_opts = {
        "outtmpl": outtmpl,  # 输出文件路径和名称
        "format": f"{format_id}",  # 指定下载的最佳音频和视频格式
        "noprogress": True,
        "quiet": True,
        "progress_hooks": [show_progress],
        "logger": MyLogger(),
        "throttled_rate": "70K",  # 设置最小下载速率为:字节/秒
    }
    if cookies:
        if "www.bilibili.com" in video_website:
            ydl_opts["http_headers"] = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com/",
            }
        elif "www.youtube.com" in video_website:
            remote_target = "ejs:github"
            ydl_opts["remote_components"]= remote_target,
            ydl_opts["http_headers"] = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                "Referer": "https://www.youtube.com/",
            }
        ydl_opts["cookiefile"] = cookies  # cookies 是你的 cookies 文件名
    if playlist_num:  # 播放列表的第n个视频
        ydl_opts["playliststart"] = playlist_num
        ydl_opts["playlistend"] = playlist_num
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"{video_website}"])  # 下载指定视频链接的视频
        return None, None
    except Exception as download_video_error:
        fail_info = fail_message_initialize(download_video_error, video_url).replace(
            "\n", ""
        )
        remove_info = ""
        if (
            fail_info == ""
            or re.search(r"请求拒绝|数据不完整|传输中断|请求超时|响应超时", fail_info)
        ) and "www.youtube.com" in video_website:
            if fail_info != "":
                remove_info_part = "|"
            else:
                remove_info_part = ""
            if os.path.isfile(outtmpl):
                os.remove(outtmpl)
                remove_info = remove_info_part + "已删除失败文件"
            elif os.path.isfile(outtmpl + ".part"):
                os.remove(outtmpl + ".part")
                remove_info = remove_info_part + "已删除部分失败文件"
        write_log(
            f"{video_write_log} \033[31m下载失败\033[0m",
            None,
            True,
            True,
            f"错误信息: {fail_info}{remove_info}",
        )  # 写入下载失败的日志信息
        download_bar(mod=2, status="下载失败")
        return video_url, fail_info


# 视频完整下载模块
def dl_full_video(
    video_url,
    output_dir,
    output_format,
    format_id,
    id_duration,
    video_website,
    video_write_log,
    sesuffix="",
    cookies=None,
    playlist_num=None,
):
    video_id_failed, fail_info = download_video(
        video_url,
        output_dir,
        output_format,
        format_id,
        video_website,
        video_write_log,
        sesuffix,
        cookies,
        playlist_num,
    )
    if video_id_failed:
        return video_url, fail_info
    duration_video = get_duration(
        f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}"
    )  # 获取已下载视频的实际时长
    if (
        duration_video is not None and abs(id_duration - duration_video) <= 1
    ):  # 检查实际时长与预计时长是否一致
        return None, None
    if duration_video:
        fail_info = f"不完整({id_duration}|{duration_video}"
        write_log(f"{video_write_log} \033[31m下载失败\033[0m\n错误信息: {fail_info})")
        download_bar(mod=2, status="下载失败")
        os.remove(
            f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}"
        )  # 删除不完整的视频
    return video_url, fail_info


# 视频重试下载模块
def dl_retry_video(
    video_url,
    output_dir,
    output_format,
    format_id,
    id_duration,
    retry_count,
    video_website,
    video_write_log,
    sesuffix="",
    cookies=None,
    playlist_num=None,
    youtube_cookie_switch=False,
):
    duration_and_id = []
    if youtube_cookie_switch:
        video_id_count_num = 0
    elif retry_count > 1:
        video_id_count_num = 1
    else:
        video_id_count_num = 0
    video_id_failed, _ = dl_full_video(
        video_url,
        output_dir,
        output_format,
        format_id,
        id_duration,
        video_website,
        video_write_log,
        sesuffix,
        cookies,
        playlist_num,
    )
    # 下载失败后重复尝试下载视频
    video_id_count = 0
    while video_id_count < retry_count and video_id_failed:
        if (
            cookies is None
            and "www.youtube.com" in video_website
            and gVar.youtube_cookie
        ):
            cookies = "channel_data/yt_dlp_youtube.txt"
            if video_id_count == video_id_count_num:
                write_log(f"{video_write_log} 重新获取媒体信息 🍪")
                gVar.video_id_update_format[video_url]["cookies"] = cookies
                id_update_format = media_format(
                    video_website,
                    video_url,
                    gVar.video_id_update_format[video_url]["media"],
                    gVar.video_id_update_format[video_url]["quality"],
                    gVar.video_id_update_format[video_url]["cookies"],
                    gVar.video_id_update_format[video_url]["language"],
                )
            if isinstance(id_update_format, list):
                if len(id_update_format) == 1:
                    one_format(id_update_format, video_url)
                    duration_and_id = gVar.video_id_update_format[video_url]["format"]
                    if output_format == "m4a":
                        format_id = duration_and_id[1]
                    else:
                        format_id = duration_and_id[2]
                    write_log(f"{video_write_log} \033[32m获取成功\033[0m")
                else:
                    write_log(f"{video_write_log} \033[31m获取失败\033[0m\n错误信息: 该媒体存在分集, 请打开【YouTube 🍪】按钮")
            else:
                def get_fail_info(id_update_format):
                    for fail_info in ["年龄限制", "需登录", "请求拒绝", "无法获取音频ID", "年龄验证"]:
                        if fail_info in id_update_format:
                            return fail_info
                    return None
                if fail_info := get_fail_info(id_update_format):
                    id_update_format = f"\033[31m{fail_info}\033[0m(Cookies错误)"
                write_log(f"{video_write_log} \033[31m获取失败\033[0m\n错误信息: {id_update_format}")
        video_id_count += 1
        if "www.youtube.com" in video_website:
            time.sleep(gVar.config["youtube_download_span"])
        if cookies:
            write_log(
                f"{video_write_log} 第\033[34m{video_id_count}\033[0m次重新下载 🍪"
            )
        else:
            write_log(f"{video_write_log} 第\033[34m{video_id_count}\033[0m次重新下载")
        video_id_failed, _ = dl_full_video(
            video_url,
            output_dir,
            output_format,
            format_id,
            id_duration,
            video_website,
            video_write_log,
            sesuffix,
            cookies,
            playlist_num,
        )
    return video_id_failed, duration_and_id


# 音视频总下载模块
def dl_aideo_video(
    video_url,
    output_dir,
    output_format,
    video_format,
    retry_count,
    video_website,
    output_dir_name="",
    cookies=None,
    playlist_num=None,
    display_color="\033[95m",
    title_name="",
):
    if gVar.youtube_cookie_switch and gVar.youtube_cookie:
        cookies = "channel_data/yt_dlp_youtube.txt"
        youtube_cookie_switch = True
    else:
        youtube_cookie_switch = False
    if output_dir_name:
        video_write_log = f"{display_color}{output_dir_name}\033[0m|{video_url}"
    else:
        video_write_log = video_url
    id_duration = video_format[0]
    print_message = (
        "\033[34m开始下载\033[0m 🍪" if cookies else "\033[34m开始下载\033[0m"
    )
    if "www.youtube.com" in video_website:
        time.sleep(gVar.config["youtube_download_span"])
    time_print(
        f"{video_write_log} {print_message}",
        NoEnter=True,
    )
    download_bar(
        mod=0,
        per=0,
        idname=output_dir_name,
        nametext=title_name,
        file=f"{video_url}.{output_format}",
    )
    if output_format == "m4a":
        if video_format[1] in ["140", "30280"]:
            time_print(
                "",
                Time=False,
            )
        else:
            time_print(
                f" \033[97m{video_format[1]}\033[0m",
                Time=False,
            )
        video_id_failed, _ = dl_retry_video(
            video_url,
            output_dir,
            "m4a",
            video_format[1],
            id_duration,
            retry_count,
            video_website,
            video_write_log,
            "",
            cookies,
            playlist_num,
            youtube_cookie_switch,
        )
    else:
        time_print(
            "",
            Time=False,
        )
        time_print(
            f"\033[34m视频部分开始下载\033[0m \033[97m{video_format[2]}\033[0m",
        )
        video_id_failed, duration_and_id = dl_retry_video(
            video_url,
            output_dir,
            "mp4",
            video_format[2],
            id_duration,
            retry_count,
            video_website,
            video_write_log,
            ".part",
            cookies,
            playlist_num,
            youtube_cookie_switch,
        )
        if video_id_failed is None:
            if duration_and_id:
                duration_and_id = video_format
            time_print(
                f"\033[34m音频部分开始下载\033[0m \033[97m{video_format[1]}\033[0m",
            )
            video_id_failed, _ = dl_retry_video(
                video_url,
                output_dir,
                "m4a",
                video_format[1],
                id_duration,
                retry_count,
                video_website,
                video_write_log,
                ".part",
                cookies,
                playlist_num,
                youtube_cookie_switch,
            )
        if video_id_failed is None:
            time_print(
                "\033[34m开始合成...\033[0m",
                NoEnter=True,
            )
            # 指定视频文件和音频文件的路径
            video_file = f"channel_audiovisual/{output_dir}/{video_url}.part.mp4"
            audio_file = f"channel_audiovisual/{output_dir}/{video_url}.part.m4a"
            output_file = f"channel_audiovisual/{output_dir}/{video_url}.mp4"
            try:
                # 使用 ffmpeg-python 合并视频和音频
                video = ffmpeg.input(video_file)
                audio = ffmpeg.input(audio_file)
                stream = ffmpeg.output(
                    audio, video, output_file, vcodec="copy", acodec="copy"
                )
                ffmpeg.run(stream, quiet=True)
                time_print(" \033[32m合成成功\033[0m", Time=False)
                # 删除临时文件
                os.remove(f"channel_audiovisual/{output_dir}/{video_url}.part.mp4")
                os.remove(f"channel_audiovisual/{output_dir}/{video_url}.part.m4a")
            except ffmpeg.Error as dl_aideo_video_error:
                video_id_failed = video_url
                time_print(
                    "",
                    Time=False,
                )
                write_log(
                    f"{video_write_log} \033[31m下载失败\033[0m\n错误信息: 合成失败:{dl_aideo_video_error}"
                )
    if video_id_failed is None:
        if output_format == "m4a":
            only_log = f" {video_format[1]}"
        else:
            only_log = f" {video_format[1]}+{video_format[2]}"
        if cookies:
            only_log += " Cookies"
        write_log(
            f"{video_write_log} \033[32m下载成功\033[0m", None, True, True, only_log
        )  # 写入下载成功的日志信息
        download_bar(mod=2, status="下载成功")
    return video_id_failed
