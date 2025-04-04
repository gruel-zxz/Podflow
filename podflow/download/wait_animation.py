# podflow/download/wait_animation.py
# coding: utf-8

import time
from datetime import datetime
from podflow.basic.time_print import time_print


# 等待动画模块
def wait_animation(stop_flag, wait_animation_display_info):
    animation = "."
    i = 1
    prepare_youtube_print = datetime.now().strftime("%H:%M:%S")
    while True:
        if stop_flag[0] == "keep":
            time_print(
                f"{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation.ljust(5)}\033[0m",
                Top=True,
                NoEnter=True,
                Time=False,
            )
            if i % 5 == 0:
                animation = "."
            else:
                animation += "."
            i += 1
            time.sleep(0.5)
        elif stop_flag[0] == "error":
            time_print(
                f"{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation}\033[0m \033[31m失败:\033[0m",
                Top=True,
                Time=False,
            )
            break
        elif stop_flag[0] == "end":
            time_print(
                f"{prepare_youtube_print}|{wait_animation_display_info}\033[34m准备中{animation} 已完成\033[0m",
                Top=True,
                Time=False,
            )
            break
