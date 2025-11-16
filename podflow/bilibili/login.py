# podflow/bilibili/login.py
# coding: utf-8

import os
import re
import time
import json
import binascii
import base64
import hashlib
import requests
from datetime import datetime
from podflow.basic.qr_code import qr_code
from podflow.basic.write_log import write_log
from podflow.basic.file_save import file_save
from podflow.basic.time_print import time_print
from podflow.basic.time_stamp import time_stamp
from podflow.basic.http_client import http_client
from podflow.netscape.bulid_netscape import bulid_netscape


def mgf1(seed: bytes, length: int, hash_func=hashlib.sha256) -> bytes:
    """MGF1 based on given hash function."""
    counter = 0
    output = b""
    while len(output) < length:
        C = counter.to_bytes(4, "big")
        output += hash_func(seed + C).digest()
        counter += 1
    return output[:length]


def oaep_pad(message: bytes, k: int, label: bytes = b"", hash_func=hashlib.sha256) -> bytes:
    """
    OAEP pad the message for RSA encryption.
    - k: modulus length in bytes
    - hash_func: hash constructor (e.g. hashlib.sha256)
    Returns the padded message of length k bytes.
    """
    hlen = hash_func().digest_size
    mlen = len(message)
    if mlen > k - 2 * hlen - 2:
        raise ValueError("message too long for OAEP padding with given key size")

    lhash = hash_func(label).digest()
    ps = b"\x00" * (k - mlen - 2 * hlen - 2)
    db = lhash + ps + b"\x01" + message
    seed = os.urandom(hlen)
    db_mask = mgf1(seed, k - hlen - 1, hash_func)
    masked_db = bytes(x ^ y for x, y in zip(db, db_mask))
    seed_mask = mgf1(masked_db, hlen, hash_func)
    masked_seed = bytes(x ^ y for x, y in zip(seed, seed_mask))
    return b"\x00" + masked_seed + masked_db


def rsa_encrypt_integer(padded: bytes, n: int, e: int, k: int) -> bytes:
    """Compute ciphertext = (m^e mod n) and return k-byte big-endian."""
    m = int.from_bytes(padded, "big")
    c = pow(m, e, n)
    return c.to_bytes(k, "big")


# Minimal ASN.1 DER parser helpers to extract modulus n and exponent e from an RSA public key PEM.
def _der_read_length(data: bytes, idx: int):
    first = data[idx]
    idx += 1
    if first & 0x80 == 0:
        return first, idx
    num_bytes = first & 0x7F
    if num_bytes == 0:
        raise ValueError("Invalid DER length")
    length = int.from_bytes(data[idx: idx + num_bytes], "big")
    idx += num_bytes
    return length, idx


def _der_read_tlv(data: bytes, idx: int):
    if idx >= len(data):
        raise ValueError("DER parse error: index out of range")
    tag = data[idx]
    idx += 1
    length, idx = _der_read_length(data, idx)
    value = data[idx: idx + length]
    return tag, length, value, idx + length


def parse_rsa_public_key_from_pem(pem: str):
    """
    Parse an RSA public key from PEM string (SubjectPublicKeyInfo or RSAPublicKey).
    Returns (n, e) as integers.
    """
    pem_body = re.sub(r"-----BEGIN [^-]+-----", "", pem)
    pem_body = re.sub(r"-----END [^-]+-----", "", pem_body)
    pem_body = re.sub(r"\s+", "", pem_body)
    der = base64.b64decode(pem_body)

    # parse outer SEQUENCE
    idx = 0
    tag, _length, value, _next_idx = _der_read_tlv(der, idx)
    if tag != 0x30:  # SEQUENCE
        raise ValueError("Not a valid ASN.1 SEQUENCE for public key")
    seq = value
    seq_idx = 0

    # try to detect if this is SubjectPublicKeyInfo (algorithm + BITSTRING) or direct RSAPublicKey
    # If inside sequence we find a BIT STRING (0x03), it's SPKI; inside the bit string is RSAPublicKey sequence
    # else, if the first element is INTEGER then it's likely RSAPublicKey directly (rare in SPKI PEM form)
    # We'll scan for a BIT STRING
    # parse first element inside seq
    try:
        tag1, _len1, _val1, _pos1 = _der_read_tlv(seq, seq_idx)
    except Exception:
        raise ValueError("Malformed public key ASN.1")

    if tag1 == 0x30:
        # Could be SPKI: sequence -> sequence(alg) + bitstring(pubkey)
        # Move to next element after the algorithm sequence
        seq_idx = 0
        # Read algorithm sequence
        _tag_a, _len_a, _val_a, seq_idx = _der_read_tlv(seq, seq_idx)
        # Next should be BIT STRING
        tag_b, _len_b, val_b, _seq_idx2 = _der_read_tlv(seq, seq_idx)
        if tag_b != 0x03:
            # Not SPKI? fallback attempt: treat original DER as RSAPublicKey
            der_rsa = der
        else:
            # val_b is BIT STRING; the first byte is number of unused bits, usually 0
            der_rsa = val_b[1:]
    else:
        # Not a sequence as first element — treat whole DER as RSAPublicKey
        der_rsa = der

    # Now der_rsa should be an RSAPublicKey sequence: SEQUENCE { INTEGER(n), INTEGER(e) }
    idx2 = 0
    tag_r, _len_r, val_r, _next_r = _der_read_tlv(der_rsa, idx2)
    if tag_r != 0x30:
        raise ValueError("Expected RSAPublicKey SEQUENCE")
    inner = val_r
    inner_idx = 0
    # read modulus
    tag_n, _len_n, val_n, inner_idx = _der_read_tlv(inner, inner_idx)
    if tag_n != 0x02:
        raise ValueError("Expected INTEGER (modulus)")
    # read exponent
    tag_e, _len_e, val_e, _inner_idx2 = _der_read_tlv(inner, inner_idx)
    if tag_e != 0x02:
        raise ValueError("Expected INTEGER (exponent)")

    n = int.from_bytes(val_n, "big")
    e = int.from_bytes(val_e, "big")
    return n, e


def rsa_encrypt_oaep_sha256(message: bytes, pem_key: str) -> bytes:
    """
    High-level wrapper:
    - parse PEM key to n,e
    - compute OAEP(SHA256) padding
    - RSA encrypt and return raw ciphertext bytes
    """
    n, e = parse_rsa_public_key_from_pem(pem_key)
    k = (n.bit_length() + 7) // 8
    padded = oaep_pad(message, k, label=b"", hash_func=hashlib.sha256)
    ciphertext = rsa_encrypt_integer(padded, n, e, k)
    return ciphertext


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
def bilibili_login(retry=False):
    buvid3_and_bnut = http_client(
        "https://www.bilibili.com", "哔哩哔哩主页", 10, 4, True
    ).cookies.get_dict()
    token, url = bilibili_request_qr_code()
    if retry:
        time_print("请用BiliBili App扫描登录:", Number=-3)
        upward = qr_code(url, to_html=True, num=-2)
    else:
        time_print("请用BiliBili App扫描登录:")
        upward = qr_code(url, to_html=True)
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
            num = -1 if retry else None
            if login_status == "":
                time_print(
                    f"{time_text}{login_status}".ljust(42),
                    NoEnter=True,
                    Time=False,
                    Number=num,
                )
            else:
                time_print(
                    f"{time_text}{login_status}".ljust(42),
                    Top=True,
                    NoEnter=True,
                    Time=False,
                    Number=num,
                )
        login_status_change = login_status
        if status == 86038:
            time_print(
                "",
                Time=False,
            )
            return status, refresh_token, upward
        elif status == 0:
            time_print(
                "",
                Time=False,
            )
            cookie["buvid3"] = buvid3_and_bnut.get("buvid3", "")
            cookie["b_nut"] = buvid3_and_bnut.get("b_nut", "")
            return cookie, refresh_token, upward
        time.sleep(1)


# 保存哔哩哔哩登陆成功后的cookies模块
def save_bilibili_cookies(retry=False):
    bilibili_cookie, refresh_token, upward = bilibili_login(retry)
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


# 生成CorrespondPath模块（使用纯 Python SHA256-OAEP + RSA）
def getCorrespondPath(ts, key_pem):
    data = f"refresh_{ts}".encode()
    encrypted = rsa_encrypt_oaep_sha256(data, key_pem)
    return binascii.b2a_hex(encrypted).decode()


def bilibili_cookie_update_data(
    bilibili_cookie, new_bilibili_cookie, bilibili_data, new_refresh_token
):
    new_bilibili_cookie["buvid3"] = bilibili_cookie.get("buvid3", "")
    new_bilibili_cookie["b_nut"] = bilibili_cookie.get("b_nut", "")
    bilibili_data["cookie"] = new_bilibili_cookie
    bilibili_data["refresh_token"] = new_refresh_token
    bulid_netscape("yt_dlp_bilibili", new_bilibili_cookie)
    return bilibili_data


# 哔哩哔哩cookie刷新模块
def bilibili_cookie_update(bilibili_data):
    bilibili_cookie = bilibili_data["cookie"]

    # B站公钥（PEM）
    key_pem = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----"""

    # 获取当前时间戳
    ts = time_stamp()
    # 获取refresh_csrf
    refresh_csrf_response = http_client(
        f"https://www.bilibili.com/correspond/1/{getCorrespondPath(ts, key_pem)}",
        "获取refresh_csrf",
        3,
        5,
        True,
        bilibili_cookie,
    )
    if not refresh_csrf_response:
        return {"cookie": None}
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
    if update_cookie_response.json().get("code") != 0:
        return {"cookie": None}
    new_bilibili_cookie = requests.utils.dict_from_cookiejar(
        update_cookie_response.cookies
    )
    new_refresh_token = update_cookie_response.json().get("data", {}).get(
        "refresh_token"
    )
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
    if confirm_cookie_response.json().get("code") == 0:
        return bilibili_cookie_update_data(
            bilibili_cookie,
            new_bilibili_cookie,
            bilibili_data,
            new_refresh_token,
        )
    else:
        return {"cookie": None}


def get_bilibili_data_success(bilibili_data, channelid_bilibili_ids):
    time_print("BiliBili \033[32m获取cookie成功\033[0m")
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
                time_print("BiliBili \033[31m未登陆\033[0m")
                bilibili_data, upward = save_bilibili_cookies()
            else:
                time_print(
                    f"BiliBili \033[31m未登陆, 重试第\033[0m{try_num}\033[31m次\033[0m",
                    Head=f"\033[{upward + 3}F\033[{upward + 3}K",
                    Number=-4,
                )
                bilibili_data, upward = save_bilibili_cookies(True)
            try_num += 1
        else:
            time_print("BiliBili \033[33m需刷新\033[0m")
            bilibili_data = bilibili_cookie_update(bilibili_data)
            if bilibili_data.get("cookie"):
                time_print("BiliBili \033[32m刷新成功\033[0m")
            else:
                time_print("BiliBili \033[31m刷新失败, 重新登陆\033[0m")
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
    time_print("BiliBili \033[33m获取cookie成功\033[0m")
    if not os.path.isfile("channel_data/yt_dlp_bilibili.txt"):
        bulid_netscape("yt_dlp_bilibili", bilibili_data["cookie"])
    return channelid_bilibili_ids, bilibili_data
