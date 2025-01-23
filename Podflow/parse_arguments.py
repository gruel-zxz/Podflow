# Podflow/parse_arguments.py
# coding: utf-8

import argparse
from Podflow import parse


def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
    return ivalue


# 获取命令行参数并判断
def parse_arguments():
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(
        description="you can try: Podflow -n 24 -d 3600"
    )
    # 参数
    parser.add_argument(
        "-n",
        "--times",
        nargs=1,
        type=positive_int,
        metavar="NUM",
        help="number of times",
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=positive_int,
        default=1500,
        metavar="NUM",
        help="delay in seconds(default: 1500)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config.json",
        metavar="FILE_PATH",
        help="path to the config.json file",
    )
    parser.add_argument(
        "-p",
        "--period",
        type=positive_int,
        metavar="NUM",
        default=1,
        help="Specify the update frequency (unit: times/day), default value is 1",
    )
    parser.add_argument(
        "--shortcuts",
        nargs="*",
        type=str,
        metavar="URL",
        help="only shortcuts can be work",
    )
    parser.add_argument("--file", nargs="?", help=argparse.SUPPRESS)  # 仅运行在ipynb中
    parser.add_argument("--httpfs", action="store_true", help=argparse.SUPPRESS)
    # 解析参数
    args = parser.parse_args()
    parse.time_delay = args.delay
    parse.config = args.config
    parse.period = args.period
    parse.file = args.file
    parse.httpfs = args.httpfs
    # 检查并处理参数的状态
    if args.times is not None:
        parse.update_num = int(args.times[0])
    if args.shortcuts is not None:
        parse.update_num = 1
        parse.argument = "a-shell"
        parse.shortcuts_url_original = args.shortcuts
    if args.file is not None and ".json" in args.file:
        parse.update_num = 1
        parse.argument = ""
        parse.shortcuts_url_original = []
