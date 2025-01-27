# Podflow/ffmpeg_judge.py
# coding: utf-8

import sys
import subprocess
import shutil
from Podflow.basic.write_log import write_log


def error_ffmpeg_judge(ffmpeg_worry):
    write_log("FFmpeg 未安装, 请安装后重试")
    print(ffmpeg_worry)
    sys.exit(0)


def ffmpeg_judge():
    ffmpeg_worry = """\033[0mFFmpeg安装方法:
    Ubuntu:
    \033[32msudo apt update
    sudo apt install ffmpeg\033[0m
    CentOS:
    \033[32msudo yum update
    sudo yum install ffmpeg\033[0m
    Debian:
    \033[32msudo apt-get update
    sudo apt-get install ffmpeg\033[0m
    Arch Linux、Fedora:
    \033[32msudo pacman -S ffmpeg
    sudo dnf install ffmpeg\033[0m
    检查FFmpeg版本:
    \033[32mffmpeg -version\033[0m"""

    # 使用 shutil.which 检查 ffmpeg 是否安装
    if shutil.which("ffmpeg") is None:
        error_ffmpeg_judge(ffmpeg_worry)

    try:
        # 执行 ffmpeg 命令获取版本信息
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        output = result.stdout.lower()
        # 检查输出中是否包含 ffmpeg 版本信息
        if "ffmpeg version" not in output:
            error_ffmpeg_judge(ffmpeg_worry)
    except FileNotFoundError:
        error_ffmpeg_judge(ffmpeg_worry)
