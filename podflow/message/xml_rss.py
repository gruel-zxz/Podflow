# podflow/message/xml_rss.py
# coding: utf-8

import time


# 生成XML模块
def xml_rss(title, link, description, category, icon, items):
    # 获取当前时间
    current_time_now = time.time()  # 获取当前时间的秒数
    # 获取当前时区和夏令时信息
    time_info_now = time.localtime(current_time_now)
    # 构造时间字符串
    formatted_time_now = time.strftime("%a, %d %b %Y %H:%M:%S %z", time_info_now)
    #itunes_summary = description.replace("\n", "&#xA;")
    if title == "Podflow":
        author = "gruel-zxz"
        subtitle = "gruel-zxz-podflow"
    else:
        author = title
        subtitle = title
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
    <channel>
        <title>{title}</title>
        <link>{link}</link>
        <description>{description}</description>
        <category>{category}</category>
        <generator>Podflow (support us at https://github.com/gruel-zxz/podflow)</generator>
        <language>en-us</language>
        <lastBuildDate>{formatted_time_now}</lastBuildDate>
        <pubDate>Sun, 24 Apr 2005 11:20:54 +0800</pubDate>
        <image>
            <url>{icon}</url>
            <title>{title}</title>
            <link>{link}</link>
        </image>
        <itunes:author>{author}</itunes:author>
        <itunes:subtitle>{subtitle}</itunes:subtitle>
        <itunes:summary><![CDATA[{description}]]></itunes:summary>
        <itunes:image href="{icon}"></itunes:image>
        <itunes:explicit>no</itunes:explicit>
        <itunes:category text="{category}"></itunes:category>
{items}
    </channel>
</rss>"""
