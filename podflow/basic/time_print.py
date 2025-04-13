# podflow/basic/time_print.py
# coding: utf-8

from datetime import datetime
from podflow import gVar
from podflow.httpfs.to_html import ansi_to_html, qrcode_to_html


def time_print(
    text,
    Top=False,
    NoEnter=False,
    Time=True,
    Url="",
    Qrcode=False,
    Number=None,
    Head="",
):
    if Time:
        text = f"{datetime.now().strftime('%H:%M:%S')}|{text}"
    text_print = f"\r{text}" if Top else f"{text}"
    if Url:
        text_print = f"{text_print}\n\033[34m{Url}\033[0m"
    if Head:
        text_print = f"{Head}{text_print}"
    if NoEnter:
        print(text_print, end="")
    else:
        print(text_print)

    if Number is not None and (
        not isinstance(Number, int)
        or not -min(len(gVar.index_message["podflow"]), 4) <= Number < 0
    ):
        Number = None
    if text:
        text = qrcode_to_html(Qrcode) if Qrcode else ansi_to_html(text)
        if Number:
            gVar.index_message["podflow"][Number] = text
        elif not gVar.index_message["enter"] and gVar.index_message["podflow"]:
            if Top:
                gVar.index_message["podflow"][-1] = text
            else:
                gVar.index_message["podflow"][-1] += text
        else:
            gVar.index_message["podflow"].append(text)
    gVar.index_message["enter"] = not NoEnter
    if Url:
        gVar.index_message["podflow"].append(
            f'<a href="{Url}" target="_blank"><span class="ansi-url">{Url}</span></a>'
        )
