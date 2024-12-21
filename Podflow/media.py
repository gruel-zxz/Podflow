# Podflow/media.py
# coding: utf-8

import re
import os
import math
import ffmpeg
import yt_dlp
from datetime import datetime
from Podflow.basis import write_log, show_progress

# 获取媒体时长和ID模块
def media_format(video_website, video_url, media="m4a", quality="480", cookies=None):
    fail_message = None
    class MyLogger:
        def debug(self, msg):
            pass
        def warning(self, msg):
            pass
        def info(self, msg):
            pass
        def error(self, msg):
            pass
    def duration_and_formats(video_website, video_url):
        fail_message, infos = None, []
        try:
            # 初始化 yt_dlp 实例, 并忽略错误
            ydl_opts = {
                "no_warnings": True,
                "quiet": True,  # 禁止非错误信息的输出
                "logger": MyLogger(),
            }
            if cookies:
                ydl_opts["http_headers"] = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                    "Referer": "https://www.bilibili.com/",
                }
                ydl_opts["cookiefile"] = cookies  # cookies 是你的 cookies 文件名
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 使用提供的 URL 提取视频信息
                if info_dict := ydl.extract_info(
                    f"{video_website}", download=False
                ):
                    # 获取视频时长并返回
                    entries = info_dict.get("entries", None)
                    download_url = info_dict.get("original_url", None)
                    if entries:
                        for playlist_num, entry in enumerate(entries):
                            infos.append({
                                "title": entry.get("title"),
                                "duration": entry.get("duration"),
                                "formats": entry.get("formats"),
                                "timestamp": entry.get("timestamp"),
                                "id": entry.get("id"),
                                "description": entry.get("description"),
                                "url": entry.get("webpage_url"),
                                "image": entry.get("thumbnail"),
                                "download": {
                                    "url": download_url,
                                    "num": playlist_num + 1,
                                },
                                "format_note": entry.get("format_note"),
                            })
                    else:
                        infos.append({
                            "title": info_dict.get("title"),
                            "duration": info_dict.get("duration"),
                            "formats": info_dict.get("formats"),
                            "timestamp": info_dict.get("timestamp"),
                            "id": info_dict.get("id"),
                            "description": info_dict.get("description"),
                            "url": info_dict.get("webpage_url"),
                            "image": info_dict.get("thumbnail"),
                            "download": {
                                "url": download_url,
                                "num": None
                            },
                            "format_note": info_dict.get("format_note"),
                        })
        except Exception as message_error:
            fail_message = (
                (str(message_error))
                .replace("ERROR: ", "")
                .replace("\033[0;31mERROR:\033[0m ", "")
                .replace(f"{video_url}: ", "")
                .replace("[youtube] ", "")
                .replace("[BiliBili] ", "")
            )
            if video_url[:2] == "BV":
                fail_message = fail_message.replace(f"{video_url[2:]}: ", "")
        return fail_message, infos
    error_reason = {
        r"Premieres in ": ["\033[31m预播\033[0m|", "text"],
        r"This live event will begin in ": ["\033[31m直播预约\033[0m|", "text"],
        r"Video unavailable. This video contains content from SME, who has blocked it in your country on copyright grounds": ["\033[31m版权保护\033[0m", "text"],
        r"Premiere will begin shortly": ["\033[31m马上开始首映\033[0m", "text"],
        r"Private video. Sign in if you've been granted access to this video": ["\033[31m私享视频\033[0m", "text"],
        r"This video is available to this channel's members on level: .*? Join this channel to get access to members-only content and other exclusive perks\.": ["\033[31m会员专享\033[0m", "regexp"],
        r"Join this channel to get access to members-only content like this video, and other exclusive perks.": ["\033[31m会员视频\033[0m", "text"],
        r"Video unavailable. This video has been removed by the uploader": ["\033[31m视频被删除\033[0m", "text"],
        r"Video unavailable. This video is no longer available because the YouTube account associated with this video has been terminated.": ["\033[31m关联频道被终止\033[0m", "text"],
        r"Video unavailable": ["\033[31m视频不可用\033[0m", "text"],
        r"This video has been removed by the uploader": ["\033[31m发布者删除\033[0m", "text"],
        r"This video has been removed for violating YouTube's policy on harassment and bullying": ["\033[31m违规视频\033[0m", "text"],
        r"This video is private. If the owner of this video has granted you access, please sign in.": ["\033[31m私人视频\033[0m", "text"],
        r"This video is unavailable": ["\033[31m无法观看\033[0m", "text"],
        r"The following content is not available on this app.. Watch on the latest version of YouTube.": ["\033[31m需App\033[0m", "text"],
        r"This video may be deleted or geo-restricted. You might want to try a VPN or a proxy server (with --proxy)": ["\033[31m删除或受限\033[0m", "text"],
        r"Sign in to confirm your age. This video may be inappropriate for some users. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies": ["\033[31m年龄限制\033[0m", "text"],
        r"Sign in to confirm your age. This video may be inappropriate for some users.": ["\033[31m年龄限制\033[0m", "text"],
        r"Failed to extract play info; please report this issue on  https://github.com/yt-dlp/yt-dlp/issues?q= , filling out the appropriate issue template. Confirm you are on the latest version using  yt-dlp -U": ["\033[31mInfo失败\033[0m", "text"],
        r"This is a supporter-only video: 该视频为「专属视频」专属视频，开通「[0-9]+元档包月充电」即可观看\. Use --cookies-from-browser or --cookies for the authentication\. See  https://github\.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies": ["\033[31m充电专属\033[0m", "regexp"],
        r"'.+' does not look like a Netscape format cookies file": ["\033[31mCookie错误\033[0m", "regexp"],
    }
    def fail_message_initialize(fail_message, error_reason):
        for key, value in error_reason.items():
            if value[1] == "text":
                if key in fail_message:
                    return [key, value[0], value[1]]
            else:
                if re.search(key, fail_message):
                    return [key, value[0], value[1]]
    video_id_count, change_error, fail_message, infos = 0, None, "", []
    while (
        video_id_count < 3
        and change_error is None
        and (fail_message is not None or infos == [])
    ):
        video_id_count += 1
        fail_message, infos = duration_and_formats(video_website, video_url)
        if fail_message:
            change_error = fail_message_initialize(fail_message, error_reason)
    if change_error:
        if change_error[2] == "text":
            fail_message = fail_message.replace(f"{change_error[0]}", change_error[1])
        else:
            fail_message = re.sub(rf"{change_error[0]}", change_error[1], fail_message)
    if fail_message is None:
        lists = []
        for entry in infos:
            duration = entry["duration"]
            formats = entry["formats"]
            if duration == "" or duration is None:
                return "无法获取时长"
            if formats == "" or formats is None:
                return "无法获取格式"
            duration_and_id = []
            duration_and_id.append(duration)
            # 定义条件判断函数
            def check_resolution(item):
                if "aspect_ratio" in item and (
                    isinstance(item["aspect_ratio"], (float, int))
                ):
                    if item["aspect_ratio"] >= 1:
                        return item["height"] <= int(quality)
                    else:
                        return item["width"] <= int(quality)
                else:
                    return False
            def check_ext(item, media):
                return item["ext"] == media if "ext" in item else False
            def check_vcodec(item):
                if "vcodec" in item:
                    return (
                        "vp" not in item["vcodec"].lower()
                        and "av01" not in item["vcodec"].lower()
                        and "hev1" not in item["vcodec"].lower()
                    )
                else:
                    return False
            # 获取最好质量媒体的id
            def best_format_id(formats):
                tbr_max = 0.0
                format_id_best = ""
                vcodec_best = ""
                for format in formats:
                    if (
                        "tbr" in format
                        and "drc" not in format["format_id"]
                        and format["protocol"] == "https"
                        and (isinstance(format["tbr"], (float, int)))
                        and format["tbr"] >= tbr_max
                    ):
                        tbr_max = format["tbr"]
                        format_id_best = format["format_id"]
                        vcodec_best = format["vcodec"]
                return format_id_best, vcodec_best
            # 进行筛选
            formats_m4a = list(
                filter(lambda item: check_ext(item, "m4a") and check_vcodec(item), formats)
            )
            (best_formats_m4a, vcodec_best) = best_format_id(formats_m4a)
            if best_formats_m4a == "" or best_formats_m4a is None:
                if entry["format_note"] == "试看":
                    return "\033[31m试看\033[0m"
                else:
                    return "无法获取音频ID"
            duration_and_id.append(best_formats_m4a)
            if media == "mp4":
                formats_mp4 = list(
                    filter(
                        lambda item: check_resolution(item)
                        and check_ext(item, "mp4")
                        and check_vcodec(item),
                        formats,
                    )
                )
                (best_formats_mp4, vcodec_best) = best_format_id(formats_mp4)
                if best_formats_mp4 == "" or best_formats_mp4 is None:
                    if entry["format_note"] == "试看":
                        return "\033[31m试看\033[0m"
                    else:
                        return "无法获取视频ID"
                duration_and_id.append(best_formats_mp4)
                duration_and_id.append(vcodec_best)
            lists.append({
                "duration_and_id": duration_and_id,
                "title": entry.get("title"),
                "timestamp": entry.get("timestamp"),
                "id": entry.get("id"),
                "description": entry.get("description"),
                "url": entry.get("url"),
                "image": entry.get("image"),
                "download": entry.get("download"),
            })
        return lists
    else:
        return fail_message

# 获取已下载视频时长模块
def get_duration_ffmpeg(file_path):
    try:
        # 调用ffmpeg获取视频文件的时长信息
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        return math.ceil(duration)
    except ffmpeg.Error as e:
        error_note = e.stderr.decode('utf-8').splitlines()[-1]
        write_log(f"\033[31mError:\033[0m {error_note}")

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
                msg
                .replace("ERROR: ", "")
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
            f"{video_write_log} \033[31m下载失败\033[0m", None, True, True, (f"错误信息: {str(download_video_error)}")
            .replace("ERROR: ", "")
            .replace("\033[0;31mERROR:\033[0m ", "")
            .replace(f"{video_url}: ", "")
            .replace("[youtube] ", "")
            .replace("[download] ", "")
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
    duration_video = get_duration_ffmpeg(
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
    display_color="\033[95m"
):
    if output_dir_name:
        video_write_log = f"{display_color}{output_dir_name}\033[0m|{video_url}"
    else:
        video_write_log = video_url
    id_duration = video_format[0]
    if cookies:
        print_message = "\033[34m开始下载\033[0m 🍪"
    else:
        print_message = "\033[34m开始下载\033[0m"
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
                f"{datetime.now().strftime('%H:%M:%S')}|\033[34m开始合成...\033[0m", end=""
            )
            # 指定视频文件和音频文件的路径
            video_file = f"channel_audiovisual/{output_dir}/{video_url}.part.mp4"
            audio_file = f"channel_audiovisual/{output_dir}/{video_url}.part.m4a"
            output_file = f"channel_audiovisual/{output_dir}/{video_url}.mp4"
            try:
                # 使用 ffmpeg-python 合并视频和音频
                video = ffmpeg.input(video_file)
                audio = ffmpeg.input(audio_file)
                stream = ffmpeg.output(audio, video, output_file, vcodec='copy', acodec='copy')
                ffmpeg.run(stream)
                print(" \033[32m合成成功\033[0m")
                # 删除临时文件
                os.remove(f"channel_audiovisual/{output_dir}/{video_url}.part.mp4")
                os.remove(f"channel_audiovisual/{output_dir}/{video_url}.part.m4a")
            except ffmpeg.Error as dl_aideo_video_error:
                video_id_failed = video_url
                write_log(f"\n{video_write_log} \033[31m下载失败\033[0m\n错误信息: 合成失败:{dl_aideo_video_error}")
    if video_id_failed is None:
        if output_format == "m4a":
            only_log = f" {video_format[1]}"
        else:
            only_log = f" {video_format[1]}+{video_format[2]}"
        if cookies:
            only_log += " Cookies"
        write_log(f"{video_write_log} \033[32m下载成功\033[0m", None, True, True, only_log)  # 写入下载成功的日志信息
    return video_id_failed
