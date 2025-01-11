# Podflow/download/dl_aideo_video.py
# coding: utf-8

import os
from datetime import datetime
import ffmpeg
import yt_dlp
from Podflow.basic.get_duration import get_duration
from Podflow.basic.write_log import write_log
from Podflow.download.show_progress import show_progress


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
            msg = (
                msg.replace("ERROR: ", "")
                .replace("\033[0;31mERROR:\033[0m ", "")
                .replace(f"{video_url}: ", "")
                .replace("[youtube] ", "")
                .replace("[BiliBili] ", "")
                .replace("[download] ", "")
            )
            if video_url[:2] == "BV":
                msg = msg.replace(f"{video_url[2:]}: ", "")
            print(msg)

    ydl_opts = {
        "outtmpl": f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}",  # 输出文件路径和名称
        "format": f"{format_id}",  # 指定下载的最佳音频和视频格式
        "noprogress": True,
        "quiet": True,
        "progress_hooks": [show_progress],
        "logger": MyLogger(),
        "throttled_rate": "70K",  # 设置最小下载速率为:字节/秒
    }
    if cookies:
        ydl_opts["http_headers"] = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
        }
        ydl_opts["cookiefile"] = cookies  # cookies 是你的 cookies 文件名
    if playlist_num:  # 播放列表的第n个视频
        ydl_opts["playliststart"] = playlist_num
        ydl_opts["playlistend"] = playlist_num
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"{video_website}"])  # 下载指定视频链接的视频
    except Exception as download_video_error:
        write_log(
            f"{video_write_log} \033[31m下载失败\033[0m",
            None,
            True,
            True,
            (f"错误信息: {str(download_video_error)}")
            .replace("ERROR: ", "")
            .replace("\033[0;31mERROR:\033[0m ", "")
            .replace(f"{video_url}: ", "")
            .replace("[youtube] ", "")
            .replace("[download] ", ""),
        )  # 写入下载失败的日志信息
        return video_url


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
    if download_video(
        video_url,
        output_dir,
        output_format,
        format_id,
        video_website,
        video_write_log,
        sesuffix,
        cookies,
        playlist_num,
    ):
        return video_url
    duration_video = get_duration(
        f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}"
    )  # 获取已下载视频的实际时长
    if abs(id_duration - duration_video) <= 1:  # 检查实际时长与预计时长是否一致
        return None
    if duration_video:
        write_log(
            f"{video_write_log} \033[31m下载失败\033[0m\n错误信息: 不完整({id_duration}|{duration_video})"
        )
        os.remove(
            f"channel_audiovisual/{output_dir}/{video_url}{sesuffix}.{output_format}"
        )  # 删除不完整的视频
    return video_url


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
):
    video_id_failed = dl_full_video(
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
        video_id_count += 1
        write_log(f"{video_write_log} 第\033[34m{video_id_count}\033[0m次重新下载")
        video_id_failed = dl_full_video(
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
    return video_id_failed


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
):
    if output_dir_name:
        video_write_log = f"{display_color}{output_dir_name}\033[0m|{video_url}"
    else:
        video_write_log = video_url
    id_duration = video_format[0]
    print_message = (
        "\033[34m开始下载\033[0m 🍪" if cookies else "\033[34m开始下载\033[0m"
    )
    print(
        f"{datetime.now().strftime('%H:%M:%S')}|{video_write_log} {print_message}",
        end="",
    )
    if output_format == "m4a":
        if video_format[1] in ["140", "30280"]:
            print("")
        else:
            print(f" \033[97m{video_format[1]}\033[0m")
        video_id_failed = dl_retry_video(
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
        )
    else:
        print(
            f"\n{datetime.now().strftime('%H:%M:%S')}|\033[34m视频部分开始下载\033[0m \033[97m{video_format[2]}\033[0m"
        )
        video_id_failed = dl_retry_video(
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
        )
        if video_id_failed is None:
            print(
                f"{datetime.now().strftime('%H:%M:%S')}|\033[34m音频部分开始下载\033[0m \033[97m{video_format[1]}\033[0m"
            )
            video_id_failed = dl_retry_video(
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
            )
        if video_id_failed is None:
            print(
                f"{datetime.now().strftime('%H:%M:%S')}|\033[34m开始合成...\033[0m",
                end="",
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
                ffmpeg.run(stream)
                print(" \033[32m合成成功\033[0m")
                # 删除临时文件
                os.remove(f"channel_audiovisual/{output_dir}/{video_url}.part.mp4")
                os.remove(f"channel_audiovisual/{output_dir}/{video_url}.part.m4a")
            except ffmpeg.Error as dl_aideo_video_error:
                video_id_failed = video_url
                write_log(
                    f"\n{video_write_log} \033[31m下载失败\033[0m\n错误信息: 合成失败:{dl_aideo_video_error}"
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
    return video_id_failed
