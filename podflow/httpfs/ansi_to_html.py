# podflow/httpfs/ansi_to_htmlpy
# coding: utf-8

import re
import html


def ansi_to_html(ansi_text):
    html_output = ""
    ansi_codes = {
        "\033[30m": "color: black;",  # 黑色
        "\033[31m": "color: red;",  # 红色
        "\033[32m": "color: green;",  # 绿色
        "\033[33m": "color: yellow;",  # 黄色
        "\033[34m": "color: blue;",  # 蓝色
        "\033[35m": "color: magenta;",  # 品红
        "\033[36m": "color: cyan;",  # 青色
        "\033[37m": "color: white;",  # 白色
        "\033[90m": "color: gray;",  # 亮黑色 (通常显示为灰色)
        "\033[91m": "color: #ff69b4;",  # 亮红色 (例如：热粉色)
        "\033[92m": "color: #90ee90;",  # 亮绿色 (例如：浅绿色)
        "\033[93m": "color: #ffff00;",  # 亮黄色 (通常与黄色相同)
        "\033[94m": "color: #add8e6;",  # 亮蓝色 (例如：浅蓝色)
        "\033[95m": "color: #ff00ff;",  # 亮品红 (通常与品红相同)
        "\033[96m": "color: #00ffff;",  # 亮青色 (通常与青色相同)
        "\033[97m": "color: #f0f8ff;",  # 亮白色 (例如：爱丽丝蓝)
        "\033[0m": "",  # 重置
    }
    inside_span = False

    parts = re.split(r"(\033\[\d+m)", ansi_text)

    for part in parts:
        if part in ansi_codes:
            style = ansi_codes[part]
            if style:
                if inside_span:
                    html_output += "</span>"
                html_output += f'<span style="{style}">'
                inside_span = True
            elif inside_span:  # Reset code
                html_output += "</span>"
                inside_span = False
        else:
            escaped_part = html.escape(part)
            html_output += escaped_part

    if inside_span:
        html_output += "</span>"

    #html_output = html_output.replace("\n", "</p><p>")
    return html_output
