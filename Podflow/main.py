# Podflow/main.py
# coding: utf-8

from datetime import datetime
from importlib.metadata import version
from Podflow.main_podcast import main_podcast
from Podflow.parse_arguments import parse_arguments


def main():
    # 获取传入的参数
    parse_arguments()
    # 开始运行
    print(
        f"{datetime.now().strftime('%H:%M:%S')}|Podflow|{version('Podflow')}开始运行....."
    )
    main_podcast()


if __name__ == "__main__":
    main()
