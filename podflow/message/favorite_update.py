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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
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
    gVar.favorite_update_skip_wait.clear()
    gVar.favorite_update_active = True
    
    # 初始预估时间（不考虑网络耗时）
    gVar.favorite_update_next_run = time.time() + (times * 600)

    try:
        while num < times:
            # 1. 首次跳过，后续先进行网络请求
            if num > 0:
                for channel_id, channel_value in gVar.channelid_youtube.items():
                    if channel_value.get("Favorite"):
                        updated, error = check_xml_update(channel_value["id"])
                        if error:
                            write_log(f"特别关注获取失败：{error}")
                        elif updated:
                            write_log(f"特别关注存在更新：{channel_id}")
                            return

                # 2. 网络请求结束后，使用剩余次数 (times - num) * 600 秒修正预计完成时间
                gVar.favorite_update_next_run = time.time() + (times - num) * 600

            # 3. 每一轮（包含最后一轮）都固定等待 600 秒
            if gVar.favorite_update_skip_wait.wait(timeout=600):
                write_log("已跳过等待，立即开始下一次更新")
                return

            num += 1

        write_log("倒计时结束")
    finally:
        gVar.favorite_update_active = False
        gVar.favorite_update_next_run = None
