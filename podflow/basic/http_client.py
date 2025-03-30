# podflow/basic/http_client.py
# coding: utf-8

import time
import requests
from podflow.basic.time_print import time_print


# HTTP 请求重试模块
def http_client(
    url,
    name="",
    max_retries=10,
    retry_delay=4,
    headers_possess=False,
    cookies=None,
    data=None,
    mode="get",
    filename=None,
):
    user_agent = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    if "bilibili" in url:
        user_agent["Referer"] = "https://www.bilibili.com/"
    elif "youtube" in url:
        user_agent["Referer"] = "https://www.youtube.com/"
    elif "douyin" in url:
        headers_douyin = {
            "authority": "sso.douyin.com",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "origin": "https://www.douyin.com",
            "referer": "https://www.douyin.com/",
            "sec-ch-ua": '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        }
        user_agent |= headers_douyin
    err = None  # 初始化 err 变量
    response = None  # 初始化 response 变量
    # 创建一个Session对象
    session = requests.Session()
    if headers_possess:
        session.headers.update(user_agent)
    if cookies:
        session.cookies.update(cookies)
    if data:
        session.params.update(data)
    for num in range(max_retries):
        try:
            if mode.lower() != "post":
                response = session.get(url, timeout=8)
            elif filename:
                with open(filename, "rb") as f:
                    files = {"file": f}  # 这里 "file" 对应服务器端接收文件的字段名称
                    response = session.post(url, files=files, timeout=8)
            else:
                response = session.post(url, timeout=8)
            response.raise_for_status()
        except Exception as http_get_error:
            if response is not None and response.status_code in {404}:
                return response
            if name:
                time_print(f"{name}|\033[31m连接异常重试中...\033[97m{num + 1}\033[0m")
            if err:
                err = f"{err}\n{str(http_get_error)}"
            else:
                err = f":\n{str(http_get_error)}"
        else:
            return response
        time.sleep(retry_delay)
    if name:
        time_print(f"{name}|\033[31m达到最大重试次数\033[97m{max_retries}\033[0m{err}")
    return response
