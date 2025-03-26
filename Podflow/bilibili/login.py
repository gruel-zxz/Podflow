# podflow/bilibili/login.py
# coding: utf-8

import binascii
import json
import os
import re
import time
from datetime import datetime
import requests
from podflow.basic.file_save import file_save
from podflow.basic.http_client import http_client
from podflow.basic.qr_code import qr_code
from podflow.basic.time_stamp import time_stamp
from podflow.basic.write_log import write_log
from podflow.netscape.bulid_netscape import bulid_netscape

try:
    from Cryptodome.Cipher import PKCS1_OAEP
    from Cryptodome.Hash import SHA256
    from Cryptodome.PublicKey import RSA
except Exception:
    from Crypto.Cipher import PKCS1_OAEP
    from Crypto.Hash import SHA256
    from Crypto.PublicKey import RSA


# 获取最新的img_key和sub_key模块
def getWbiKeys(bilibili_cookie=None):
    bilibili_url = "https://api.bilibili.com/x/web-interface/nav"
    if resp := http_client(
        bilibili_url, "获取最新的img_key和sub_key", 10, 4, True, bilibili_cookie
    ):
        resp.raise_for_status()
        json_content = resp.json()
        img_url: str = json_content["data"]["wbi_img"]["img_url"]
        sub_url: str = json_content["data"]["wbi_img"]["sub_url"]
        img_key = img_url.rsplit("/", 1)[1].split(".")[0]
        sub_key = sub_url.rsplit("/", 1)[1].split(".")[0]
        return img_key, sub_key
    else:
        return "", ""


# 申请哔哩哔哩二维码并获取token和URL模块
def bilibili_request_qr_code():
    # 实际申请二维码的API请求
    response = http_client(
        "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
        "申请BiliBili二维码",
        3,
        5,
        True,
    )
    data = response.json()
    return data["data"]["qrcode_key"], data["data"]["url"]


# 扫码登录哔哩哔哩并返回状态和cookie模块
def bilibili_scan_login(token):
    # 发送GET请求
    response = http_client(
        "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
        "",
        1,
        1,
        True,
        None,
        {"qrcode_key": token},
    )
    if not response:
        return None, None, None
    data = response.json()
    return data["data"]["code"], response.cookies, data["data"]["refresh_token"]


# 登陆哔哩哔哩模块
def bilibili_login():
    buvid3_and_bnut = http_client(
        "https://www.bilibili.com", "哔哩哔哩主页", 10, 4, True
    ).cookies.get_dict()
    token, url = bilibili_request_qr_code()
    print(f"{datetime.now().strftime('%H:%M:%S')}|请用BiliBili App扫描登录:")
    upward = qr_code(url)
    login_status_change = ""
    time_text = f"{datetime.now().strftime('%H:%M:%S')}|BiliBili "
    while True:
        status, cookie, refresh_token = bilibili_scan_login(token)
        if status == 86101:
            login_status = "\033[0m未扫描\033[0m"
        elif status == 86038:
            login_status = "\033[31m二维码超时, 请重试\033[0m"
        elif status == 86090:
            login_status = "\033[32m扫描成功\033[0m"
        elif status == 0:
            login_status = "\033[32m登陆成功\033[0m"
        else:
            login_status = "\033[31m错误\033[0m"
        if login_status_change != login_status:
            if login_status == "":
                print(f"{time_text}{login_status}".ljust(42), end="")
            else:
                print(f"\r{time_text}{login_status}".ljust(42), end="")
        login_status_change = login_status
        if status == 86038:
            print("")
            return status, refresh_token, upward
        elif status == 0:
            print("")
            cookie["buvid3"] = buvid3_and_bnut.get("buvid3", "")
            cookie["b_nut"] = buvid3_and_bnut.get("b_nut", "")
            return cookie, refresh_token, upward
        time.sleep(1)


# 保存哔哩哔哩登陆成功后的cookies模块
def save_bilibili_cookies():
    bilibili_cookie, refresh_token, upward = bilibili_login()
    if bilibili_cookie == 86038:
        return {"cookie": None}, upward
    bilibili_cookie = requests.utils.dict_from_cookiejar(bilibili_cookie)
    bilibili_data = {"cookie": bilibili_cookie, "refresh_token": refresh_token}
    bulid_netscape("yt_dlp_bilibili", bilibili_cookie)
    return bilibili_data, upward


# 检查哔哩哔哩是否需要刷新模块
def judgment_bilibili_update(cookies):
    url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
    response = http_client(url, "BiliBili刷新判断", 3, 5, True, cookies)
    response = response.json()
    if response["code"] == 0:
        return response["code"], response["data"]["refresh"]
    else:
        return response["code"], None


# 生成CorrespondPath模块
def getCorrespondPath(ts, key):
    cipher = PKCS1_OAEP.new(key, SHA256)
    encrypted = cipher.encrypt(f"refresh_{ts}".encode())
    return binascii.b2a_hex(encrypted).decode()


def bilibili_cookie_update_data(
    bilibili_cookie, new_bilibili_cookie, bilibili_data, new_refresh_token
):
    new_bilibili_cookie["buvid3"] = bilibili_cookie["buvid3"]
    new_bilibili_cookie["b_nut"] = bilibili_cookie["b_nut"]
    bilibili_data["cookie"] = new_bilibili_cookie
    bilibili_data["refresh_token"] = new_refresh_token
    bulid_netscape("yt_dlp_bilibili", new_bilibili_cookie)
    return bilibili_data


# 哔哩哔哩cookie刷新模块
def bilibili_cookie_update(bilibili_data):
    bilibili_cookie = bilibili_data["cookie"]
    # 获取refresh_csrf
    key = RSA.importKey("""\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----""")

    # 获取当前时间戳
    ts = time_stamp()
    # 获取refresh_csrf
    refresh_csrf_response = http_client(
        f"https://www.bilibili.com/correspond/1/{getCorrespondPath(ts, key)}",
        "获取refresh_csrf",
        3,
        5,
        True,
        bilibili_cookie,
    )
    if refresh_csrf_match := re.search(
        r'<div id="1-name">(.+?)</div>', refresh_csrf_response.text
    ):
        refresh_csrf_value = refresh_csrf_match[1]
    else:
        return {"cookie": None}
    # 更新bilibili_cookie
    update_cookie_url = (
        "https://passport.bilibili.com/x/passport-login/web/cookie/refresh"
    )
    update_cookie_data = {
        "csrf": bilibili_cookie["bili_jct"],
        "refresh_csrf": refresh_csrf_value,
        "source": "main_web",
        "refresh_token": bilibili_data["refresh_token"],
    }
    update_cookie_response = http_client(
        update_cookie_url,
        "更新BiliBili_cookie",
        3,
        5,
        True,
        bilibili_cookie,
        update_cookie_data,
        "post",
    )
    if update_cookie_response.json()["code"] != 0:
        return {"cookie": None}
    new_bilibili_cookie = requests.utils.dict_from_cookiejar(
        update_cookie_response.cookies
    )
    new_refresh_token = update_cookie_response.json()["data"]["refresh_token"]
    # 确认更新bilibili_cookie
    confirm_cookie_url = (
        "https://passport.bilibili.com/x/passport-login/web/confirm/refresh"
    )
    confirm_cookie_data = {
        "csrf": new_bilibili_cookie["bili_jct"],
        "refresh_token": bilibili_data["refresh_token"],
    }
    confirm_cookie_response = http_client(
        confirm_cookie_url,
        "确认更新BiliBili_cookie",
        3,
        5,
        True,
        new_bilibili_cookie,
        confirm_cookie_data,
        "post",
    )
    if confirm_cookie_response.json()["code"] == 0:
        return bilibili_cookie_update_data(
            bilibili_cookie,
            new_bilibili_cookie,
            bilibili_data,
            new_refresh_token,
        )
    else:
        return {"cookie": None}


def get_bilibili_data_success(bilibili_data, channelid_bilibili_ids):
    print(
        f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[32m获取cookie成功\033[0m"
    )
    img_key, sub_key = getWbiKeys()
    bilibili_data["img_key"] = img_key
    bilibili_data["sub_key"] = sub_key
    bilibili_data["timestamp"] = time.time()
    file_save(bilibili_data, "bilibili_data.json", "channel_data")
    if not os.path.isfile("channel_data/yt_dlp_bilibili.txt"):
        bulid_netscape("yt_dlp_bilibili", bilibili_data["cookie"])
    return channelid_bilibili_ids, bilibili_data


def get_bilibili_data_state(bilibili_data, channelid_bilibili_ids):
    bilibili_login_code, bilibili_login_refresh_token = judgment_bilibili_update(
        bilibili_data["cookie"]
    )
    upward = 0
    try_num = 0
    while try_num < 2 and (
        bilibili_login_code != 0 or bilibili_login_refresh_token is not False
    ):
        if bilibili_login_code != 0:
            if try_num == 0:
                print(
                    f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[31m未登陆\033[0m"
                )
            else:
                print(
                    f"\033[{upward + 3}F\033[{upward + 3}K{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[31m未登陆, 重试第\033[0m{try_num}\033[31m次\033[0m"
                )
            bilibili_data, upward = save_bilibili_cookies()
            try_num += 1
        else:
            print(
                f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[33m需刷新\033[0m"
            )
            bilibili_data = bilibili_cookie_update(bilibili_data)
            if bilibili_data["cookie"]:
                print(
                    f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[32m刷新成功\033[0m"
                )
            else:
                print(
                    f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[31m刷新失败, 重新登陆\033[0m"
                )
        bilibili_login_code, bilibili_login_refresh_token = judgment_bilibili_update(
            bilibili_data["cookie"]
        )
    if bilibili_login_code == 0 and bilibili_login_refresh_token is False:
        return get_bilibili_data_success(bilibili_data, channelid_bilibili_ids)
    write_log("BiliBili \033[31m获取cookie失败\033[0m")
    return {}, {"cookie": None, "timestamp": 0.0}


# 登陆刷新哔哩哔哩并获取data
def get_bilibili_data(channelid_bilibili_ids):
    if not channelid_bilibili_ids:
        return {}, {"cookie": None, "timestamp": 0.0}
    try:
        with open("channel_data/bilibili_data.json", "r") as file:
            bilibili_data = file.read()
        bilibili_data = json.loads(bilibili_data)
    except Exception:
        bilibili_data = {"cookie": None, "timestamp": 0.0}
    if time.time() - bilibili_data["timestamp"] - 60 * 60 > 0:
        return get_bilibili_data_state(bilibili_data, channelid_bilibili_ids)
    print(
        f"{datetime.now().strftime('%H:%M:%S')}|BiliBili \033[33m获取cookie成功\033[0m"
    )
    if not os.path.isfile("channel_data/yt_dlp_bilibili.txt"):
        bulid_netscape("yt_dlp_bilibili", bilibili_data["cookie"])
    return channelid_bilibili_ids, bilibili_data
