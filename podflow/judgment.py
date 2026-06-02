# podflow/judgment.py
# coding: utf-8

import sys
import subprocess
import shutil
from podflow.basic.write_log import write_log
from podflow.basic.time_print import time_print


def error_ffmpeg_judge(ffmpeg_worry):
    write_log("FFmpeg 未安装, 请安装后重试")
    time_print(ffmpeg_worry, Time=False)
    sys.exit(0)


def ffmpeg_judge():
    ffmpeg_worry = """\033[0mFFmpeg安装方法:
    Windows:
    \033[32mwinget install Gyan.FFmpeg\033[0m
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


def error_deno_judge(deno_worry):
    """Deno 未安装时的错误处理"""
    write_log("Deno 未安装, 请安装后重试")
    time_print(deno_worry, Time=False)
    sys.exit(0)


def deno_judge():
    """检查 Deno 是否安装（苹果设备自动跳过）"""
    # 考虑兼容性，如果系统是 macOS (darwin) 或 iOS (ios)，直接跳过检查
    if sys.platform in ["darwin", "ios"]:
        return

    deno_worry = """\033[0mDeno安装方法:
    Windows:
    \033[32mwinget install DenoLand.Deno\033[0m
    Linux (Ubuntu/Debian/CentOS等):
    \033[32mcurl -fsSL https://deno.land/install.sh | sh\033[0m
    检查Deno版本:
    \033[32mdeno --version\033[0m"""

    # 使用 shutil.which 检查 deno 命令是否存在
    if shutil.which("deno") is None:
        error_deno_judge(deno_worry)

    try:
        # 执行 deno --version 获取版本信息
        result = subprocess.run(["deno", "--version"], capture_output=True, text=True, check=True)
        output = result.stdout.lower()
        # 检查输出中是否包含 deno 版本关键字
        if "deno" not in output:
            error_deno_judge(deno_worry)
    except (FileNotFoundError, subprocess.CalledProcessError):
        error_deno_judge(deno_worry)