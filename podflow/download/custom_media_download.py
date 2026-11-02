# podflow/download/custom_media_download.py
# coding: utf-8

import os

from podflow import gVar
from podflow.basic.write_log import write_log
from podflow.basic.folder_build import folder_build
from podflow.download.delete_part import delete_part
from podflow.httpfs.app_bottle import bottle_app_instance
from podflow.httpfs.progress_bar import progress_update
from podflow.download.dl_aideo_video import dl_aideo_video
from podflow.basic.custom_media_file import get_custom_media
from podflow.basic.custom_media_file import update_custom_media
from podflow.message.custom_media_format import  custom_media_cookies


# 按链接更新自定义媒体条目的状态
# 写入期间置忙碌标记, 网页在忙碌期间禁用所有操作按钮, 减少并发修改
# 仍采用"读取-校验版本号-修改-写入"的方式, 与网页并发修改冲突时重试
def update_media_status(media_url, status, error=None):
    def modify(media_list):
        for media_item in media_list:
            if media_item.get("url") == media_url:
                media_item["status"] = status
                if error is None:
                    media_item.pop("error", None)
                else:
                    media_item["error"] = error
        return media_list

    gVar.custom_media_busy = True  # 置忙碌标记, 网页据此禁用所有操作按钮
    try:
        for _ in range(3):
            if update_custom_media(modify) is not None:
                return
        # 多次冲突时放弃写入, 保留条目原状态, 待下次下载流程重试
        write_log(
            f"custom_media {media_url} \033[33m状态更新失败(列表已被其他进程修改)\033[0m"
        )
    finally:
        # 恢复调用前的忙碌状态(被主流程置为忙碌时不提前解除)
        gVar.custom_media_busy = False


# 下载自定义媒体模块
def custom_media_download():
    # 自定义媒体下载时的显示颜色(青色, 与频道下载的品红区分)
    custom_media_display_color = "\033[36m"
    # 自定义媒体的存放文件夹(channel_audiovisual下的custom_media文件夹)
    custom_media_output_dir = "custom_media"
    # 自定义媒体统一存放在custom_media文件夹中
    folder_build(custom_media_output_dir, "channel_audiovisual")
    # 按配置删除中断下载的媒体文件
    if gVar.config["delete_incompletement"]:
        delete_part({})
    # 暂停进程打印
    gVar.server_process_print_flag[0] = "pause"
    # 先整理下载计划: 无需下载的媒体直接处理状态, 需下载的按媒体分组待执行
    plan = []
    pre_failed_urls = set()
    for media in get_custom_media():
        # 仅下载状态为准备中且已获取到格式信息的条目, 失败条目由网页重新提交覆盖
        if media.get("status") != "preparing" or not media.get("lists"):
            continue
        media_url = media.get("url", "")
        video_id = media.get("id", "")
        # 旧条目的type可能为audio/video, 归一成新取值(m4a/mp4)后再用于下载
        output_format = media.get("type")
        if output_format not in ("m4a", "mp4"):
            continue
        title = media.get("title") or video_id
        display_name = f"{custom_media_display_color}{title}\033[0m"
        # 媒体文件已存在时不再重新下载, 直接完成
        if all(
            os.path.exists(
                f"channel_audiovisual/{custom_media_output_dir}/"
                f"{entry.get('id') or video_id}.{output_format}"
            )
            for entry in media["lists"]
        ):
            update_media_status(media_url, "completed")
            continue
        # 按平台选择cookie文件, 失败原因为None表示可以继续下载
        cookies, fail_reason = custom_media_cookies(media_url)
        if fail_reason is not None:
            update_media_status(media_url, "failed", fail_reason)
            write_log(f"{display_name}|{video_id} \033[31m{fail_reason}\033[0m")
            continue
        entries = []
        for entry in media["lists"]:
            entry_id = entry.get("id") or video_id
            # 格式信息缺失时无法定位下载流, 该媒体直接按失败处理
            if not entry.get("duration_and_id"):
                update_media_status(media_url, "failed", "无法获取媒体信息")
                pre_failed_urls.add(media_url)
                break
            # 分集文件已存在时不再重新下载
            if os.path.exists(
                f"channel_audiovisual/{custom_media_output_dir}/{entry_id}.{output_format}"
            ):
                continue
            entries.append(entry)
        if entries:
            plan.append(
                {
                    "media_url": media_url,
                    "video_id": video_id,
                    "title": title,
                    "display_name": display_name,
                    "output_format": output_format,
                    "cookies": cookies,
                    "entries": entries,
                }
            )
    # 按下载单元(含分P)平均分配主进度条的100%, 并开启自定义媒体下载的进度开关
    total = sum(len(item["entries"]) for item in plan)
    if total:
        # 有下载任务时才启用总进度条: 开始时归零并置为准备中
        progress_update(0, refresh=1)
        gVar.custom_media_progress = {
            "share": 1 / total,
            "subs_total": 1,
            "subs_done": 0,
            "last_per": 0.0,
            "unit_credited": 0.0,
        }
    else:
        gVar.custom_media_progress = None
    try:
        for item in plan:
            download_failed = None
            for entry in item["entries"]:
                download_info = entry.get("download") or {}
                if dl_aideo_video(
                    entry.get("id") or item["video_id"],
                    custom_media_output_dir,
                    item["output_format"],
                    entry["duration_and_id"],
                    gVar.config["retry_count"],
                    download_info.get("url") or item["media_url"],
                    "自定义媒体",
                    item["cookies"],
                    download_info.get("num"),
                    custom_media_display_color,
                    entry.get("title") or item["title"],
                ):
                    download_failed = "下载失败"
                    break
            # 格式信息缺失的媒体已在计划阶段标记失败, 不再覆盖其状态
            if item["media_url"] in pre_failed_urls:
                continue
            if download_failed:
                update_media_status(item["media_url"], "failed", download_failed)
                write_log(
                    f"{item['display_name']}|{item['video_id']} \033[31m无法下载\033[0m"
                )
            else:
                update_media_status(item["media_url"], "completed")
    finally:
        # 关闭自定义媒体下载的进度开关, 恢复常规下载行为
        gVar.custom_media_progress = None
    # 有下载任务时才标记总进度条完成
    if total:
        progress_update(1, refresh=3)
    # 恢复进程打印
    bottle_app_instance.cherry_print()
