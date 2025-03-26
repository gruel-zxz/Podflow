# podflow/parse_arguments.py
# coding: utf-8

import argparse
from podflow import parse


def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
    return ivalue


# 获取命令行参数并判断
def parse_arguments():
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(
        description="You can try: Podflow -n 24 -d 3600"
    )
    # 参数
    parser.add_argument(
        "-n",
        "--times",
        nargs=1,
        type=positive_int,
        metavar="NUM",
        help="Number of times",
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=positive_int,
        default=1500,
        metavar="NUM",
        help="Delay in seconds(default: 1500)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config.json",
        metavar="FILE_PATH",
        help="Path to the config.json file",
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
        help="Only shortcuts can be work",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Only shortcuts can be work",
    )
    parser.add_argument(
        "--httpfs",
        action="store_true",
        help="Only enable server functionality, do not update channels",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Only upload server function, solely for LAN backup (applicable to iOS)",
    )
    parser.add_argument("--file", nargs="?", help=argparse.SUPPRESS)  # 仅运行在ipynb中
    # 解析参数
    args = parser.parse_args()
    parse.time_delay = args.delay
    parse.config = args.config
    parse.period = args.period
    parse.file = args.file
    parse.httpfs = args.httpfs
    parse.upload = args.upload
    parse.index = args.index
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
