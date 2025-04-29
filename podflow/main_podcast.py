# podflow/main_podcast.py
# coding: utf-8

import sys
import json
import time
import urllib
import subprocess

import cherrypy

# 基本功能模块
from podflow import gVar, parse
from podflow.basic.split_dict import split_dict
from podflow.basic.time_print import time_print

# 网络和 HTTP 模块
from podflow.httpfs.browser import open_url
from podflow.httpfs.port_judge import port_judge
from podflow.httpfs.progress_bar import progress_update
from podflow.httpfs.app_bottle import bottle_app_instance

# 下载和视频处理模块
from podflow.ffmpeg_judge import ffmpeg_judge
from podflow.download.delete_part import delete_part
from podflow.download_and_build import download_and_build

# RSS 和消息处理模块
from podflow.message.save_rss import save_rss
from podflow.message.get_original_rss import get_original_rss
from podflow.message.get_video_format import get_video_format
from podflow.message.optimize_download import optimize_download
from podflow.message.original_rss_fail_print import original_rss_fail_print
from podflow.message.update_information_display import update_information_display
from podflow.message.update_youtube_bilibili_rss import update_youtube_bilibili_rss

# 登录模块
from podflow.bilibili.login import get_bilibili_data
from podflow.youtube.login import get_youtube_cookie

# 配置和图标模块
from podflow.config.channge_icon import channge_icon
from podflow.config.build_original import build_original

# 制作和修改文件模块
from podflow.makeup.make_up_file import make_up_file
from podflow.makeup.make_up_file_mod import make_up_file_mod
from podflow.makeup.del_makeup_format_fail import del_makeup_format_fail
from podflow.makeup.make_up_file_format_mod import make_up_file_format_mod

# 移除模块
from podflow.remove.remove_dir import remove_dir
from podflow.remove.remove_file import remove_file

# 处理 YouTube 信息模块
from podflow.youtube.build import print_fail_youtube

# 长期媒体进行上传模块
from podflow.upload.login import login_upload
from podflow.upload.add_upload import add_upload
from podflow.upload.update_upload import update_upload
from podflow.upload.linked_client import connect_upload_server
from podflow.upload.get_upload_original import get_upload_original


def main_podcast():
    # 判断是否安装ffmpeg
    ffmpeg_judge()
    # 初始化
    build_original()
    # http共享
    port = gVar.config.get("port", 8000) # 使用 .get 获取端口
    hostip = "0.0.0.0"

    if port_judge(hostip, port): # 假设 port_judge 存在
        # 设置路由 (确保此时 gVar.config 等已就绪)
        bottle_app_instance.setup_routes(upload=False) # 或者根据需要设置为 True

        # 设置logname
        bottle_app_instance.set_logname(
            logname="httpfs.log",
            http_fs=gVar.config.get("httpfs", False), # 使用 .get
        )

        # 启动 CherryPy 服务器
        cherrypy.tree.graft(
            bottle_app_instance.app_bottle
        )  # 将 Bottle 应用嵌入到 CherryPy 中
        cherrypy.config.update(
            {
                "global": {
                    "tools.sessions.on": True,  # 启用会话支持
                    "server.socket_host": hostip,  # 监听所有 IP 地址
                    "server.socket_port": port,  # 设置监听端口
                    "log.screen": False,  # 禁用屏幕日志输出
                    "log.access_file": "",  # 关闭访问日志
                    "log.error_file": "",  # 关闭错误日志
                    # 添加线程池配置，对于长连接 (SSE) 可能有帮助
                    'server.thread_pool': 30 # 示例值，根据需要调整
                }
            }
        )
        cherrypy.engine.start()  # 启动 CherryPy 服务器
        time_print(f"HTTP服务器启动, 端口: \033[32m{port}\033[0m")
        if parse.index:
            open_url(f"{gVar.config['address']}/index")
        if parse.httpfs:  # HttpFS参数判断, 是否继续运行
            cherrypy.engine.block()  # 阻止程序退出, 保持HTTP服务运行
            sys.exit(0)
    else:
        time_print(f"HTTP服务器端口: \033[32m{port}\033[0m, \033[31m被占用\033[0m")
        if parse.httpfs:
            sys.exit(0)
    # 主流程
    while parse.update_num > 0 or parse.update_num == -1:  # 循环主更新
        # 主进度条
        progress_update(0, refresh=1)
        # 暂停进程打印
        gVar.server_process_print_flag[0] = "pause"
        # 获取YouTube cookie
        gVar.youtube_cookie = get_youtube_cookie(gVar.channelid_youtube_ids_original)
        progress_update(0.01 ,num=0.0049)
        # 更新哔哩哔哩data
        gVar.channelid_bilibili_ids, gVar.bilibili_data = get_bilibili_data(
            gVar.channelid_bilibili_ids_original
        )
        progress_update(0.02, num=0.0049)
        # 恢复进程打印
        bottle_app_instance.cherry_print()
        # 获取原始xml字典和rss文本
        gVar.xmls_original, gVar.hash_rss_original, gVar.xmls_original_fail  = get_original_rss()
        progress_update(0.025, num=-0.0024)
        # 暂停进程打印
        gVar.server_process_print_flag[0] = "pause"
        # 连接上传服务器
        upload_url = connect_upload_server()
        progress_update(0.03, num=0.0024)
        # 恢复进程打印
        bottle_app_instance.cherry_print()
        # 登陆上传服务器
        if upload_url:
            upload_json = login_upload(upload_url)
            if upload_json:
                gVar.config["upload"] = False
        else:
            gVar.config["upload"] = False
        progress_update(0.035, num=0.0024)
        # 初始化原始上传信息
        get_upload_original()
        progress_update(0.04)
        # 更新Youtube和哔哩哔哩频道xml
        update_youtube_bilibili_rss()
        progress_update(0.1)
        # 判断是否有更新内容
        if gVar.channelid_youtube_ids_update or gVar.channelid_bilibili_ids_update:
            gVar.update_generate_rss = True
        if gVar.update_generate_rss:
            # 根据日出日落修改封面(只适用原封面)
            channge_icon()
            progress_update(0.11, num=0.0049)
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
            progress_update(0.12)
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            # 获取视频格式信息
            get_video_format()
            progress_update(0.199)
            # 恢复进程打印
            bottle_app_instance.cherry_print()
            # 优化下载顺序
            optimize_download()
            # 删除中断下载的媒体文件
            if gVar.config["delete_incompletement"]:
                delete_part(gVar.channelid_youtube_ids | gVar.channelid_bilibili_ids)
            progress_update(0.20, refresh=2)
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            # 下载并构建YouTube和哔哩哔哩视频
            download_and_build()
            progress_update(0.8)
            # 添加新媒体至上传列表
            add_upload()
            progress_update(0.81, num=0.0049)
            # 恢复进程打印
            bottle_app_instance.cherry_print()
            # 打印无法保留原节目信息
            original_rss_fail_print(gVar.xmls_original_fail)
            progress_update(0.82, num=0.0049)
            # 打印无法获取youtube信息
            print_fail_youtube()
            progress_update(0.83, num=0.0049)
            if gVar.config["remove_media"]:
                # 删除不在rss中的媒体文件
                remove_file()
                # 删除已抛弃的媒体文件夹
                remove_dir()
            progress_update(0.84)
            # 补全缺失媒体文件到字典
            make_up_file()
            progress_update(0.85)
            # 按参数获取需要补全的最大个数
            gVar.make_up_file_format = split_dict(
                gVar.make_up_file_format,
                gVar.config["completion_count"],
                True,
            )[0]
            progress_update(0.86, num=0.0049)
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            # 补全在rss中缺失的媒体格式信息
            make_up_file_format_mod()
            progress_update(0.90, num=0.0049)
            # 恢复进程打印
            bottle_app_instance.cherry_print()
            progress_update(0.91, num=0.0049)
            # 删除无法补全的媒体
            del_makeup_format_fail()
            progress_update(0.92, num=0.0049)
            # 暂停进程打印
            gVar.server_process_print_flag[0] = "pause"
            # 保存rss文件模块
            save_rss()
            progress_update(0.93, num=0.0049)
            # 下载补全Youtube和哔哩哔哩视频模块
            make_up_file_mod()
            progress_update(0.99, num=0.0099)
            # 恢复进程打印
            bottle_app_instance.cherry_print()
            # 更新并保存上传列表
            update_upload()
            progress_update(1, refresh=3)
        else:
            time_print("频道无更新内容")
        # 清空变量内数据
        gVar.channelid_youtube_ids_update.clear()  # 需更新的YouTube频道字典
        gVar.youtube_content_ytid_update.clear()  # 需下载YouTube视频字典
        gVar.youtube_content_ytid_backward_update.clear()  # 向后更新需下载YouTube视频字典
        gVar.channelid_youtube_rss.clear()  # YouTube频道最新Rss Response字典
        gVar.channelid_bilibili_ids_update.clear()  # 需更新的哔哩哔哩频道字典
        gVar.bilibili_content_bvid_update.clear()  # 需下载哔哩哔哩视频字典
        gVar.channelid_bilibili_rss.clear()  # 哔哩哔哩频道最新Rss Response字典
        gVar.bilibili_content_bvid_backward_update.clear()  # 向后更新需下载哔哩哔哩视频字典
        gVar.video_id_failed.clear()  # YouTube&哔哩哔哩视频下载失败列表
        gVar.video_id_update_format.clear()  # YouTube&哔哩哔哩视频下载的详细信息字典
        gVar.hash_rss_original = ""  # 原始rss哈希值文本
        gVar.xmls_original.clear()  # 原始xml信息字典
        gVar.xmls_original_fail.clear()  # 未获取原始xml频道列表
        gVar.xmls_quantity.clear()  # xml数量字典
        gVar.youtube_xml_get_tree.clear()  # YouTube频道简介和图标字典
        gVar.all_youtube_content_ytid.clear()  # 所有YouTube视频id字典
        gVar.all_bilibili_content_bvid.clear()  # 所有哔哩哔哩视频id字典
        gVar.all_items.clear()  # 更新后所有item明细列表
        gVar.overall_rss = ""  # 更新后的rss文本
        gVar.make_up_file_format.clear()  # 补全缺失媒体字典
        gVar.make_up_file_format_fail.clear()  # 补全缺失媒体失败字典
        # 将需要更新转为否
        gVar.update_generate_rss = False
        if parse.update_num != -1:
            parse.update_num -= 1
        if parse.argument == "a-shell":
            shortcuts_input = urllib.parse.quote(json.dumps(gVar.shortcuts_url))
            openserver_process = subprocess.Popen(
                [
                    "open",
                    f"shortcuts://run-shortcut?name=Podflow&input=text&text={shortcuts_input}",
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
    time_print("Podflow运行结束")
    cherrypy.engine.exit()
