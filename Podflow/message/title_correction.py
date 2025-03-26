# podflow/message/title_correction.py
# coding: utf-8

import re


# 标题文本修改
def title_correction(title, video_url, title_changes: list):
    for title_change in title_changes:
        match = title_change.get("match", None)
        mode = title_change["mode"]
        text = title_change["text"]
        table = title_change.get("table", [])

        def add_title(mode, text, title):
            if mode == "add-left":
                return text + title
            elif mode == "add-right":
                return title + text

        if text and text in title:
            return title
        elif video_url in table:
            return add_title(mode, text, title)
        elif match is not None and re.search(match, title):
            if mode == "replace":
                return re.sub(match, text, title)
            else:
                return add_title(mode, text, title)
    return title
