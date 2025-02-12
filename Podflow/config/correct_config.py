# Podflow/config/correct_config.py
# coding: utf-8

import re
from Podflow import gVar, default_config, parse


# 纠正配置信息config模块
def correct_config():
    config = gVar.config
    # 对completion_count进行纠正
    if (
        "completion_count" not in config
        or not isinstance(config["completion_count"], int)
        or config["completion_count"] < 0
    ):
        config["completion_count"] = default_config["completion_count"]
    # 对preparation_per_count进行纠正
    if (
        "preparation_per_count" not in config
        or not isinstance(config["preparation_per_count"], int)
        or config["preparation_per_count"] <= 0
    ):
        config["preparation_per_count"] = default_config["preparation_per_count"]
    # 对retry_count进行纠正
    if (
        "retry_count" not in config
        or not isinstance(config["retry_count"], int)
        or config["retry_count"] <= 0
    ):
        config["retry_count"] = default_config["retry_count"]
    # 对url进行纠正
    match_url = re.search(r"^(https?|ftp)://([^/\s:]+)", config["url"])
    if "url" in config and match_url:
        config["url"] = match_url.group()
    else:
        config["url"] = default_config["url"]
    # 对port进行纠正
    if (
        "port" not in config
        or not isinstance(config["port"], int)
        or config["port"] < 0
        or config["port"] > 65535
    ):
        config["port"] = default_config["port"]
    # 对port_in_url进行纠正
    if "port_in_url" not in config or not isinstance(config["port_in_url"], bool):
        config["port_in_url"] = default_config["port_in_url"]
    # 合并地址和端口
    if config["port_in_url"]:
        config["address"] = f"{config['url']}:{config['port']}"
    else:
        config["address"] = config["url"]
    # 对httpfs进行纠正
    if "httpfs" not in config or not isinstance(config["httpfs"], bool):
        config["httpfs"] = default_config["httpfs"]
    # 对title进行纠正
    if "title" not in config:
        config["title"] = default_config["title"]
    # 对filename进行纠正
    if "filename" not in config:
        config["filename"] = default_config["filename"]
    # 对link进行纠正
    if "link" not in config or not re.search(
        r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", config["link"]
    ):
        config["link"] = default_config["link"]
    # 对description进行纠正
    if "description" not in config:
        config["description"] = default_config["description"]
    # 对icon进行纠正
    if "icon" not in config or not re.search(
        r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", config["icon"]
    ):
        config["icon"] = default_config["icon"]
    # 对category进行纠正
    if "category" not in config:
        config["category"] = default_config["category"]
    # 对IOS中shortcuts自动关注进行纠正
    if (
        f"{config['address']}/{config['filename']}.xml"
        not in parse.shortcuts_url_original
    ):
        gVar.shortcuts_url[f"{config['filename']}(Main RSS)"] = (
            f"{config['address']}/{config['filename']}.xml"
        )
    # 对token进行纠正
    if "token" not in config:
        config["token"] = default_config["token"]
    if config["token"] in [None, ""]:
        config["token"] = ""
    else:
        config["token"] = str(config["token"])
    # 对delete_incompletement进行纠正
    if "delete_incompletement" not in config or not isinstance(
        config["delete_incompletement"], bool
    ):
        config["delete_incompletement"] = default_config["delete_incompletement"]
    # 对remove_media进行纠正
    if "remove_media" not in config or not isinstance(
        config["remove_media"], bool
    ):
        config["remove_media"] = default_config["remove_media"]
    # 对upload进行纠正
    if "upload" not in config or not isinstance(
        config["upload"], bool
    ):
        config["upload"] = default_config["upload"]
