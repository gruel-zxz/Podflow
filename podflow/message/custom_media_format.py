# podflow/message/custom_media_format.py
# coding: utf-8

import re

from podflow import gVar
from podflow.bilibili.get import get_bilibili_cid
from podflow.message.media_format import media_format

# 失败信息里混有ANSI颜色码, 存入列表文件前需清除
custom_media_ansi_pattern = re.compile(r"\033\[\d+m")
# 由链接本身决定、不被 media_format 抓取结果覆盖的字段
# url 参与查重, type/quality/audio_track_language/status 决定网页展示, id 用于后续下载定位
custom_media_own_field = (
    "url",
    "type",
    "quality",
    "audio_track_language",
    "status",
    "id",
)


# 按平台选择cookie文件, 返回(文件路径, 失败原因)
# 文件路径为空表示无需cookie, 失败原因为None表示可以继续抓取
def custom_media_cookies(media_url):
    if "youtube" in media_url:
        # YouTube公开视频无需cookie也能获取, cookie开关打开时才带上
        if gVar.youtube_cookie_switch and gVar.youtube_cookie:
            return "channel_data/yt_dlp_youtube.txt", None
    if "bilibili" in media_url:
        # 哔哩哔哩的cookie文件由登录时的 bulid_netscape("yt_dlp_bilibili") 生成
        if gVar.bilibili_data:
            return "channel_data/yt_dlp_bilibili.txt", None
        return None, "需登录"
    return "", None


# 失败信息统一处理: 去除ANSI颜色码并限制长度, 便于存入列表文件及网页显示
def clean_fail_reason(fail_reason):
    return custom_media_ansi_pattern.sub("", str(fail_reason)).strip()[:200]


# 调用 media_format 抓取媒体信息, 返回(可写入条目的字段, 失败原因)
# 抓取成功时失败原因为None, 失败时字段为None, 由调用方把条目状态改写为 failed
# title=True 让 media_format 返回 {"title": 视频标题, "lists": 全部格式信息}, 整体写入条目
def get_custom_media_info(media_url, video_id, media_type, media_quality, language):
    cookies, fail_reason = custom_media_cookies(media_url)
    if fail_reason is not None:
        return None, fail_reason
    try:
        media_info = media_format(
            media_url,
            video_id,
            media=media_type,
            quality=media_quality,
            cookies=cookies,
            # 音频轨道语言取自网页下拉(候选数据源自config_desc的channel.youtube)
            language=language,
            need_title=True,
        )
    except Exception as error:
        # media_format 内部多处未做键值判空, 联网异常同样会抛出
        return None, clean_fail_reason(error) or type(error).__name__
    if isinstance(media_info, str):
        if "bilibili" in media_url:
            power = get_bilibili_cid(video_id, "")[2]
            if power is True and (
                "试看" in media_info
                or "提取器错误" in media_info
                or "服务器拒绝" in media_info
                or "删除或受限" in media_info
                or "无法提取" in media_info
                or "Cookie错误"in media_info
                or media_info == "无法获取音频ID"
            ):
                media_info = "充电专属"
        # media_format 返回字符串表示获取失败
        return None, clean_fail_reason(media_info)
    if not isinstance(media_info, dict) or not media_info.get("lists"):
        return None, "无法获取媒体信息"
    # {"title", "lists"} 原样并入条目, 再剔除本页维护的字段以防被覆盖
    media_fields = {
        key: value
        for key, value in media_info.items()
        if key not in custom_media_own_field
    }
    return media_fields, None
