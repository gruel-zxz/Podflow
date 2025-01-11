# Podflow/download/wait_animation.py
# coding: utf-8

import time
from datetime import datetime


# 等待动画模块
def wait_animation(stop_flag, wait_animation_display_info):
    animation = "."
    i = 1
    prepare_youtube_print = datetime.now().strftime("%H:%M:%S")
    while True:
        if stop_flag[0] == "keep":
            print(
                f"\r{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation.ljust(5)}\033[0m",
                end="",
            )
        elif stop_flag[0] == "error":
            print(
                f"\r{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation} \033[31m失败:\033[0m"
            )
            break
        elif stop_flag[0] == "end":
            print(
                f"\r{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation} 已完成\033[0m"
            )
            break
        if i % 5 == 0:
            animation = "."
        else:
            animation += "."
        i += 1
        time.sleep(0.5)
