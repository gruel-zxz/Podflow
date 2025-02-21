# Podflow/message/fail_message_initialize.py
# coding: utf-8

import re

error_reason = [
    [
        r"Premieres in ",
        "\033[31m预播\033[0m|",
        "text",
    ],
    [
        r"This live event will begin in ",
        "\033[31m直播预约\033[0m|",
        "text",
    ],
    [
        r"Video unavailable. This video contains content from SME, who has blocked it in your country on copyright grounds",
        "\033[31m版权保护\033[0m",
        "text",
    ],
    [
        r"Premiere will begin shortly",
        "\033[31m马上开始首映\033[0m",
        "text",
    ],
    [
        r"Private video. Sign in if you've been granted access to this video",
        "\033[31m私享视频\033[0m",
        "text",
    ],
    [
        r"This video is available to this channel's members on level: .*? Join this channel to get access to members-only content and other exclusive perks\.",
        "\033[31m会员专享\033[0m",
        "regexp",
    ],
    [
        r"Join this channel to get access to members-only content like this video, and other exclusive perks.",
        "\033[31m会员视频\033[0m",
        "text",
    ],
    [
        r"Video unavailable. This video has been removed by the uploader",
        "\033[31m视频被删除\033[0m",
        "text",
    ],
    [
        r"Video unavailable. This video is no longer available because the YouTube account associated with this video has been terminated.",
        "\033[31m关联频道被终止\033[0m",
        "text",
    ],
    [
        r"Video unavailable",
        "\033[31m视频不可用\033[0m",
        "text",
    ],
    [
        r"This video has been removed by the uploader",
        "\033[31m发布者删除\033[0m",
        "text",
    ],
    [
        r"This video has been removed for violating YouTube's policy on harassment and bullying",
        "\033[31m违规视频\033[0m",
        "text",
    ],
    [
        r"This video is private. If the owner of this video has granted you access, please sign in.",
        "\033[31m私人视频\033[0m",
        "text",
    ],
    [
        r"This video is unavailable",
        "\033[31m无法观看\033[0m",
        "text",
    ],
    [
        r"The following content is not available on this app.. Watch on the latest version of YouTube.",
        "\033[31m需App\033[0m",
        "text",
    ],
    [
        r"This video may be deleted or geo-restricted. You might want to try a VPN or a proxy server (with --proxy)",
        "\033[31m删除或受限\033[0m",
        "text",
    ],
    [
        r"Sign in to confirm your age. This video may be inappropriate for some users. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies",
        "\033[31m年龄限制\033[0m",
        "text",
    ],
    [
        r"Sign in to confirm your age. This video may be inappropriate for some users.",
        "\033[31m年龄限制\033[0m",
        "text",
    ],
    [
        r"Failed to extract play info; please report this issue on  https://github.com/yt-dlp/yt-dlp/issues?q= , filling out the appropriate issue template. Confirm you are on the latest version using  yt-dlp -U",
        "\033[31mInfo失败\033[0m",
        "text",
    ],
    [
        r"This is a supporter-only video: 该视频为「专属视频」专属视频，开通「[0-9]+元档包月充电」即可观看\. Use --cookies-from-browser or --cookies for the authentication\. See  https://github\.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies",
        "\033[31m充电专属\033[0m",
        "regexp",
    ],
    [
        r"'.+' does not look like a Netscape format cookies file",
        "\033[31mCookie错误\033[0m",
        "regexp",
    ],
    [
        r"Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies",
        "\033[31m需登录\033[0m",
        "text",
    ],
    [
        r"unable to download video data: HTTP Error 403: Forbidden",
        "\033[31m请求拒绝\033[0m",
        "text",
    ],
    [
        r"Got error: [0-9]* bytes read, [0-9]* more expected",
        "\033[31m数据不完整\033[0m",
        "regexp",
    ],
    [
        r"Got error: EOF occurred in violation of protocol (_ssl.c:992)",
        "\033[31m传输中断\033[0m",
        "text",
    ],
    [
        r"Got error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))",
        "\033[31m请求超时\033[0m",
        "text",
    ],
    [
        r"Got error: HTTPSConnectionPool\(host='rr[0-9]---sn-.{8}\.googlevideo.com', port=443\): Read timed out\. \(read timeout=20\.0\)",
        "\033[31m响应超时\033[0m",
        "regexp",
    ],
    [
        r"Requested format is not available. Use --list-formats for a list of available formats",
        "\033[31m格式不可用\033[0m",
        "text",
    ],
]


# 失败信息初始化模块
def fail_message_initialize(message_error, video_url):
    if video_url[:2] == "BV":
        video_url = video_url[:12]
    fail_message = (
        str(message_error)
        .replace("ERROR: ", "")
        .replace("\033[0;31mERROR:\033[0m ", "")
        .replace(f"{video_url}: ", "")
        .replace("[youtube] ", "")
        .replace("[download] ", "")
        .replace("[BiliBili] ", "")
    )
    if video_url[:2] == "BV":
        fail_message = fail_message.replace(f"{video_url[2:]}: ", "")
    for fail_info, field, mode in error_reason:
        if mode == "text" and fail_info in fail_message:
            fail_message = fail_message.replace(f"{fail_info}", field)
            break
        elif mode == "regexp" and re.search(fail_info, fail_message):
            fail_message = re.sub(rf"{fail_info}", field, fail_message)
            break
    return fail_message
