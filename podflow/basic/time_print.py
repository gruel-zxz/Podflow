# podflow/basic/time_print.py
# coding: utf-8

from datetime import datetime
from podflow import gVar
from podflow.httpfs.ansi_to_html import ansi_to_html


def time_print(text, Top=False, NoEnter=False, Time=True):
    if Time:
        text = f"{datetime.now().strftime('%H:%M:%S')}|{text}"
    if Top:
        text = f"\r{text}"
    if NoEnter:
        print(text, end="")
    else:
        print(text)
    text = ansi_to_html(text)
    if not gVar.index_message["enter"] and gVar.index_message["podflow"]:
        if Top:
            gVar.index_message["podflow"][0] = text
        else:
            gVar.index_message["podflow"][0] += (text)
    else:
        gVar.index_message["podflow"].append(text)
    if NoEnter:
        gVar.index_message["enter"] = False
