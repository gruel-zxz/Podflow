# podflow/basic/time_print.py
# coding: utf-8

from datetime import datetime
from podflow import gVar
from podflow.httpfs.to_html import ansi_to_html


def time_print(text, Top=False, NoEnter=False, Time=True, Url=""):
    if Time:
        text = f"{datetime.now().strftime('%H:%M:%S')}|{text}"
    if Top:
        text = f"\r{text}"
    if Url:
        text_print = f"{text}\n\033[34m{Url}\033[0m"
    else:
        text_print = f"{text}"
    if NoEnter:
        print(text_print, end="")
    else:
        print(text_print)

    if text:
        text = ansi_to_html(text)
    gVar.index_message["podflow"].append(
        [
            text,
            Top,
            NoEnter,
        ]
    )
    if Url:
        gVar.index_message["podflow"].append(
            [
                f'<a href="{Url}"><span class="ansi-url">{Url}</span></a>',
                Top,
                NoEnter,
            ]
        )
