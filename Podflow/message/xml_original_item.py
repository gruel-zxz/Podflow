# podflow/message/xml_original_item.py
# coding: utf-8

import re
import html
import hashlib
from podflow import gVar
from podflow.message.title_correction import title_correction


# 生成原有的item模块
def xml_original_item(original_item, channelid_title, change_judgment=False, title_change=None):
    if title_change:
        title_change = []
    def description_change(text, sep, title, channelid_title):
        channelid_title = html.escape(channelid_title)
        if sep in text:
            text_one, text_two = text.split(sep, 1)
            if text_one[0] == "『" and text_one[-1] == "』":
                text = text_two
        elif text:
            if text[0] == "『" and text[-1] == "』":
                text = ""
        if channelid_title not in title:
            if text == "":
                text = f"『{channelid_title}』{text}"
            else:
                text = f"『{channelid_title}』{sep}{text}".replace('\x00', '')
        return text
    guid = re.search(r"(?<=<guid>).+(?=</guid>)", original_item).group()
    title = re.search(r"(?<=<title>).+(?=</title>)", original_item).group()
    if title_change:
        title = title_correction(title, guid, title_change)
    title = title.replace('\x00', '')
    link = re.search(r"(?<=<link>).+(?=</link>)", original_item).group()
    description = re.search(r"(?<=<description>).+(?=</description>)", original_item)
    description = description.group() if description else ""
    if change_judgment:
        description = description_change(description, "&#xA;", title, channelid_title)
    pubDate = re.search(r"(?<=<pubDate>).+(?=</pubDate>)", original_item).group()
    url = re.search(r"(?<=<enclosure url\=\").+?(?=\")", original_item).group()
    url = re.search(r"(?<=/channel_audiovisual/).+/.+\.(m4a|mp4)", url).group()
    if gVar.config["token"]:
        input_string = f"{gVar.config['token']}/channel_audiovisual/{url}"
    else:
        input_string = f"channel_audiovisual/{url}"
    sha256_hash = hashlib.sha256(input_string.encode()).hexdigest()
    url = f"{gVar.config['address']}/channel_audiovisual/{url}?token={sha256_hash}"
    length = re.search(r"(?<=length\=\")[0-9]+(?=\")", original_item).group()
    type_video = re.search(
        r"(?<=type\=\")(video/mp4|audio/x-m4a|audio/mpeg)(?=\")", original_item
    ).group()
    if type_video == "audio/mpeg":
        type_video = "audio/x-m4a"
    itunes_summary = re.search(
        r"(?<=<itunes:summary><\!\[CDATA\[).+(?=\]\]></itunes:summary>)",
        original_item,
        flags=re.DOTALL,
    )
    itunes_summary = itunes_summary.group() if itunes_summary else ""
    if change_judgment:
        itunes_summary = description_change(itunes_summary, "\n", title, channelid_title)
    itunes_image = re.search(
        r"(?<=<itunes:image href\=\").+(?=\"></itunes:image>)", original_item
    )
    itunes_image = itunes_image.group() if itunes_image else ""
    itunes_duration = re.search(
        r"(?<=<itunes:duration>).+(?=</itunes:duration>)", original_item
    ).group()
    itunes_explicit = re.search(
        r"(?<=<itunes:explicit>).+(?=</itunes:explicit>)", original_item
    ).group()
    itunes_order = re.search(
        r"(?<=<itunes:order>).+(?=</itunes:order>)", original_item
    ).group()
    return f"""
        <item>
            <guid>{guid}</guid>
            <title>{title}</title>
            <link>{link}</link>
            <description>{description}</description>
            <pubDate>{pubDate}</pubDate>
            <enclosure url="{url}" length="{length}" type="{type_video}"></enclosure>
            <itunes:author>{title}</itunes:author>
            <itunes:subtitle>{title}</itunes:subtitle>
            <itunes:summary><![CDATA[{itunes_summary}]]></itunes:summary>
            <itunes:image href="{itunes_image}"></itunes:image>
            <itunes:duration>{itunes_duration}</itunes:duration>
            <itunes:explicit>{itunes_explicit}</itunes:explicit>
            <itunes:order>{itunes_order}</itunes:order>
        </item>
"""
