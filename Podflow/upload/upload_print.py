# Podflow/upload/upload_print.py
# coding: utf-8

from datetime import datetime


def upload_print(text):
    print(f"{datetime.now().strftime('%H:%M:%S')}|{text}")
