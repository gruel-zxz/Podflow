# update_version.py

import re
import sys
import requests


# 获取三方库版本号模块
def get_version_num(library):
    version_json = requests.get(f"https://pypi.org/pypi/{library}/json")
    if version_json:
        version_json = version_json.json()
        version_update = version_json["info"]["version"]
        return version_update
    else:
        return None


def update_setup_version(new_version: str):
    """更新 setup.py 中的版本号"""
    setup_file = "setup.py"
    # 读取文件内容
    with open(setup_file, "r") as f:
        content = f.read()
    # 使用正则表达式精准替换版本号
    # 匹配格式：version="1.2.3" 或 version = '4.5.6'
    new_content = re.sub(
        r"version=\".+\"",
        f'version="{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    if yt_dlp_num := get_version_num("yt-dlp"):
        new_content = re.sub(
            r"\"yt-dlp>=.+\"",
            f'"yt-dlp>={yt_dlp_num}"',
            new_content,
            flags=re.MULTILINE,
        )
    # 写回文件
    with open(setup_file, "w") as f:
        f.write(new_content)


def get_webpage_content(url):
    try:
        # 发送HTTP GET请求
        response = requests.get(url)
        # 检查请求是否成功 (状态码200表示成功)
        if response.status_code == 200:
            # 返回网页的文本内容
            return response.text
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求过程中发生错误：{e}")
        return None


def read_text_file_full(filepath):
    try:
        # 'with' 语句确保文件在使用后被正确关闭
        # 'r' 表示只读模式 (默认)
        # encoding 参数很重要，特别是处理非UTF-8编码的文件时
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"错误：文件 '{filepath}' 未找到。")
        return None
    except Exception as e:
        print(f"读取文件 '{filepath}' 时发生错误：{e}")
        return None


def update_version():
    address = "podflow/podflow/templates/index.html"
    url = "https://raw.githubusercontent.com/gruel-zxz/Podflow/refs/heads/main/podflow/templates/index.html"  # 替换成你要获取的网页URL
    content = get_webpage_content(url)
    pattern = r"(?<=Version\: )[0-9]+\.[0-9]+\.[0-9]+"
    original_version = re.findall(pattern, content)
    index = read_text_file_full(address)
    version = re.findall(pattern, index)
    if original_version and version:
        original_version = original_version[0]
        version = version[0]
        v1, v2, v3 = version.split(".")
        if original_version == version:
            v3 = int(v3) + 1
            new_version = f"{v1}.{v2}.{v3}"
        else:
            new_version = f"{v1}.{v2}.0"
        index = re.sub(pattern, new_version, index)
        try:
            with open(address, 'w', encoding="utf-8") as file:
                file.write(index)
            print(f"文本内容已成功保存到 '{address}'。")
        except Exception as e:
            print(f"保存文件 '{address}' 时发生错误：{e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <new_version>")
        sys.exit(1)

    new_version = sys.argv[1]
    update_setup_version(new_version)
    update_version()
    print(f"Updated setup.py version to: {new_version}")
