# podflow/basic/time_print.py
# coding: utf-8

from datetime import datetime
from podflow import gVar
from podflow.httpfs.to_html import ansi_to_html


def time_print(text, Top=False, NoEnter=False, Time=True, Url=""):
    if Time:
        text = f"{datetime.now().strftime('%H:%M:%S')}|{text}"
    if Top:
        text_print = f"\r{text}"
    else:
        text_print = f"{text}"
    if Url:
        text_print = f"{text_print}\n\033[34m{Url}\033[0m"
    if NoEnter:
        print(text_print, end="")
    else:
        print(text_print)

    if text:
        text = ansi_to_html(text)
        if not gVar.index_message["enter"] and gVar.index_message["podflow"]:
            if Top and gVar.index_message["podflow"]:
                gVar.index_message["podflow"][-1] = text
            else:
                gVar.index_message["podflow"][-1] += text
        else:
            gVar.index_message["podflow"].append(text)
    if NoEnter:
        gVar.index_message["enter"] = False
    else:
        gVar.index_message["enter"] = True
    if Url:
        gVar.index_message["podflow"].append(
            f'<a href="{Url}"><span class="ansi-url">{Url}</span></a>'
        )
