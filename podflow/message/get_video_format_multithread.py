# podflow/message/get_video_format_multithread.py
# coding: utf-8

import threading
from podflow.download.wait_animation import wait_animation
from podflow.message.get_youtube_and_bilibili_video_format import (
    get_youtube_and_bilibili_video_format,
)


# YouTube&哔哩哔哩获取视频信息多线程模块
def get_video_format_multithread(
    video_id_update_format_item,
    wait_animation_display_info,
    ratio_part,
):
    # 创建共享的标志变量
    stop_flag = ["keep"]  # 使用列表来存储标志变量
    # 创建两个线程分别运行等待动画和其他代码, 并传递共享的标志变量
    prepare_animation = threading.Thread(
        target=wait_animation,
        args=(
            stop_flag,
            wait_animation_display_info,
        ),
    )
    # 启动动画线程
    prepare_animation.start()
    # 创建线程锁
    video_format_lock = threading.Lock()
    ratio_part_lock = threading.Lock()
    # 创建线程列表
    video_id_update_threads = []
    
    for video_id in video_id_update_format_item.keys():
        thread = threading.Thread(
            target=get_youtube_and_bilibili_video_format,
            args=(
                video_id,
                stop_flag,
                video_format_lock,
                prepare_animation,
                ratio_part,
                ratio_part_lock,
                ),
        )
        video_id_update_threads.append(thread)
        thread.start()
    # 等待所有线程完成
    for thread in video_id_update_threads:
        thread.join()
    stop_flag[0] = "end"
    prepare_animation.join()
