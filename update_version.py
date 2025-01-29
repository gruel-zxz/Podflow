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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <new_version>")
        sys.exit(1)

    new_version = sys.argv[1]
    update_setup_version(new_version)
    print(f"Updated setup.py version to: {new_version}")
