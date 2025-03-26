# coding: utf-8

from importlib.metadata import version
from podflow import parse
from podflow.main_upload import main_upload
from podflow.main_podcast import main_podcast
from podflow.basic.time_print import time_print
from podflow.repair.reverse_log import reverse_log
from podflow.parse_arguments import parse_arguments


def main():
    # 获取传入的参数
    parse_arguments()
    # 开始运行
    if parse.upload:
        time_print("Podflow|接收服务开始运行...")
        reverse_log("upload")
        main_upload()
    else:
        time_print(f"Podflow|{version('Podflow')} 开始运行...")
        reverse_log("Podflow")
        reverse_log("httpfs")
        main_podcast()


if __name__ == "__main__":
    main()
