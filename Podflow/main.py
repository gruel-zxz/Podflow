# Podflow/main.py
# coding: utf-8

from datetime import datetime
from Podflow.ffmpeg_judge import ffmpeg_judge
from Podflow.parse_arguments import parse_arguments
from Podflow.config.build_original import build_original

def main():
    parse_arguments()
    print(f"{datetime.now().strftime('%H:%M:%S')}|Podflow开始运行.....")
    ffmpeg_judge()
    build_original()

if __name__ == "__main__":
    main()
