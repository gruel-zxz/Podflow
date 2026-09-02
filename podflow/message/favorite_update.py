# podflow/message/favorite_update.py
# coding: utf-8

import os
import math
import time
import requests
import xml.etree.ElementTree as ET
from podflow import gVar
from podflow.basic.write_log import write_log


def check_xml_update(channel_id):
    # ---------- 检查本地文件 ----------
    xml_file = os.path.join("channel_id", f"{channel_id}.txt")
    if not os.path.exists(xml_file):
        return False, f"本地XML不存在：{xml_file}"

    try:
        with open(xml_file, "r", encoding="utf-8") as f:
            local_xml = f.read()
        local_root = ET.fromstring(local_xml)
        local_entry = local_root.find("{http://www.w3.org/2005/Atom}entry")
        if local_entry is None:
            return False, "本地XML缺少 <entry> 节点"
        local_pub = local_entry.find("{http://www.w3.org/2005/Atom}published")
        if local_pub is None:
            return False, "本地XML缺少 <published> 节点"
        old_pub = local_pub.text.strip()
    except Exception as e:
        return False, f"解析本地XML失败：{e}"

    # ---------- 获取网络 XML ----------
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()  # 自动判定非 200 的 HTTP 错误状态码
    except requests.exceptions.Timeout:
        return False, "获取RSS失败：网络连接超时（请检查代理或网络状况）"
    except requests.exceptions.ProxyError:
        return False, "获取RSS失败：代理服务器连接异常"
    except requests.exceptions.SSLError:
        return False, "获取RSS失败：SSL证书验证失败"
    except requests.exceptions.ConnectionError:
        # 捕获网络不可达、连接被拒绝、DNS解析失败等连接错误
        return False, "获取RSS失败：无法连接至 YouTube（请检查网络连接或代理软件）"
    except requests.exceptions.HTTPError as e:
        return False, f"获取RSS失败：HTTP响应异常（状态码：{r.status_code}）"
    except requests.exceptions.RequestException as e:
        return False, f"获取RSS失败：{e}"

    # ---------- 解析网络 XML ----------
    try:
        remote_root = ET.fromstring(r.text)
        remote_entry = remote_root.find("{http://www.w3.org/2005/Atom}entry")
        if remote_entry is None:
            return False, "网络XML缺少 <entry> 节点"
        remote_pub = remote_entry.find("{http://www.w3.org/2005/Atom}published")
        if remote_pub is None:
            return False, "网络XML缺少 <published> 节点"
        new_pub = remote_pub.text.strip()
    except Exception as e:
        return False, f"解析网络XML失败：{e}"

    return old_pub != new_pub, None


def favorite_update(time_delay):
    num = 0
    times = math.ceil(time_delay / 600)
    while num < times:
        time.sleep(600)
        for channel_id, channel_value in gVar.channelid_youtube.items():
            if channel_value["Favorite"]:
                updated, error= check_xml_update(channel_value["id"])
                if error:
                    write_log(f"特别关注获取失败：{error}")
                elif updated:
                    write_log(f"特别关注存在更新：{channel_id}")
                    return
        num += 1
    write_log(f"倒计时结束")
