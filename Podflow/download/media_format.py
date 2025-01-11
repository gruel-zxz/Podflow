# Podflow/download/media_format.py
# coding: utf-8

import re
import yt_dlp

error_reason = {
    r"Premieres in ": ["\033[31m预播\033[0m|", "text"],
    r"This live event will begin in ": ["\033[31m直播预约\033[0m|", "text"],
    r"Video unavailable. This video contains content from SME, who has blocked it in your country on copyright grounds": [
        "\033[31m版权保护\033[0m",
        "text",
    ],
    r"Premiere will begin shortly": ["\033[31m马上开始首映\033[0m", "text"],
    r"Private video. Sign in if you've been granted access to this video": [
        "\033[31m私享视频\033[0m",
        "text",
    ],
    r"This video is available to this channel's members on level: .*? Join this channel to get access to members-only content and other exclusive perks\.": [
        "\033[31m会员专享\033[0m",
        "regexp",
    ],
    r"Join this channel to get access to members-only content like this video, and other exclusive perks.": [
        "\033[31m会员视频\033[0m",
        "text",
    ],
    r"Video unavailable. This video has been removed by the uploader": [
        "\033[31m视频被删除\033[0m",
        "text",
    ],
    r"Video unavailable. This video is no longer available because the YouTube account associated with this video has been terminated.": [
        "\033[31m关联频道被终止\033[0m",
        "text",
    ],
    r"Video unavailable": ["\033[31m视频不可用\033[0m", "text"],
    r"This video has been removed by the uploader": [
        "\033[31m发布者删除\033[0m",
        "text",
    ],
    r"This video has been removed for violating YouTube's policy on harassment and bullying": [
        "\033[31m违规视频\033[0m",
        "text",
    ],
    r"This video is private. If the owner of this video has granted you access, please sign in.": [
        "\033[31m私人视频\033[0m",
        "text",
    ],
    r"This video is unavailable": ["\033[31m无法观看\033[0m", "text"],
    r"The following content is not available on this app.. Watch on the latest version of YouTube.": [
        "\033[31m需App\033[0m",
        "text",
    ],
    r"This video may be deleted or geo-restricted. You might want to try a VPN or a proxy server (with --proxy)": [
        "\033[31m删除或受限\033[0m",
        "text",
    ],
    r"Sign in to confirm your age. This video may be inappropriate for some users. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies": [
        "\033[31m年龄限制\033[0m",
        "text",
    ],
    r"Sign in to confirm your age. This video may be inappropriate for some users.": [
        "\033[31m年龄限制\033[0m",
        "text",
    ],
    r"Failed to extract play info; please report this issue on  https://github.com/yt-dlp/yt-dlp/issues?q= , filling out the appropriate issue template. Confirm you are on the latest version using  yt-dlp -U": [
        "\033[31mInfo失败\033[0m",
        "text",
    ],
    r"This is a supporter-only video: 该视频为「专属视频」专属视频，开通「[0-9]+元档包月充电」即可观看\. Use --cookies-from-browser or --cookies for the authentication\. See  https://github\.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies": [
        "\033[31m充电专属\033[0m",
        "regexp",
    ],
    r"'.+' does not look like a Netscape format cookies file": [
        "\033[31mCookie错误\033[0m",
        "regexp",
    ],
}


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
            ydl_opts["http_headers"] = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com/",
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


def fail_message_initialize(fail_message, error_reason):
    for key, value in error_reason.items():
        if (
            value[1] == "text"
            and key in fail_message
            or value[1] != "text"
            and re.search(key, fail_message)
        ):
            return [key, value[0], value[1]]


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
        if fail_message:
            change_error = fail_message_initialize(fail_message, error_reason)
    if change_error:
        if change_error[2] == "text":
            fail_message = fail_message.replace(f"{change_error[0]}", change_error[1])
        else:
            fail_message = re.sub(rf"{change_error[0]}", change_error[1], fail_message)
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
