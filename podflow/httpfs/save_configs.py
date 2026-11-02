# podflow/httpfs/save_configs.py
# coding: utf-8


from podflow import config_desc
from podflow.basic.file_save import file_save


def build_mod(website):
    mod = {}
    if website == "main":
        channel_mod = config_desc["main"]
    else:
        channel_mod = config_desc["channel"][website]
    for key_mod, value_mod in channel_mod.items():
        if key_mod not in ["title", "id"]:
            mod[key_mod] = value_mod["default"]
    return mod


def format_config(configs, channel_mod):
    new_config = {}
    for channel, config in configs.items():
        new_config[channel] = {
            "id": config["id"],
            "title": config["title"],
        }
        for key_mod, value_mod in channel_mod.items():
            if key_mod in config and config[key_mod] != value_mod:
                new_config[channel][key_mod] = config[key_mod]
        if "AllPartGet" in config and config["AllPartGet"] and config["update_size"] > 5:
            new_config[channel].pop("AllPartGet")
        if "title_change" in config and "table" in config["title_change"]:
            new_config[channel]["title_change"].pop("table")
        if (
            set(new_config[channel].keys()) == {"title", "id"}
            and channel == new_config[channel]["title"]
        ):
            new_config[channel] = new_config[channel]["id"]
        if "title" in new_config[channel] and new_config[channel]["title"] == channel:
            new_config[channel].pop("title")
    return new_config


def save_configs(config, config_file):
    youtube_mod = build_mod("youtube")
    bilibili_mod = build_mod("bilibili")
    main_mod = build_mod("main")
    new_config = {}
    for key_mod, value_mod in main_mod.items():
        if key_mod in config and config[key_mod] != value_mod:
            new_config[key_mod] = config[key_mod]
    new_config["channelid_youtube"] = format_config(
        config["channelid_youtube"], youtube_mod
    )
    new_config["channelid_bilibili"] = format_config(
        config["channelid_bilibili"], bilibili_mod
    )
    file_save(new_config, config_file)
