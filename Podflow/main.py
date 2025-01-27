# Podflow/main.py
# coding: utf-8

import sys
import json
import time
import urllib
import subprocess
from datetime import datetime
from importlib.metadata import version
import cherrypy

# 基本功能模块
from Podflow import gVar, parse
from Podflow.parse_arguments import parse_arguments
from Podflow.basic.file_save import file_save
from Podflow.basic.qr_code import qr_code
from Podflow.basic.write_log import write_log
from Podflow.basic.split_dict import split_dict

# 网络和 HTTP 模块
from Podflow.httpfs.port_judge import port_judge
from Podflow.httpfs.app_bottle import bottle_app_instance

# 下载和视频处理模块
from Podflow.download.delete_part import delete_part
from Podflow.download.youtube_and_bilibili_download import youtube_and_bilibili_download
from Podflow.ffmpeg_judge import ffmpeg_judge

# RSS 和消息处理模块
from Podflow.message.xml_rss import xml_rss
from Podflow.message.backup_zip_save import backup_zip_save
from Podflow.message.create_main_rss import create_main_rss
from Podflow.message.get_original_rss import get_original_rss
from Podflow.message.original_rss_fail_print import original_rss_fail_print
from Podflow.message.update_information_display import update_information_display
from Podflow.message.update_youtube_bilibili_rss import update_youtube_bilibili_rss
from Podflow.message.get_video_format import get_video_format

# 登录模块
from Podflow.bilibili.login import get_bilibili_data
from Podflow.youtube.login import get_youtube_cookie

# 配置和图标模块
from Podflow.config.channge_icon import channge_icon
from Podflow.config.build_original import build_original

# 制作和修改文件模块
from Podflow.makeup.make_up_file import make_up_file
from Podflow.makeup.make_up_file_mod import make_up_file_mod
from Podflow.makeup.make_up_file_format_mod import make_up_file_format_mod
from Podflow.makeup.del_makeup_yt_format_fail import del_makeup_yt_format_fail

# 移除模块
from Podflow.remove.remove_file import remove_file
from Podflow.remove.remove_dir import remove_dir

# 处理 YouTube 信息模块
from Podflow.youtube.build import get_youtube_introduction


def main():
    # 获取传入的参数
    parse_arguments()
    # 开始运行
    print(f"{datetime.now().strftime('%H:%M:%S')}|Podflow|{version('Podflow')}开始运行.....")
    # 判断是否安装ffmpeg
    ffmpeg_judge()
    # 初始化
    build_original()
    # http共享
    port = gVar.config["port"]
    host = "0.0.0.0"
    if port_judge(host, port):
        # 启动 CherryPy 服务器
        cherrypy.tree.graft(
            bottle_app_instance.app_bottle
        )  # 将 Bottle 应用嵌入到 CherryPy 中
        cherrypy.config.update(
            {
                "global": {
                    "tools.sessions.on": True,  # 启用会话支持
                    "server.socket_host": host,  # 监听所有 IP 地址
                    "server.socket_port": port,  # 设置监听端口
                    "log.screen": False,  # 禁用屏幕日志输出
                    "log.access_file": "",  # 关闭访问日志
                    "log.error_file": "",  # 关闭错误日志
                }
            }
        )
        cherrypy.engine.start()  # 启动 CherryPy 服务器
        print(
            f"{datetime.now().strftime('%H:%M:%S')}|HTTP服务器启动, 端口: \033[32m{port}\033[0m"
        )
        if parse.httpfs:  # HttpFS参数判断, 是否继续运行
            cherrypy.engine.block()  # 阻止程序退出, 保持HTTP服务运行
    else:
        print(
            f"{datetime.now().strftime('%H:%M:%S')}|HTTP服务器端口: \033[32m{port}\033[0m, \033[31m被占用\033[0m"
        )
        if parse.httpfs:
            sys.exit(0)
    # 主流程
    while parse.update_num > 0 or parse.update_num == -1:  # 循环主更新
        # 暂停进程打印
        gVar.server_process_print_flag[0] = "pause"
        # 获取YouTube cookie
        gVar.youtube_cookie = get_youtube_cookie(gVar.channelid_youtube_ids_original)
        # 更新哔哩哔哩data
        gVar.channelid_bilibili_ids, gVar.bilibili_data = get_bilibili_data(
            gVar.channelid_bilibili_ids_original
        )
        # 恢复进程打印
        bottle_app_instance.cherry_print()
        # 获取原始xml字典和rss文本
        gVar.xmls_original, gVar.hash_rss_original, gVar.xmls_original_fail = (
            get_original_rss()
        )
        # 更新Youtube和哔哩哔哩频道xml
        update_youtube_bilibili_rss()
        # 判断是否有更新内容
        if gVar.channelid_youtube_ids_update or gVar.channelid_bilibili_ids_update:
            gVar.update_generate_rss = True
        if gVar.update_generate_rss:
            # 根据日出日落修改封面(只适用原封面)
            channge_icon()
            # 输出需要更新的信息
            update_information_display(
                gVar.channelid_youtube_ids_update,
                gVar.youtube_content_ytid_update,
                gVar.youtube_content_ytid_backward_update,
                "YouTube",
            )
            update_information_display(
                gVar.channelid_bilibili_ids_update,
                gVar.bilibili_content_bvid_update,
                gVar.bilibili_content_bvid_backward_update,
                "BiliBili",
            )
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            # 获取视频格式信息
            get_video_format()
            # 恢复进程打印
            bottle_app_instance.cherry_print()
            # 删除中断下载的媒体文件
            if gVar.config["delete_incompletement"]:
                delete_part(gVar.channelid_youtube_ids | gVar.channelid_bilibili_ids)
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            # 下载YouTube和哔哩哔哩视频
            youtube_and_bilibili_download()
            # 恢复进程打印
            bottle_app_instance.cherry_print()
            # 打印无法保留原节目信息
            original_rss_fail_print(gVar.xmls_original_fail)
            # 获取YouTube频道简介
            get_youtube_introduction()
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            # 生成分和主rss
            create_main_rss()
            # 恢复进程打印
            bottle_app_instance.cherry_print()
            if gVar.config["remove_media"]:
                # 删除不在rss中的媒体文件
                remove_file()
                # 删除已抛弃的媒体文件夹
                remove_dir()
            # 补全缺失媒体文件到字典
            make_up_file()
            # 按参数获取需要补全的最大个数
            gVar.make_up_file_format = split_dict(
                gVar.make_up_file_format,
                gVar.config["completion_count"],
                True,
            )[0]
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            # 补全在rss中缺失的媒体格式信息
            make_up_file_format_mod()
            # 恢复进程打印
            bottle_app_instance.cherry_print()
            # 生成主rss
            overall_rss = xml_rss(
                gVar.config["title"],
                gVar.config["link"],
                gVar.config["description"],
                gVar.config["category"],
                gVar.config["icon"],
                "\n".join(gVar.all_items),
            )
            # 删除无法补全的媒体
            overall_rss = del_makeup_yt_format_fail(overall_rss)
            # 保存主rss
            file_save(overall_rss, f"{gVar.config['filename']}.xml")
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            address = gVar.config["address"]
            filename = gVar.config["filename"]
            if token := gVar.config["token"]:
                overall_url = f"{address}/{filename}.xml?token={token}"
            else:
                overall_url = f"{address}/{filename}.xml"
            write_log("总播客已更新", f"地址:\n\033[34m{overall_url}\033[0m")
            if "main" not in gVar.displayed_QRcode:
                qr_code(overall_url)
                gVar.displayed_QRcode.append("main")
            # 恢复进程打印
            bottle_app_instance.cherry_print()
            # 备份主rss
            backup_zip_save(overall_rss)
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            # 下载补全Youtube和哔哩哔哩视频模块
            make_up_file_mod()
            # 恢复进程打印
            bottle_app_instance.cherry_print()
        else:
            print(f"{datetime.now().strftime('%H:%M:%S')}|频道无更新内容")

        # 将需要更新转为否
        gVar.update_generate_rss = False
        if parse.update_num != -1:
            parse.update_num -= 1
        if parse.argument == "a-shell":
            openserver_process = subprocess.Popen(
                [
                    "open",
                    f"shortcuts://run-shortcut?name=Podflow&input=text&text={urllib.parse.quote(json.dumps(gVar.shortcuts_url))}",
                ]
            )
            # 延时
            time.sleep(60 + len(gVar.shortcuts_url) * 5)
            openserver_process.terminate()
            break
        elif parse.update_num == 0:
            break
        else:
            # 延时
            time.sleep(parse.time_delay)
    # 关闭CherryPy服务器
    cherrypy.engine.exit()
    print(f"{datetime.now().strftime('%H:%M:%S')}|Podflow运行结束")


if __name__ == "__main__":
    main()
