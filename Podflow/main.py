# Podflow/main.py
# coding: utf-8

import argparse
from datetime import datetime


# 获取命令行参数并判断
class Application:
    def __init__(self):
        self.shortcuts_url_original = []
        self.argument = ""
        self.update_num = -1
    def parse_arguments(self):
        def positive_int(value):
            ivalue = int(value)
            if ivalue <= 0:
                raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
            return ivalue
        # 创建 ArgumentParser 对象
        parser = argparse.ArgumentParser(description="you can try: python Podflow.py -n 24 -d 3600")
        # 参数
        parser.add_argument("-n", "--times", nargs=1, type=positive_int, metavar="NUM", help="number of times")
        parser.add_argument("-d", "--delay", type=positive_int, default=1500, metavar="NUM", help="delay in seconds(default: 1500)")
        parser.add_argument("-c", "--config", type=str, default="config.json", metavar='FILE_PATH', help="path to the config.json file")
        parser.add_argument("-p", "--period", type=positive_int, metavar="NUM", default=1, help="Specify the update frequency (unit: times/day), default value is 1")
        parser.add_argument("--shortcuts", nargs="*", type=str, metavar="URL", help="only shortcuts can be work")
        parser.add_argument("--file", nargs='?', help=argparse.SUPPRESS)
        parser.add_argument("--httpfs", action='store_true', help=argparse.SUPPRESS)
        # 解析参数
        args = parser.parse_args()
        self.time_delay = args.delay
        self.config = args.config
        self.period = args.period
        self.file = args.file
        self.httpfs = args.httpfs
        # 检查并处理参数的状态
        if args.times is not None:
            self.update_num = int(args.times[0])
        if args.shortcuts is not None:
            self.update_num = 1
            self.argument = "a-shell"
            self.shortcuts_url_original = args.shortcuts
        if args.file is not None and ".json" in args.file:
            self.update_num = 1
            self.argument = ""
            self.shortcuts_url_original = []

parse_app = Application()




def main():
    parse_app.parse_arguments()
    print(f"{datetime.now().strftime('%H:%M:%S')}|Podflow开始运行.....")


if __name__ == "__main__":
    main()
