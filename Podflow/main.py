# coding: utf-8

import signal
import sys
from datetime import datetime
from importlib.metadata import version
from Podflow.main_podcast import main_podcast
from Podflow.parse_arguments import parse_arguments


def signal_handler(sig, frame):
    print(f"\r{datetime.now().strftime('%H:%M:%S')}|Podflow被中断, 正在退出...")
    sys.exit(0)


def main():
    # 注册SIGINT信号处理器（Ctrl+C）
    signal.signal(signal.SIGINT, signal_handler)

    # 获取传入的参数
    parse_arguments()
    # 开始运行
    print(
        f"{datetime.now().strftime('%H:%M:%S')}|Podflow|{version('Podflow')}开始运行....."
    )
    main_podcast()


if __name__ == "__main__":
    main()
