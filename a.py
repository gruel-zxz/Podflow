import argparse

# 参数输入判断
shortcuts_url =[]
argument = ""
update_num = -1
def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
    return ivalue
# 创建 ArgumentParser 对象
parser = argparse.ArgumentParser(description="python Podflow.py [-h] [-n [NUM]] [--shortcuts [URL ...]]")
# 参数
parser.add_argument("-n", "--times", nargs=1, type=positive_int, metavar='NUM', help="number of times")
parser.add_argument("--shortcuts", nargs="*", type=str, metavar='URL', help="only shortcuts can be work")
parser.add_argument('--file', nargs='?', help=argparse.SUPPRESS)
# 解析参数
args = parser.parse_args()
# 检查并处理参数的状态
if args.times is not None :
    update_num = int(args.times[0])
if args.shortcuts is not None:
    update_num = 1
    argument = "a-shell"
    shortcuts_url = args.shortcuts
if args.file is not None and ".json" in args.file:
    update_num = 1
    argument = ""
    shortcuts_url = []

print(update_num)
print(argument)
print(shortcuts_url)
    
    
# python a.py --shortcuts "http://www.ximalaya.com/album/203355.xml" "https://anchor.fm/s/1d6f42f4/podcast/rss" "http://127.0.0.1:8000/YouTube.xml" "http://listenbox.app/f/JijNlIdHZq2G" "http://feeds.listenbox.app/rss/wvz03Pu8wDrG/audio.rss" "http://gruel-nas:2525/early_edu/music/songs/music.xml" "http://127.0.0.1:8000/channel_rss/1839002753.xml" "http://127.0.0.1:8000/channel_rss/3393923.xml"