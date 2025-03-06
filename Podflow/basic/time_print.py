# Podflow/basic/time_print.py
# coding: utf-8

from datetime import datetime


def time_print(text, Top=False, Enter=False, Time=True):
    if Time:
        text = f"{datetime.now().strftime('%H:%M:%S')}|{text}"
    if Top:
        text = f"\r{text}"
    if Enter:
        print(text, end="")
    else:
        print(text)
