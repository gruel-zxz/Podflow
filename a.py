import argparse
import re
import datetime

# 正则表达式匹配网址
url_regex = re.compile(
    r'^(https?:\/\/)?'  # 协议 http 或 https
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+)'  # 域名
    r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)'  # 顶级域名
    r'|localhost|'  # 本地主机名
    r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # 并且 IP 地址
    r'(?::\d+)?'  # 端口号
    r'(?:/?|[/?]\S+)$',  # 路径
    re.IGNORECASE
)

# 自定义类型转换函数，用于验证网址
def validate_url(url):
    if url_regex.match(url):
        return url
    else:
        raise argparse.ArgumentTypeError(f"{datetime.now().strftime('%H:%M:%S')}|无效的网址: {url}")

# 创建 ArgumentParser 对象
parser = argparse.ArgumentParser(description="python Podflow.py [-n int]")

# 参数
parser.add_argument("-n", "--times", type=int, default=1, help="number of times")
parser.add_argument("--shortcuts", nargs="*", type=validate_url, help="only shortcuts can be work")
parser.add_argument("urls", nargs="+", type=validate_url)

# 解析参数
args = parser.parse_args()

# 使用参数
print(f"echo 的字符串是: {args.times}")
