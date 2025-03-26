# podflow/basic/get_html_dict.py
# coding: utf-8

import re
import json
from bs4 import BeautifulSoup
from podflow.basic.http_client import http_client


# 通过bs4获取html中字典模块
def get_html_dict(url, name, script_label):
    if not (response := http_client(url, name)):
        return None
    html_content = response.text
    # 使用Beautiful Soup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    if not (
        data_script := soup.find(
            'script', string=lambda t: t and script_label in t
        )
    ):
        return None
    try:
        # 使用正则表达式提取 JSON 数据
        pattern = re.compile(r'\{.*\}', re.DOTALL)
        if match := pattern.search(data_script.text):
            data_str = match.group()
            return json.loads(data_str)
    except json.JSONDecodeError:
        return None
