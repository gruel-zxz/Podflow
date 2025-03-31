# podflow/httpfs/ansi_to_htmlpy
# coding: utf-8

import re
import html


def ansi_to_html(ansi_text):
    html_output = ""
    ansi_codes = {
        "\033[30m": "color: 30m;",  # 黑色
        "\033[31m": "color: 31m;",  # 红色
        "\033[32m": "color: 32m;",  # 绿色
        "\033[33m": "color: 33m;",  # 黄色
        "\033[34m": "color: 34m;",  # 蓝色
        "\033[35m": "color: 35m;",  # 品红
        "\033[36m": "color: 36m;",  # 青色
        "\033[37m": "color: 37m;",  # 白色
        "\033[90m": "color: 90m;",  # 亮黑色 (通常显示为灰色)
        "\033[91m": "color: 91m;",  # 亮红色 (例如：热粉色)
        "\033[92m": "color: 92m;",  # 亮绿色 (例如：浅绿色)
        "\033[93m": "color: 93m;",  # 亮黄色 (通常与黄色相同)
        "\033[94m": "color: 94m;",  # 亮蓝色 (例如：浅蓝色)
        "\033[95m": "color: 95m;",  # 亮品红 (通常与品红相同)
        "\033[96m": "color: 96m;",  # 亮青色 (通常与青色相同)
        "\033[97m": "color: 97m;",  # 亮白色 (例如：爱丽丝蓝)
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

    return html_output
