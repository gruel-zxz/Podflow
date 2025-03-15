# coding: utf-8

from importlib.metadata import version
from Podflow import parse
from Podflow.main_upload import main_upload
from Podflow.main_podcast import main_podcast
from Podflow.basic.time_print import time_print
from Podflow.repair.reverse_log import reverse_log
from Podflow.parse_arguments import parse_arguments


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
