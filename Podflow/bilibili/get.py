# podflow/bilibili/get.py
# coding: utf-8

import contextlib
import re
import json
import math
import time
import urllib
import threading
from hashlib import md5
from functools import reduce
from podflow import gVar
from podflow.basic.http_client import http_client
from podflow.basic.get_file_list import get_file_list
from podflow.basic.list_merge_tidy import list_merge_tidy


# WBI签名模块
def WBI_signature(params={}, img_key="", sub_key=""):
    mixinKeyEncTab = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52,
    ]

    def getMixinKey(orig: str):
        "对 imgKey 和 subKey 进行字符顺序打乱编码"
        return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, "")[:32]

    def encWbi(params: dict, img_key: str, sub_key: str):
        "为请求参数进行 wbi 签名"
        mixin_key = getMixinKey(img_key + sub_key)
        curr_time = round(time.time())
        params["wts"] = curr_time  # 添加 wts 字段
        params = dict(sorted(params.items()))  # 按照 key 重排参数
        # 过滤 value 中的 "!'()*" 字符
        params = {
            k: "".join(filter(lambda chr: chr not in "!'()*", str(v)))
            for k, v in params.items()
        }
        query = urllib.parse.urlencode(params)  # 序列化参数
        wbi_sign = md5((query + mixin_key).encode()).hexdigest()  # 计算 w_rid
        params["w_rid"] = wbi_sign
        return params

    return encWbi(params=params, img_key=img_key, sub_key=sub_key)


# 获取bv的cid(包含分P或互动视频)模块
def get_bilibili_cid(bvid, bilibili_value):
    bvid_part = []  # 用于存储每个分P或互动视频的信息
    bvid_cid = []  # 存储已经获取的cid
    bvid_cid_choices = []  # 存储互动视频的选择
    code_num = {
        0: "成功",
        -400: "请求错误",
        -403: "权限不足",
        -404: "无视频",
        62002: "稿件不可见",
        62004: "稿件审核中",
        62012: "仅UP主自己可见",
    }

    # 获取互动视频信息模块
    def get_edge_info(bvid, bilibili_value, graph_version, edge_id):
        if edgeinfo_v2_response := http_client(
            "https://api.bilibili.com/x/stein/edgeinfo_v2",
            f"{bilibili_value}|{bvid}",
            10,
            4,
            True,
            None,
            {"bvid": bvid, "graph_version": graph_version, "edge_id": edge_id},
        ):
            edgeinfo_v2 = edgeinfo_v2_response.json()
            return edgeinfo_v2["data"]

    # 获取选择项信息模块
    def get_choices(data):
        options = []
        options_cid = []
        if "questions" in data["edges"]:
            for question in data["edges"]["questions"]:
                if "choices" in question:
                    for choice in question["choices"]:
                        if (
                            choice["cid"] not in bvid_cid
                            and choice["cid"] not in bvid_cid_choices
                        ):
                            bvid_cid_choices.append(
                                {
                                    "cid": choice["cid"],
                                    "edge_id": choice["id"],
                                    "option": choice["option"],
                                }
                            )
                            options.append(choice["option"])
                            options_cid.append(choice["cid"])
        return options, options_cid

    # 获取剧情图id模块
    def get_graph_version(bvid, bilibili_value, cid):
        graph_version = ""
        if playerwbi_response := http_client(
            "https://api.bilibili.com/x/player/wbi/v2",
            f"{bilibili_value}|{bvid}",
            10,
            4,
            True,
            None,
            {"cid": cid, "bvid": bvid},
        ):
            playerwbi = playerwbi_response.json()
            playerwbi_data = playerwbi["data"]
            if "interaction" in playerwbi_data:
                graph_version = playerwbi["data"]["interaction"]["graph_version"]
        return graph_version

    # 判断媒体类型
    if interface_response := http_client(
        "https://api.bilibili.com/x/web-interface/wbi/view",
        f"{bilibili_value}|{bvid}",
        10,
        4,
        True,
        gVar.bilibili_data["cookie"],
        {"bvid": bvid},
    ):
        interface_json = interface_response.json()
        code = interface_json["code"]
        if code != 0:
            error = code_num[code]
            return error, "error", None
        data = interface_json["data"]
        upower = data["is_upower_exclusive"]
        pages = data["pages"]
        cid = data["cid"]
        if len(pages) > 1:
            for part in pages:
                bvid_part.append(
                    {
                        "cid": part["cid"],
                        "page": part["page"],
                        "part": part["part"],
                        "duration": part["duration"],
                        "dimension": part["dimension"],
                        "first_frame": part["first_frame"],
                    }
                )
            bvid_part.sort(key=lambda x: x["page"], reverse=True)
            return bvid_part, "part", upower
        elif data["rights"]["is_stein_gate"]:
            # 获取互动视频信息
            if graph_version := get_graph_version(bvid, bilibili_value, cid):
                data_1 = get_edge_info(bvid, bilibili_value, graph_version, "1")
                for story_list in data_1["story_list"]:
                    if story_list["edge_id"] == 1:
                        story_list_1 = story_list
                        break
                options, options_cid = get_choices(data_1)
                bvid_part.append(
                    {
                        "cid": story_list_1["cid"],
                        "title": data_1["title"],
                        "edge_id": story_list_1["edge_id"],
                        "first_frame": f"http://i0.hdslb.com/bfs/steins-gate/{story_list_1['cid']}_screenshot.jpg",
                        "options": options,
                        "options_cid": options_cid,
                        "num": 1,
                    }
                )
                bvid_cid.append(story_list_1["cid"])
                while bvid_cid_choices:
                    if bvid_cid_choices[0]["cid"] not in bvid_cid:
                        data = get_edge_info(
                            bvid,
                            bilibili_value,
                            graph_version,
                            bvid_cid_choices[0]["edge_id"],
                        )
                        options, options_cid = get_choices(data)
                        bvid_part.append(
                            {
                                "cid": bvid_cid_choices[0]["cid"],
                                "title": data["title"],
                                "edge_id": bvid_cid_choices[0]["edge_id"],
                                "first_frame": f"http://i0.hdslb.com/bfs/steins-gate/{bvid_cid_choices[0]['cid']}_screenshot.jpg",
                                "options": options,
                                "options_cid": options_cid,
                                "num": len(bvid_part) + 1,
                            }
                        )
                        bvid_cid.append(bvid_cid_choices[0]["cid"])
                    del bvid_cid_choices[0]
                bvid_part.sort(key=lambda x: x["num"], reverse=True)
                return bvid_part, "edgeinfo", upower
            else:
                return None, None, None
        else:
            return cid, "cid", upower
    else:
        return None, None, None


# 查询哔哩哔哩用户投稿视频明细模块
def get_bilibili_vlist(bilibili_key, bilibili_value, num=1, all_part_judgement=False):
    bilibili_list = []
    bilibili_entry = {}
    if bilibili_response := http_client(
        "https://api.bilibili.com/x/space/wbi/arc/search",
        bilibili_value,
        10,
        4,
        True,
        gVar.bilibili_data["cookie"],
        WBI_signature(
            {
                "mid": bilibili_key,
                "pn": str(num),
                "ps": "25",
            },
            gVar.bilibili_data["img_key"],
            gVar.bilibili_data["sub_key"],
        ),
    ):
        bilibili_json = bilibili_response.json()
        bilibili_vlists = bilibili_json["data"]["list"]["vlist"]
        for vlist in bilibili_vlists:
            with contextlib.suppress(KeyError, TypeError, IndexError, ValueError):
                bilibili_entry[vlist["bvid"]] = {
                    "aid": vlist["aid"],
                    "author": vlist["author"],
                    "bvid": vlist["bvid"],
                    "copyright": vlist["copyright"],
                    "created": vlist["created"],
                    "description": vlist["description"],
                    "is_union_video": vlist["is_union_video"],
                    "length": vlist["length"],
                    "mid": vlist["mid"],
                    "pic": vlist["pic"],
                    "title": vlist["title"],
                    "typeid": vlist["typeid"],
                }
                bilibili_list.append(vlist["bvid"])
    if all_part_judgement and bilibili_list:

        def all_part(bvid):
            bvid_cid, bvid_type, power = get_bilibili_cid(bvid, bilibili_value)
            if bvid_type:
                bilibili_entry[bvid][bvid_type] = bvid_cid
                bilibili_entry[bvid]["power"] = power

        # 创建一个线程列表
        threads = []
        for bvid in bilibili_list:
            thread = threading.Thread(target=all_part, args=(bvid,))
            threads.append(thread)
            thread.start()
        # 等待所有线程完成
        for thread in threads:
            thread.join()
    return bilibili_entry, bilibili_list


# 更新哔哩哔哩频道json模块
def bilibili_json_update(bilibili_key, bilibili_value):
    bilibili_space = {}
    bilibili_lists = []
    bilibili_entrys = {}
    if not (
        bilibili_card_response := http_client(
            "https://api.bilibili.com/x/web-interface/card",
            bilibili_value,
            10,
            4,
            True,
            gVar.bilibili_data["cookie"],
            {
                "mid": bilibili_key,
                "photo": "true",
            },
        )
    ):
        return None
    bilibili_card_json = bilibili_card_response.json()
    with contextlib.suppress(KeyError, TypeError, IndexError, ValueError):
        if bilibili_card_json["code"] == 0:
            bilibili_space = {
                "mid": bilibili_card_json["data"]["card"]["mid"],
                "name": bilibili_card_json["data"]["card"]["name"],
                "sex": bilibili_card_json["data"]["card"]["sex"],
                "face": bilibili_card_json["data"]["card"]["face"],
                "spacesta": bilibili_card_json["data"]["card"]["spacesta"],
                "sign": bilibili_card_json["data"]["card"]["sign"],
                "Official": bilibili_card_json["data"]["card"]["Official"],
                "official_verify": bilibili_card_json["data"]["card"][
                    "official_verify"
                ],
            }
        else:
            return bilibili_card_json["code"]
    # 查询哔哩哔哩用户投稿视频明细
    for num in range(math.ceil(gVar.channelid_bilibili[bilibili_value]["update_size"] / 25)):
        num += 1
        bilibili_entry, bilibili_list = get_bilibili_vlist(
            bilibili_key,
            f"{bilibili_value}第{num}页",
            num,
            gVar.channelid_bilibili[bilibili_value]["AllPartGet"],
        )
        bilibili_entrys = bilibili_entrys | bilibili_entry
        bilibili_lists += bilibili_list
    bilibili_space["entry"] = bilibili_entrys
    bilibili_space["list"] = bilibili_lists
    return bilibili_space


# 更新哔哩哔哩频道xml模块
def bilibili_rss_update(bilibili_key, bilibili_value):
    # 获取已下载文件列表
    bilibili_content_bvid_original = get_file_list(
        bilibili_key, gVar.channelid_bilibili[bilibili_value]["media"]
    )[0]
    # 获取原xml中文件列表
    try:
        original_item = gVar.xmls_original[bilibili_key]  # 尝试获取原始的xml内容
        guids = list_merge_tidy(
            re.findall(r"(?<=<guid>).+(?=</guid>)", original_item), [], 12
        )  # 从xml中提取guid
    except KeyError:
        guids = []  # 如果没有找到对应的key，则初始化guids为空列表
    bilibili_space = bilibili_json_update(
        bilibili_key, bilibili_value
    )  # 更新bilibili相关的json内容
    # 读取原哔哩哔哩频道xml文件并判断是否要更新
    try:
        with open(
            f"channel_id/{bilibili_key}.json",
            "r",
            encoding="utf-8",  # 打开指定的json文件
        ) as file:
            bilibili_space_original = json.load(file)  # 读取文件内容并解析成字典
    except FileNotFoundError:  # 捕获文件不存在异常
        bilibili_space_original = {}  # 如果文件不存在，初始化为空字典
    except json.decoder.JSONDecodeError:  # 捕获json解码错误
        bilibili_space_original = {}  # 如果json读取失败，初始化为空字典
    # 根据更新条件更新频道数据
    if bilibili_space == -404:  # 检查更新状态
        gVar.channelid_bilibili_rss[bilibili_key] = {
            "content": bilibili_space,
            "type": "int",
        }  # 设置为整型内容
    elif bilibili_space is None:
        gVar.channelid_bilibili_rss[bilibili_key] = {
            "content": bilibili_space_original,
            "type": "json",
        }  # 使用原始json内容
    else:
        gVar.channelid_bilibili_rss[bilibili_key] = {
            "content": bilibili_space,
            "type": "dict",
        }  # 设置为字典类型内容
        # 判断是否需要更新ID列表
        if bilibili_space != bilibili_space_original:
            gVar.channelid_bilibili_ids_update[bilibili_key] = bilibili_value  # 更新ID
        # 获取需要更新的内容列表
        bilibili_content_bvid = bilibili_space["list"][
            : gVar.channelid_bilibili[bilibili_value]["update_size"]
        ]
        bilibili_space_new = list_merge_tidy(
            bilibili_content_bvid, guids
        )  # 合并新内容和原内容
        # 检查内容是否有变动
        if bilibili_content_bvid := [
            exclude
            for exclude in bilibili_content_bvid
            if exclude not in bilibili_content_bvid_original  # 筛选新增的内容
        ]:
            gVar.channelid_bilibili_ids_update[bilibili_key] = bilibili_value  # 需要更新ID
            gVar.bilibili_content_bvid_update[bilibili_key] = (
                bilibili_content_bvid  # 更新新增内容
            )
        # 向后更新
        if (
            gVar.channelid_bilibili[bilibili_value]["BackwardUpdate"] and guids
        ):  # 如果设置了向后更新
            backward_update_size = gVar.channelid_bilibili[bilibili_value][
                "last_size"
            ] - len(bilibili_space_new)  # 计算需要向后更新的数量
            if backward_update_size > 0:
                backward_update_size = min(
                    backward_update_size,
                    gVar.channelid_bilibili[bilibili_value]["BackwardUpdate_size"],
                )  # 限制更新数量
                backward_update_page_start = math.ceil(
                    len(bilibili_space_new) / 25
                )  # 确定开始页面
                backward_update_page_end = math.ceil(
                    (len(bilibili_space_new) + backward_update_size) / 25
                )  # 确定结束页面
                backward_entry = {}  # 初始化向后更新的条目
                backward_list = []  # 初始化向后更新的列表
                # 循环更新每一页的内容
                for num in range(
                    backward_update_page_start, backward_update_page_end + 1
                ):
                    backward_entry_part, backward_list_part = get_bilibili_vlist(
                        bilibili_key, bilibili_value, num
                    )  # 获取具体内容
                    backward_entry = backward_entry | backward_entry_part  # 合并条目
                    backward_list += backward_list_part  # 合并列表
                # 检查条目和列表是否有效
                if backward_entry and backward_list and guids[-1] in backward_list:
                    try:
                        backward_list_start = (
                            backward_list.index(guids[-1]) + 1
                        )  # 获取guids的起始索引
                        backward_list = backward_list[backward_list_start:][
                            :backward_update_size
                        ]  # 更新向后列表
                    except ValueError:
                        backward_list = []  # 如果没有找到，清空列表
                    # 根据条件移除已经存在的元素
                    for guid in backward_list.copy():
                        if guid in bilibili_space_new:
                            backward_list.remove(guid)  # 移除已存在的条目
                    # 如果有向后条目需要更新
                    if backward_list:
                        if gVar.channelid_bilibili[bilibili_value][
                            "AllPartGet"
                        ]:  # 如果需要获取所有部分

                            def backward_all_part(guid):
                                guid_cid, guid_type, power = get_bilibili_cid(
                                    guid, bilibili_value
                                )
                                if guid_type:
                                    backward_entry[guid][guid_type] = guid_cid
                                    backward_entry[guid]["power"] = power

                            # 创建一个线程列表
                            threads = []
                            for guid in backward_list:
                                thread = threading.Thread(
                                    target=backward_all_part, args=(guid,)
                                )  # 为每个条目创建线程
                                threads.append(thread)  # 添加线程到列表
                                thread.start()  # 启动线程
                            # 等待所有线程完成
                            for thread in threads:
                                thread.join()
                        # 更新频道信息
                        gVar.channelid_bilibili_rss[bilibili_key].update(
                            {
                                "backward": {
                                    "list": backward_list,
                                    "entry": backward_entry,
                                }
                            }
                        )
                        gVar.channelid_bilibili_ids_update[bilibili_key] = (
                            bilibili_value  # 标记ID更新
                        )
                        bilibili_content_bvid_backward = []  # 初始化向后更新的内容列表
                        for guid in backward_list:
                            if (
                                guid not in bilibili_content_bvid_original
                            ):  # 检查新增的内容
                                bilibili_content_bvid_backward.append(
                                    guid
                                )  # 添加到向后更新列表
                        if bilibili_content_bvid_backward:
                            gVar.bilibili_content_bvid_backward_update[bilibili_key] = (
                                bilibili_content_bvid_backward  # 更新最终的向后更新内容
                            )
