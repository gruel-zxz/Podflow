# podflow/download_and_build.py
# coding: utf-8

import threading
from podflow import gVar
from podflow.upload.upload_files import all_upload
from podflow.youtube.build import get_youtube_introduction
from podflow.message.create_main_rss import create_main_rss
from podflow.download.youtube_and_bilibili_download import youtube_and_bilibili_download


def get_and_duild():
    get_youtube_introduction()
    create_main_rss()
    gVar.upload_stop = True  # 停止上传线程


# 下载并构建YouTube和哔哩哔哩视频模块
def download_and_build(upload_url):
    thread_download = threading.Thread(target=youtube_and_bilibili_download)
    thread_build = threading.Thread(target=get_and_duild)
    if upload_url:
        thread_upload = threading.Thread(
            target=all_upload,
            args=(upload_url,)
        )

    thread_download.start()
    thread_build.start()
    if upload_url:
        thread_upload.start()

    thread_download.join()
    thread_build.join()
    if upload_url:
        thread_upload.join()
