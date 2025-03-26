# podflow/config/build_original.py
# coding: utf-8

from podflow import gVar, parse
from podflow.config.get_config import get_config
from podflow.basic.folder_build import folder_build
from podflow.config.get_channelid import get_channelid
from podflow.config.correct_config import correct_config
from podflow.config.get_channelid_id import get_channelid_id
from podflow.config.correct_channelid import correct_channelid


def build_original():
    # 获取配置文件config
    gVar.config = get_config(parse.config)
    # 纠正配置信息config
    correct_config()
    # 从配置文件中获取YouTube的频道
    gVar.channelid_youtube = get_channelid("youtube")
    # 从配置文件中获取哔哩哔哩的频道
    gVar.channelid_bilibili = get_channelid("bilibili")
    # 构建文件夹channel_id
    folder_build("channel_id")
    # 构建文件夹channel_audiovisual
    folder_build("channel_audiovisual")
    # 构建文件夹channel_rss
    folder_build("channel_rss")
    # 构建文件夹channel_data
    folder_build("channel_data")
    # 修正channelid_youtube
    gVar.channelid_youtube = correct_channelid(gVar.channelid_youtube, "youtube")
    # 修正channelid_bilibili
    gVar.channelid_bilibili = correct_channelid(gVar.channelid_bilibili, "bilibili")
    # 读取youtube频道的id
    gVar.channelid_youtube_ids = get_channelid_id(gVar.channelid_youtube, "youtube")
    # 复制youtube频道id用于删除已抛弃的媒体文件夹
    gVar.channelid_youtube_ids_original = gVar.channelid_youtube_ids.copy()
    # 读取bilibili频道的id
    gVar.channelid_bilibili_ids = get_channelid_id(gVar.channelid_bilibili, "bilibili")
    # 复制bilibili频道id用于删除已抛弃的媒体文件夹
    gVar.channelid_bilibili_ids_original = gVar.channelid_bilibili_ids.copy()
