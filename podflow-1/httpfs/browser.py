# podflow/httpfs/browser.py
# coding: utf-8

import os


def open_url(url):
    browser = os.getenv("BROWSER", "internalbrowser")
    os.system(f"{browser} {url}")  # 在后台运行，避免阻塞