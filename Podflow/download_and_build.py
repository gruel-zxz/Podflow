# podflow/download_and_build.py
# coding: utf-8

import threading
from podflow.youtube.build import get_youtube_introduction
from podflow.message.create_main_rss import create_main_rss
from podflow.download.youtube_and_bilibili_download import youtube_and_bilibili_download


def get_and_duild():
    get_youtube_introduction()
    create_main_rss()


# 下载并构建YouTube和哔哩哔哩视频模块
def download_and_build():
    thread_download = threading.Thread(target=youtube_and_bilibili_download)
    thread_build = threading.Thread(target=get_and_duild)

    thread_download.start()
    thread_build.start()

    thread_download.join()
    thread_build.join()
