# podflow/message/media_format.py
# coding: utf-8

import yt_dlp
from podflow.message.fail_message_initialize import fail_message_initialize


class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def info(self, msg):
        pass

    def error(self, msg):
        pass


def duration_and_formats(video_website, video_url, cookies):
    fail_message, infos = None, []
    try:
        # 初始化 yt_dlp 实例, 并忽略错误
        ydl_opts = {
            "no_warnings": True,
            "quiet": True,  # 禁止非错误信息的输出
            "logger": MyLogger(),
        }
        if cookies:
            if "www.bilibili.com" in video_website:
                ydl_opts["http_headers"] = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                    "Referer": "https://www.bilibili.com/",
                }
            elif "www.youtube.com" in video_website:
                ydl_opts["http_headers"] = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                    "Referer": "https://www.youtube.com/",
                }
            ydl_opts["cookiefile"] = cookies  # cookies 是你的 cookies 文件名
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 使用提供的 URL 提取视频信息
            if info_dict := ydl.extract_info(f"{video_website}", download=False):
                # 获取视频时长并返回
                entries = info_dict.get("entries", None)
                download_url = info_dict.get("original_url", None)
                if entries:
                    infos.extend(
                        {
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
                        }
                        for playlist_num, entry in enumerate(entries)
                    )
                else:
                    infos.append(
                        {
                            "title": info_dict.get("title"),
                            "duration": info_dict.get("duration"),
                            "formats": info_dict.get("formats"),
                            "timestamp": info_dict.get("timestamp"),
                            "id": info_dict.get("id"),
                            "description": info_dict.get("description"),
                            "url": info_dict.get("webpage_url"),
                            "image": info_dict.get("thumbnail"),
                            "download": {"url": download_url, "num": None},
                            "format_note": info_dict.get("format_note"),
                        }
                    )
    except Exception as message_error:
        fail_message = fail_message_initialize(message_error, video_url)
    return fail_message, infos


# 定义条件判断函数
def check_resolution(item, quality):
    if "aspect_ratio" in item and (isinstance(item["aspect_ratio"], (float, int))):
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
    for form in formats:
        if (
            "tbr" in form
            and "drc" not in form["format_id"]
            and form["protocol"] == "https"
            and (isinstance(form["tbr"], (float, int)))
            and form["tbr"] >= tbr_max
        ):
            tbr_max = form["tbr"]
            format_id_best = form["format_id"]
            vcodec_best = form["vcodec"]
    return format_id_best, vcodec_best


# 获取媒体时长和ID模块
def media_format(video_website, video_url, media="m4a", quality="480", cookies=None):
    fail_message = None
    video_id_count, change_error, fail_message, infos = 0, None, "", []
    while (
        video_id_count < 3
        and change_error is None
        and (fail_message is not None or not infos)
    ):
        video_id_count += 1
        fail_message, infos = duration_and_formats(video_website, video_url, cookies)
    if fail_message is not None:
        return fail_message
    lists = []
    for entry in infos:
        duration = entry["duration"]
        formats = entry["formats"]
        if duration == "" or duration is None:
            return "无法获取时长"
        if formats == "" or formats is None:
            return "无法获取格式"
        # 进行筛选
        formats_m4a = list(
            filter(lambda item: check_ext(item, "m4a") and check_vcodec(item), formats)
        )
        (best_formats_m4a, vcodec_best) = best_format_id(formats_m4a)
        if best_formats_m4a == "" or best_formats_m4a is None:
            return (
                "\033[31m试看\033[0m"
                if entry["format_note"] == "试看"
                else "无法获取音频ID"
            )
        duration_and_id = [duration, best_formats_m4a]
        if media == "mp4":
            formats_mp4 = list(
                filter(
                    lambda item: check_resolution(item, quality)
                    and check_ext(item, "mp4")
                    and check_vcodec(item),
                    formats,
                )
            )
            (best_formats_mp4, vcodec_best) = best_format_id(formats_mp4)
            if best_formats_mp4 == "" or best_formats_mp4 is None:
                return (
                    "\033[31m试看\033[0m"
                    if entry["format_note"] == "试看"
                    else "无法获取视频ID"
                )
            duration_and_id.extend((best_formats_mp4, vcodec_best))
        lists.append(
            {
                "duration_and_id": duration_and_id,
                "title": entry.get("title"),
                "timestamp": entry.get("timestamp"),
                "id": entry.get("id"),
                "description": entry.get("description"),
                "url": entry.get("url"),
                "image": entry.get("image"),
                "download": entry.get("download"),
            }
        )
    return lists
