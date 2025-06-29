# podflow/run_and_upload.py
# coding: utf-8

import threading
from podflow import gVar
from podflow.upload.upload_files import all_upload
from podflow.config.channge_icon import channge_icon
from podflow.download.delete_part import delete_part
from podflow.httpfs.progress_bar import progress_update
from podflow.download_and_build import download_and_build
from podflow.httpfs.app_bottle import bottle_app_instance
from podflow.message.get_video_format import get_video_format
from podflow.message.optimize_download import optimize_download
from podflow.message.update_information_display import update_information_display
from podflow.message.update_youtube_bilibili_rss import update_youtube_bilibili_rss


def find_and_duild():
    # 更新Youtube和哔哩哔哩频道xml
    update_youtube_bilibili_rss()
    progress_update(0.1)
    # 判断是否有更新内容
    if gVar.channelid_youtube_ids_update or gVar.channelid_bilibili_ids_update:
        gVar.update_generate_rss = True
    if gVar.update_generate_rss:
        # 根据日出日落修改封面(只适用原封面)
        channge_icon()
        progress_update(0.11, num=0.0049)
        # 输出需要更新的信息
        update_information_display(
            gVar.channelid_youtube_ids_update,
            gVar.youtube_content_ytid_update,
            gVar.youtube_content_ytid_backward_update,
            "YouTube",
        )
        update_information_display(
            gVar.channelid_bilibili_ids_update,
            gVar.bilibili_content_bvid_update,
            gVar.bilibili_content_bvid_backward_update,
            "BiliBili",
        )
        progress_update(0.12)
        # 暂停进程打印
        gVar.server_process_print_flag[0] = "pause"
        # 获取视频格式信息
        get_video_format()
        progress_update(0.199)
        # 恢复进程打印
        bottle_app_instance.cherry_print()
        # 优化下载顺序
        optimize_download()
        # 删除中断下载的媒体文件
        if gVar.config["delete_incompletement"]:
            delete_part(gVar.channelid_youtube_ids | gVar.channelid_bilibili_ids)
        progress_update(0.20, refresh=2)
        # 暂停进程打印
        gVar.server_process_print_flag[0] = "pause"
        # 下载并构建YouTube和哔哩哔哩视频
        download_and_build()
        progress_update(0.8)

# 运行并上传模块
def run_and_upload(upload_url):
    if upload_url:
        thread_find_and_duild = threading.Thread(target=find_and_duild)
        thread_upload = threading.Thread(
            target=all_upload,
            args=(upload_url,)
        )

        thread_find_and_duild.start()
        thread_upload.start()

        thread_find_and_duild.join()
        thread_upload.join()
    else:
        find_and_duild()
