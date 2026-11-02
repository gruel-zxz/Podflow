# podflow/message/normalize_video_url.py
# coding: utf-8

import re
from urllib.parse import parse_qs, urlparse
from podflow.basic.http_client import http_client


def normalize_video_url(url: str, resolve_shortlink: bool = True) -> str:
    if not url or not isinstance(url, str):
        return "", None

    url = url.strip()

    # ------------------------------------------------------------------
    # 0. 处理需要网络请求解析的短链接 (如 b23.tv/gOgWMUN)
    # ------------------------------------------------------------------
    if resolve_shortlink and "b23.tv" in url and not re.search(r"BV[a-zA-Z0-9]{10}", url, re.IGNORECASE):
        target_url = url if url.startswith(("http://", "https://")) else "https://" + url
        
        # 调用项目的 http_client 发起请求
        response = http_client(
            url=target_url,
            name="短链解析",
            headers_possess=True,
            mode="get"
        )
        
        # 请求成功后提取重定向后的最终地址 (response.url)
        if response is not None and hasattr(response, "url"):
            url = response.url

    # ------------------------------------------------------------------
    # 1. 处理 Bilibili 链接
    # ------------------------------------------------------------------
    # 匹配 BV 号 (如 BV16Pau6VErn)
    bv_match = re.search(r"(BV[a-zA-Z0-9]{10})", url, re.IGNORECASE)
    if bv_match:
        bv_id = bv_match.group(1)
        # 确保 BV 两个字母大写
        bv_id = "BV" + bv_id[2:]
        return f"https://www.bilibili.com/video/{bv_id}/", bv_id

    # 匹配 av 号 (如 av170001)
    av_match = re.search(r"(av\d+)", url, re.IGNORECASE)
    if av_match:
        av_id = av_match.group(1).lower()
        return f"https://www.bilibili.com/video/{av_id}/", av_id

    # ------------------------------------------------------------------
    # 2. 处理 YouTube 链接
    # ------------------------------------------------------------------
    parsed = urlparse(url)
    hostname = parsed.netloc.lower()

    if "youtube.com" in hostname or "youtu.be" in hostname:
        video_id = None

        # 短链接 (youtu.be/<VIDEO_ID>)
        if "youtu.be" in hostname:
            video_id = parsed.path.lstrip("/").split("/")[0]
        else:
            # 标准/移动端链接 (?v=<VIDEO_ID>)
            query_params = parse_qs(parsed.query)
            if "v" in query_params:
                video_id = query_params["v"][0]
            # 路径链接 (/embed/, /shorts/, /v/)
            elif parsed.path:
                path_parts = [p for p in parsed.path.split("/") if p]
                if path_parts and path_parts[0] in ["embed", "v", "shorts"]:
                    if len(path_parts) > 1:
                        video_id = path_parts[1]

        if video_id:
            video_id = video_id.split("?")[0].split("&")[0]
            return f"https://www.youtube.com/watch?v={video_id}", video_id

    return url, None
