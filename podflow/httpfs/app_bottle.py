# podflow/httpfs/app_bottle.py
# coding: utf-8

import os
import re
import sys
import io
import errno
import json
import time
import pprint
import hashlib
import mimetypes
import threading
import traceback
import contextlib
from datetime import datetime
from importlib import resources
from urllib.parse import urlparse
import cherrypy
from bottle import Bottle, abort, redirect, request, static_file, response
from cheroot import makefile as cheroot_makefile
from podflow import config_desc, gVar, default_config, parse
from podflow.upload.login import create
from podflow.basic.file_save import file_save
from podflow.basic.write_log import write_log
from podflow.httpfs.to_html import ansi_to_html
from podflow.upload.build_hash import build_hash
from podflow.upload.time_key import check_time_key
from podflow.basic.folder_build import folder_build
from podflow.httpfs.save_configs import save_configs
from podflow.httpfs.get_channelid import get_channelid
from podflow.basic.random_sequence import random_sequence
from podflow.upload.find_media_index import find_media_index
from podflow.upload.store_users_info import store_users_info
from podflow.basic.custom_media_file import read_custom_media
from podflow.basic.custom_media_file import save_custom_media
from podflow.message.normalize_video_url import normalize_video_url
from podflow.message.custom_media_format import get_custom_media_info


def patch_cheroot_closed_socket_flush():
    original_flush = cheroot_makefile.BufferedWriter._flush_unlocked
    if getattr(original_flush, "podflow_closed_socket_patch", False):
        return

    closed_socket_errors = {
        errno.EBADF,
        errno.ECONNABORTED,
        errno.ECONNRESET,
        errno.EPIPE,
        getattr(errno, "ESHUTDOWN", None),
    }
    closed_socket_errors.discard(None)

    def patched_flush(self):
        try:
            return original_flush(self)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 10038 or exc.errno in closed_socket_errors:
                self._write_buf.clear()
                return None
            raise

    patched_flush.podflow_closed_socket_patch = True
    cheroot_makefile.BufferedWriter._flush_unlocked = patched_flush


patch_cheroot_closed_socket_flush()


# 播放进度文件的读写锁: 页面关闭/切换时会连发多个保存请求,
# 加锁串行化读改写, 防止并发时读到写了一半的文件后用空记录覆盖全部播放进度
playback_history_lock = threading.Lock()


class bottle_app:
    # Bottle和Cherrypy初始化模块
    def __init__(self):
        self.app_bottle = Bottle()  # 创建 Bottle 应用
        self.bottle_print = []  # 存储打印日志
        self.setup_routes()  # 设置路由
        self.logname = "httpfs.log"  # 默认日志文件名
        self.http_fs = False
        self._last_message_state = {}  # 用于 SSE，跟踪消息状态
        self.random_list = random_sequence(64)

    def setup_routes(self, upload=False):
        # 设置/favicon.ico路由，回调函数为favicon
        self.app_bottle.route("/favicon.ico", callback=self.favicon)
        self.app_bottle.route("/apple-touch-icon.png", callback=self.favicon)
        self.app_bottle.route("/apple-touch-icon-precomposed.png", callback=self.favicon)
        # 设置根路由，回调函数为home
        self.app_bottle.route("/", callback=self.home)
        # 设置/shutdown路由，回调函数为shutdown
        self.app_bottle.route("/shutdown", callback=self.shutdown)
        if upload:
            self.app_bottle.route("/newuser", callback=self.new_user)
            self.app_bottle.route("/login", callback=self.login)
            self.app_bottle.route("/upload", method="POST", callback=self.upload)
            self.app_bottle.route("/flush", method="POST", callback=self.clear_cache)
            self.app_bottle.route("/remove", method="POST", callback=self.remove)
            self.app_bottle.route("/download", callback=self.download)
        else:
            self.app_bottle.route("/index", callback=self.index)
            self.app_bottle.route("/podcast", callback=self.podcast)
            self.app_bottle.route(
                "/playback-history",
                method=["GET", "POST"],
                callback=self.playback_history,
            )
            self.app_bottle.route("/getid", method="POST", callback=self.getid)
            self.app_bottle.route("/getconfig", callback=self.getconfig)
            self.app_bottle.route(
                "/saveconfig", method="POST", callback=self.saveconfig
            )
            self.app_bottle.route(
                "/favorite-update-status",
                method=["GET", "POST"],
                callback=self.favorite_update_status,
            )
            self.app_bottle.route(
                "/templates/<filepath:path>", callback=self.serve_template_file
            )
            self.app_bottle.route("/<filename:path>", callback=self.serve_static)
            self.app_bottle.route("/stream", callback=self.stream)
            self.app_bottle.route(
                "/youtube-cookie-setting",
                method=["GET", "POST"],
                callback=self.youtube_cookie_setting,
            )
            self.app_bottle.route(
                "/youtube-cookie-file",
                method=["GET", "POST"],
                callback=self.youtube_cookie_file,
            )
            # 隐藏测试页面: 查询任意 Python 变量或代码段(仅本地测试使用)
            # GET 供前端查询开关状态, POST 仅在 --debug-variable 启用时执行
            self.app_bottle.route(
                "/debug-variable",
                method=["GET", "POST"],
                callback=self.debug_variable,
            )
            # 隐藏测试页面: 历史记录 API(GET 列表 / POST 保存 / DELETE 删除)
            self.app_bottle.route(
                "/debug-history",
                method=["GET", "POST", "DELETE"],
                callback=self.debug_history,
            )
            self.app_bottle.route("/timestamp", method="GET", callback=self.timestamp)
            self.app_bottle.route("/playlist", method="GET", callback=self.playlist)
            self.app_bottle.route(
                "/custom-media",
                method=["GET", "POST"],
                callback=self.custom_media,
            )
            self.app_bottle.route(
                "/custom-media/reorder",
                method="POST",
                callback=self.custom_media_reorder,
            )
            self.app_bottle.route(
                "/custom-media/remove",
                method="POST",
                callback=self.custom_media_remove,
            )
            self.app_bottle.route(
                "/custom-media/lock",
                method=["GET", "POST"],
                callback=self.custom_media_lock,
            )

    # 设置日志文件名及写入判断
    def set_logname(self, logname="httpfs.log", http_fs=False):
        self.logname = logname
        self.http_fs = http_fs

    # 判断token是否正确的验证模块
    def token_judgment(self, token, VALID_TOKEN="", filename="", foldername=""):
        # 判断 token 是否有效
        if foldername != "channel_audiovisual/":
            # 对于其他文件夹, 采用常规的 Token 验证
            return VALID_TOKEN == "" or token == VALID_TOKEN
        if (
            VALID_TOKEN == ""
            and token == hashlib.sha256(f"{filename}".encode()).hexdigest()
        ):  # 如果没有配置 Token, 则使用文件名的哈希值
            return True
        elif (
            token == hashlib.sha256(f"{VALID_TOKEN}/{filename}".encode()).hexdigest()
        ):  # 使用验证 Token 和文件名的哈希值
            return True
        else:
            return False

    # 添加至bottle_print模块
    def add_bottle_print(self, client_ip, filename, status=""):
        # 后缀
        suffixs = [".mp4", ".m4a", ".xml", ".ico"]
        # 设置状态码对应的颜色
        status_colors = {
            200: "\033[32m",  # 绿色 (成功)
            401: "\033[31m",  # 红色 (未经授权)
            404: "\033[35m",  # 紫色 (未找到)
            303: "\033[33m",  # 黄色 (重定向)
            206: "\033[36m",  # 青色 (部分内容)
            400: "\033[33m",  # 黄色 (请求错误)
        }
        # 默认颜色
        if status in status_colors:
            color = status_colors.get(status, "\033[0m")
            status = f"{color}{status}\033[0m"
        now_time = datetime.now().strftime("%H:%M:%S")
        client_ip = f"\033[34m{client_ip}\033[0m"
        if self.http_fs:
            write_log(
                f"{client_ip} {filename} {status}",
                None,
                False,
                True,
                None,
                self.logname,
            )
        for suffix in suffixs:
            filename = filename.replace(suffix, "")
        bottle_text = f"{now_time}|{client_ip} {filename} {status}"
        self.bottle_print.append(bottle_text)
        gVar.index_message["http"].append(ansi_to_html(bottle_text))

    # CherryPy 服务器打印模块
    def cherry_print(self, flag_judgment=True):
        # 如果flag_judgment为True，则将gVar.server_process_print_flag[0]设置为"keep"
        if flag_judgment:
            gVar.server_process_print_flag[0] = "keep"
        # 如果gVar.server_process_print_flag[0]为"keep"且self.bottle_print不为空，则打印日志
        if (
            gVar.server_process_print_flag[0] == "keep" and self.bottle_print
        ):  # 如果设置为保持输出, 则打印日志
            # 遍历self.bottle_print中的每个元素，并打印
            for info_print in self.bottle_print:
                print(info_print)
            # 清空self.bottle_print
            self.bottle_print.clear()

    # 输出请求日志的函数
    def print_out(self, filename, status=""):
        client_ip = request.remote_addr
        if client_port := request.environ.get("REMOTE_PORT"):
            client_ip = f"{client_ip}:{client_port}"
        if filename not in [
            "favicon.ico",
            "/",
            "shutdown",
            "newuser",
            "login",
        ]:
            bottle_channelid = (
                gVar.channelid_youtube_ids_original
                | gVar.channelid_bilibili_ids_original
                | {"channel_audiovisual/": "", "channel_rss/": ""}
            )  # 合并多个频道 ID
            for (
                bottle_channelid_key,
                bottle_channelid_value,
            ) in bottle_channelid.items():
                filename = filename.replace(
                    bottle_channelid_key, bottle_channelid_value
                )  # 替换频道路径
                if status == 200 and request.headers.get(
                    "Range"
                ):  # 如果是部分请求, 则返回 206 状态
                    status = 206
        self.add_bottle_print(client_ip, filename, status)  # 输出日志
        self.cherry_print(False)

    # 主路由处理根路径请求
    def home(self):
        VALID_TOKEN = gVar.config["token"]  # 从配置中读取主验证 Token
        token = request.query.get("token")  # 获取请求中的 Token

        if self.token_judgment(token, VALID_TOKEN):  # 验证 Token
            self.print_out("/", 303)  # 如果验证成功, 输出 200 状态
            return redirect("https://github.com/gruel-zxz/podflow")  # 返回正常响应
        else:
            self.print_out("/", 401)  # 如果验证失败, 输出 401 状态
            abort(401, "Unauthorized: Invalid Token")  # 返回未经授权错误

    # 路由处理关闭服务器的请求
    def shutdown(self):
        Shutdown_VALID_TOKEN = "shutdown"
        Shutdown_VALID_TOKEN += datetime.now().strftime("%Y%m%d%H%M%S")
        Shutdown_VALID_TOKEN += os.urandom(32).hex()
        Shutdown_VALID_TOKEN = hashlib.sha256(
            Shutdown_VALID_TOKEN.encode()
        ).hexdigest()  # 用于服务器关闭的验证 Token
        token = request.query.get("token")  # 获取请求中的 Token

        if self.token_judgment(
            token, Shutdown_VALID_TOKEN
        ):  # 验证 Token 是否为关闭用的 Token
            self.print_out("shutdown", 200)  # 如果验证成功, 输出 200 状态
            threading.Timer(0.1, cherrypy.engine.exit).start()
            return "Shutting down..."  # 返回关机响应
        else:
            self.print_out("shutdown", 401)  # 如果验证失败, 输出 401 状态
            abort(401, "Unauthorized: Invalid Token")  # 返回未经授权错误

    # 路由处理 favicon 请求
    def favicon(self):
        current_path = request.path.lstrip("/")  # 获取当前路径
        self.print_out(current_path, 303)  # 输出访问 favicon 的日志
        return redirect(
            "https://raw.githubusercontent.com/gruel-zxz/podflow/main/Podflow.png"
        )  # 重定向到图标 URL

    # 路由处理静态文件请求
    def serve_static(self, filename):
        VALID_TOKEN = gVar.config["token"]  # 从配置中读取主验证 Token
        # 定义要共享的文件路径
        bottle_filename = gVar.config["filename"]  # 从配置中读取文件名
        shared_files = {
            bottle_filename.lower(): f"{bottle_filename}.xml",  # 文件路径映射, 支持大小写不敏感的文件名
            f"{bottle_filename.lower()}.xml": f"{bottle_filename}.xml",  # 同上, 支持带 .xml 后缀
        }
        token = request.query.get("token")  # 获取请求中的 Token

        # 文件是否存在检查的函数
        def file_exist(token, VALID_TOKEN, filename, foldername=""):
            # 验证 Token
            if self.token_judgment(
                token, VALID_TOKEN, filename, foldername
            ):  # 验证 Token
                # 如果文件存在, 返回文件
                if os.path.exists(filename):  # 如果文件存在, 返回文件
                    self.print_out(filename, 200)
                    # 设置正确的 Content-Type 头部
                    content_type, _ = mimetypes.guess_type(filename)
                    # 如果无法自动猜测出正确的 Content-Type，手动指定
                    if not content_type:
                        if filename.endswith(".xml"):
                            content_type = "application/xml"
                        elif filename.endswith(".m4a"):
                            content_type = "audio/mp4"
                        elif filename.endswith(".mp4"):
                            content_type = "video/mp4"
                        else:
                            content_type = "application/octet-stream"  # 默认文件类型

                    # 返回静态文件并附加正确的 Content-Type
                    return static_file(filename, root=".", mimetype=content_type)
                else:  # 如果文件不存在, 返回 404 错误
                    self.print_out(filename, 404)
                    abort(404, "File not found")
            else:  # 如果 Token 验证失败, 返回 401 错误
                self.print_out(filename, 401)
                abort(401, "Unauthorized: Invalid Token")

        # 处理不同的文件路径
        if filename in ["channel_audiovisual/", "channel_rss/"]:
            self.print_out(filename, 404)
            abort(404, "File not found")
        elif filename.startswith("channel_audiovisual/"):
            return file_exist(token, VALID_TOKEN, filename, "channel_audiovisual/")
        elif filename.startswith("channel_rss/") and filename.endswith(".xml"):
            return file_exist(token, VALID_TOKEN, filename)
        elif filename.startswith("channel_rss/"):
            return file_exist(token, VALID_TOKEN, f"{filename}.xml")
        elif filename.lower() in shared_files:
            return file_exist(token, VALID_TOKEN, shared_files[filename.lower()])
        else:
            self.print_out(filename, 404)  # 如果文件路径未匹配, 返回 404 错误
            abort(404, "File not found")

    # 路由获取账号密码请求
    def new_user(self):
        # 生成一个用于上传非一次性项目的账户密码，该密码需要保存
        seed = "We need to generate an account password for uploading non one-time items that need to be saved."
        token = request.query.get("token")  # 获取请求中的 Token
        response.content_type = "application/json"

        if check_time_key(token, seed):  # 验证 Token
            username, password = create()  # 生成用户名和密码
            self.print_out("newuser", 200)
            return {
                "code": 0,
                "message": "Get New Username And Password Success",
                "data": {
                    "username": username,
                    "password": password,
                },
            }
        else:
            self.print_out("newuser", 401)
            return {
                "code": -1,
                "message": "Unauthorized: Invalid Token",  # 未经授权: 无效的 Token
            }

    # 路由处理登陆请求
    def login(self):
        # 获取上传的数据
        upload_data = gVar.upload_data
        # 获取用户名
        username = request.query.get("username")
        # 获取密码
        password = request.query.get("password")
        # 判断用户名是否在上传的数据中
        if username in upload_data:
            # 判断密码是否正确
            if upload_data[username] == password:
                # 打印登录成功
                self.print_out("login", 200)
                # 返回登录成功的信息
                return {
                    "code": 0,
                    "message": "Login Success",
                }
            else:
                # 打印密码错误
                self.print_out("login", 401)
                # 返回密码错误的信息
                return {
                    "code": -3,
                    "message": "Password Error",
                }
        else:
            # 打印用户名错误
            self.print_out("login", 401)
            # 返回用户名错误的信息
            return {
                "code": -2,
                "message": "Username Error",
            }

    # 文件上传处理请求
    def upload(self):
        # 初始化 upload_file 为 None，以便在 finally 块中安全检查
        upload_file = None
        # 获取上传数据配置(存储用户名和密码)
        upload_data = gVar.upload_data
        # 从请求参数中获取用户名，默认为空字符串
        username = request.query.get("username", "")
        # 从请求参数中获取密码，默认为空字符串
        password = request.query.get("password", "")
        upload_hash = request.query.get("hash", "")
        channelid = request.query.get("channel_id", "")
        check = request.query.get("check", "")
        filename = request.query.get("filename", "")
        if username not in upload_data:
            self.print_out("login", 401)
            return {
                "code": -2,
                "message": "Username Error",  # 用户名错误
            }
        # 验证密码是否正确
        if upload_data[username] != password:
            self.print_out("login", 401)
            return {
                "code": -3,
                "message": "Password Error",  # 密码错误
            }
        if not re.match(r"^[0-9a-fA-F]{64}$", upload_hash):
            self.print_out("upload", 404)
            return {
                "code": -8,
                "message": "Invalid Hash Format",  # 哈希值格式不正确
            }
        if not channelid:
            # 打印错误信息并返回错误码
            self.print_out("upload", 404)
            return {
                "code": -6,
                "message": "ChannelId Does Not Exist",  # 频道ID不存在
            }
        if not filename:
            self.print_out("upload", 404)
            return {
                "code": -14,
                "message": "Filename Not Provided",  # 未提供文件名
            }
        address = f"channel_audiovisual/{channelid}"
        file_list = os.listdir(address) if os.path.exists(address) else []
        # 安全地分割文件名和后缀
        parts = filename.rsplit(".", 1)
        name = parts[0]
        suffix = parts[1].lower() if len(parts) > 1 else ""  # 转换为小写以便比较
        if suffix not in ["mp4", "m4a"]:
            self.print_out("upload", 404)
            return {
                "code": -7,
                "message": "File Name Error",  # 文件格式错误
            }
        create_check = ""
        for ref in self.random_list:
            create_check += upload_hash[ref]
        if check:
            if check != create_check:
                self.print_out("upload", 404)
                return {
                    "code": -9,
                    "message": "Check Error",  # 检查错误
                }
            try:
                # 从请求中获取上传的文件对象
                upload_file = request.files.get("file")
                # 检查是否有文件被上传
                if not upload_file:
                    # 打印错误信息并返回错误码
                    self.print_out("upload", 404)
                    return {
                        "code": -4,
                        "message": "No File Provided",  # 没有上传文件
                    }
                # 获取实际的文件句柄
                uploadfile_obj = upload_file.file
                # 去除临时文件模块
                def close_file():
                    if (
                        upload_file
                        and hasattr(upload_file, "file")
                        and not upload_file.file.closed
                    ):
                        try:
                            upload_file.file.close()
                        except Exception:
                            pass
                # 判断文件是否完整
                uploadfile_obj.seek(0)  # 确保从文件开头计算哈希
                uploadfile_hash = build_hash(uploadfile_obj)
                if upload_hash != uploadfile_hash:
                    self.print_out("upload", 401)
                    close_file()
                    return {
                        "code": -5,
                        "message": "Incomplete File",  # 文件不完整
                        "hash": uploadfile_hash,
                    }
                num = 0
                while True:
                    # 构建当前尝试的文件名
                    current_filename = (
                        f"{name}.{suffix}" if num == 0 else f"{name}.{num}.{suffix}"
                    )
                    full_target_path = os.path.join(
                        os.getcwd(), address, current_filename
                    )  # 完整的保存路径
                    if current_filename in file_list:
                        # 如果文件名已存在，检查是否是相同文件
                        # 再次检查文件是否存在于磁盘，以防在列表检查后文件被删除
                        if os.path.exists(full_target_path):
                            with open(full_target_path, "rb") as original_file:
                                original_file.seek(0)
                                if upload_hash == build_hash(original_file):
                                    self.print_out("upload same", 200)
                                    store_users_info(username, filename, channelid)
                                    close_file()
                                    return {
                                        "code": 1,
                                        "message": "The Same File Exists",  # 相同文件已存在
                                        "data": {
                                            "filename": current_filename,
                                        },
                                    }
                        num += 1  # 如果哈希不同，尝试下一个文件名
                    else:
                        # 文件名不存在，可以保存
                        folder_build(
                            channelid, "channel_audiovisual"
                        )  # 确保目标文件夹存在
                        uploadfile_obj.seek(0)  # 再次重置文件指针到开头，准备写入
                        file_save(
                            uploadfile_obj, current_filename, address, True
                        )  # 传递文件对象
                        # 打印成功信息并返回成功码
                        self.print_out("upload", 200)
                        store_users_info(username, filename, channelid)
                        close_file()
                        return {
                            "code": 0,
                            "message": "Upload Success",  # 上传成功
                            "data": {
                                "filename": current_filename,
                            },
                        }
            except Exception as e:
                # 捕获所有其他可能的异常
                self.print_out("upload", 500)
                return {
                    "code": -10,
                    "message": f"Server Error: {str(e)}",  # 将异常信息返回给客户端
                }
            finally:
                # 无论函数如何退出（正常返回或抛出异常），都会执行此块
                if (
                    upload_file
                    and hasattr(upload_file, "file")
                    and not upload_file.file.closed
                ):
                    try:
                        upload_file.file.close()
                    except Exception:
                        pass
        else:
            num = 0
            while True:
                # 构建当前尝试的文件名
                current_filename = (
                    f"{name}.{suffix}" if num == 0 else f"{name}.{num}.{suffix}"
                )
                full_target_path = os.path.join(
                    os.getcwd(), address, current_filename
                )  # 完整的保存路径
                if current_filename in file_list:
                    if os.path.exists(full_target_path):
                        with open(full_target_path, "rb") as original_file:
                            original_file.seek(0)
                            if upload_hash == build_hash(original_file):
                                self.print_out("upload same", 200)
                                store_users_info(username, filename, channelid)
                                return {
                                    "code": 1,
                                    "message": "The Same File Exists",  # 相同文件已存在
                                    "data": {
                                        "filename": current_filename,
                                    },
                                }
                    num += 1  # 如果哈希不同，尝试下一个文件名
                else:
                    self.print_out("advance upload", 200)
                    return {
                        "code": 2,
                        "message": "Can Be Uploaded",  # 可以上传
                        "data": {
                            "filename": current_filename,
                            "check": create_check,  # 返回创建的检查值
                        },
                    }

    # 路由处理清除缓存请求
    def clear_cache(self):
        # 获取上传数据配置(存储用户名和密码)
        upload_data = gVar.upload_data
        # 从请求参数中获取用户名，默认为空字符串
        username = request.query.get("username", "")
        # 从请求参数中获取密码，默认为空字符串
        password = request.query.get("password", "")
        if username not in upload_data:
            self.print_out("login", 401)
            return {
                "code": -2,
                "message": "Username Error",  # 用户名错误
            }
        # 验证密码是否正确
        if upload_data[username] != password:
            self.print_out("login", 401)
            return {
                "code": -3,
                "message": "Password Error",  # 密码错误
            }
        if os.path.exists("tmp"):
            # 清除 tmp 目录下的所有文件
            for filename in os.listdir("tmp"):
                file_path = os.path.join("tmp", filename)
                try:
                    os.remove(file_path)  # 删除文件
                except Exception as e:
                    self.print_out("flush", 500)
                    return {
                        "code": -11,
                        "message": "Error removing flush",  # 删除文件错误
                        "error": str(e),
                    }
            self.print_out("flush", 200)
            return {
                "code": 3,
                "message": "Cache Cleared Successfully",  # 缓存清除成功
            }
        else:
            self.print_out("flush", 404)
            return {
                "code": -12,
                "message": "Cache Does Not Exist",  # 缓存不存在
            }

    # 路由处理删除请求
    def remove(self):
        # 获取已上传数据
        upload_message = gVar.upload_message
        # 获取上传数据配置(存储用户名和密码)
        upload_data = gVar.upload_data
        # 从请求参数中获取用户名，默认为空字符串
        username = request.query.get("username", "")
        # 从请求参数中获取密码，默认为空字符串
        password = request.query.get("password", "")
        if username not in upload_data:
            self.print_out("login", 401)
            return {
                "code": -2,
                "message": "Username Error",  # 用户名错误
                "error": None,
            }
        # 验证密码是否正确
        if upload_data[username] != password:
            self.print_out("login", 401)
            return {
                "code": -3,
                "message": "Password Error",  # 密码错误
                "error": None,
            }
        mode = request.query.get("mode", "")
        if mode not in ["file", "folder"]:
            self.print_out("remove", 404)
            return {
                "code": -13,
                "message": "Invalid Mode",  # 无效的模式
                "error": None,
            }
        channelid = request.query.get("channel_id", "")
        if not channelid:
            # 打印错误信息并返回错误码
            self.print_out("remove", 404)
            return {
                "code": -6,
                "message": "ChannelId Does Not Exist",  # 频道ID不存在
                "error": None,
            }
        if mode == "file":
            filename = request.query.get("filename", "")
            if not filename:
                self.print_out("remove", 404)
                return {
                    "code": -14,
                    "message": "Filename Not Provided",  # 未提供文件名
                    "error": None,
                }
            index = find_media_index(upload_message, filename, "mediaid")
            if index == -1:
                self.print_out("remove", 404)
                return{
                    "code": -15,
                    "message": "File Not In Data",  # 文件不在数据中
                    "error": None,
                }
            if upload_message[index]["channelid"] != channelid:
                self.print_out("remove", 404)
                return {
                    "code": -16,
                    "message": "ChannelId Mismatch",  # 频道ID不匹配
                    "error": None,
                }
            userlist = upload_message[index]["users"]
            if username not in userlist:
                self.print_out("remove", 404)
                return {
                    "code": -17,
                    "message": "User Not In List",  # 用户不在列表中
                    "error": None,
                }
            try:
                os.remove(f"channel_audiovisual/{channelid}/{filename}")
            except FileNotFoundError:
                self.print_out("remove", 404)
                return {
                    "code": -18,
                    "message": "File Not Found",  # 文件未找到
                    "error": None,
                }
            except Exception as e:
                self.print_out("remove", 500)
                return {
                    "code": -19,
                    "message": f"Error Removing File: {str(e)}",  # 删除文件错误
                    "error": str(e),
                }
            if len(userlist) == 1:
                # 如果用户列表中只有当前用户, 则删除该条记录
                del upload_message[index]
            else:
                # 如果用户列表中有多个用户, 则移除当前用户
                upload_message[index]["users"].remove(username)
            self.print_out("remove", 200)
            return {
                "code": 4,
                "message": "File Removed Successfully",  # 文件删除成功
                "error": None,
            }
        else:
            remove_num = 0
            for item in upload_message:
                userlist = item["users"]
                if item["channelid"] == channelid and username in userlist:
                    try:
                        os.remove(f"channel_audiovisual/{channelid}/{item['mediaid']}")
                        remove_num += 1
                    except FileNotFoundError:
                        self.print_out("remove", 404)
                        return {
                            "code": -18,
                            "message": "File Not Found",  # 文件未找到
                            "error": None,
                        }
                    except Exception as e:
                        self.print_out("remove", 500)
                        return {
                            "code": -19,
                            "message": f"Error Removing File: {str(e)}",  # 删除文件错误
                            "error": str(e),
                        }
                    if len(userlist) == 1:
                        # 如果用户列表中只有当前用户, 则删除该条记录
                        del upload_message[index]
                    else:
                        # 如果用户列表中有多个用户, 则移除当前用户
                        upload_message[index]["users"].remove(username)
            if remove_num == 0:
                self.print_out("remove", 404)
                return {
                    "code": -20,
                    "message": "No Files Found",  # 未找到用户的文件
                    "error": None,
                }
            else:
                self.print_out("remove", 200)
                return {
                    "code": 5,
                    "message": "Folder Removed Successfully",  # 文件夹删除成功
                    "error": None,
                }
    # 路由处理下载请求
    def download(self):
        # 获取已上传数据
        upload_message = gVar.upload_message
        # 获取上传数据配置(存储用户名和密码)
        upload_data = gVar.upload_data
        # 从请求参数中获取用户名，默认为空字符串
        username = request.query.get("username", "")
        # 从请求参数中获取密码，默认为空字符串
        password = request.query.get("password", "")
        channelid = request.query.get("channel_id", "")
        filename = request.query.get("filename", "")
        if username not in upload_data:
            self.print_out("login", 401)
            return {
                "code": -2,
                "message": "Username Error",  # 用户名错误
                "error": None,
            }
        # 验证密码是否正确
        if upload_data[username] != password:
            self.print_out("login", 401)
            return {
                "code": -3,
                "message": "Password Error",  # 密码错误
                "error": None,
            }
        if not channelid:
            self.print_out("download", 404)
            return {
                "code": -6,
                "message": "ChannelId Does Not Exist",  # 频道ID不存在
            }
        if not filename:
            self.print_out("download", 404)
            return {
                "code": -14,
                "message": "Filename Not Provided",  # 未提供文件名
            }
            
            
            
            
            
    

    # 路由处理模板文件请求
    def serve_template_file(self, filepath):
        # 禁止浏览器缓存模板文件（HTML/CSS/JS），确保前端更新后立即可见
        # 注意: static_file 返回全新 response 对象, 必须把缓存头通过参数传入才会生效
        cache_headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        # 使用 resources.files 定位 'podflow' 包内的 'templates' 目录
        # 结果是一个 path-like 对象，转为 str 确保兼容 static_file 函数
        template_dir_path = resources.files("podflow") / "templates"
        # 假设 static_file 需要一个字符串路径作为 root
        return static_file(filepath, root=str(template_dir_path), headers=cache_headers)

    # 使用 importlib.resources 获取模板文件内容
    def index(self):
        # 使用 resources.files 定位到具体的文件
        template_file = resources.files("podflow") / "templates" / "index.html"
        # TraversablePath 对象支持 open() 方法，直接打开文件
        with template_file.open("r", encoding="UTF-8") as f:
            html_content = f.read()
        # 禁止浏览器缓存 index.html，确保模板更新后立即可见
        response.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.set_header("Pragma", "no-cache")
        response.set_header("Expires", "0")
        self.print_out("index", 200)
        return html_content
    
    def podcast(self):
        # 使用 resources.files 定位到具体的文件
        template_file = resources.files("podflow") / "templates" / "podcast.html"
        # TraversablePath 对象支持 open() 方法，直接打开文件
        with template_file.open("r", encoding="UTF-8") as f:
            html_content = f.read()
        self.print_out("podcast", 200)
        return html_content

    # 播客播放器的播放进度(GET 读取 / POST 保存)
    # 进度存于channel_data/playback_history.json, 跨终端共享
    # 文件按xml(播客地址)分组, 每个xml都有自己独立的最后播放内容与单集进度:
    # {"<播客地址>": {"last_played": {...}, "episodes": {"<guid>": {...}}}}
    def read_playback_history(self, history_path):
        # 文件不存在或内容损坏时返回空字典
        try:
            if os.path.exists(history_path):
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            else:
                return {}
        except Exception:
            return {}
        if not isinstance(history, dict):
            return {}
        return history

    def save_playback_history(self, history_path, history):
        # 先写临时文件再原子替换, 即使写入中途断电/被并发读取也不会留下损坏的文件
        temp_path = history_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        os.replace(temp_path, history_path)

    def playback_history(self):
        response.content_type = "application/json"
        history_path = os.path.join(
            os.getcwd(), "channel_data", "playback_history.json"
        )
        # 页面关闭/切换时会连发多个保存请求, 加锁串行化读改写;
        # 否则并发时可能读到写了一半的文件, 按空记录覆盖, 丢失全部播放进度
        with playback_history_lock:
            if request.method == "POST":
                req_data = self.get_request_json()
                feed_url = req_data.get("url")
                guid = req_data.get("guid")
                filter_value = req_data.get("filter")
                rate = req_data.get("rate")
                rate_valid = (
                    isinstance(rate, (int, float))
                    and not isinstance(rate, bool)
                    and 0.5 <= rate <= 4
                )
                # 播放进度保存需携带guid, 筛选选项/播放速率保存需携带合法取值
                if (
                    not isinstance(feed_url, str)
                    or not feed_url
                    or (
                        not (isinstance(guid, str) and guid)
                        and filter_value not in ("unplayed", "played", "all")
                        and not rate_valid
                    )
                ):
                    self.print_out("playback-history", 400)
                    response.status = 400
                    return {"error": "无效的播放进度数据"}
                history = self.read_playback_history(history_path)
                # 旧格式(按单集guid平铺)或异常结构直接丢弃, 按新格式重建
                history = {
                    key: value
                    for key, value in history.items()
                    if isinstance(value, dict) and "episodes" in value
                }
                feed_data = history.get(feed_url)
                if not isinstance(feed_data, dict):
                    feed_data = {}
                if isinstance(guid, str) and guid:
                    episodes = feed_data.get("episodes")
                    if not isinstance(episodes, dict):
                        episodes = {}
                    record = {
                        "time": req_data.get("time"),
                        "duration": req_data.get("duration"),
                        "updated": req_data.get("updated"),
                        "completed": bool(req_data.get("completed")),
                    }
                    episodes[guid] = record
                    # 每次保存都覆盖该xml的最后播放内容
                    feed_data["last_played"] = {
                        "guid": guid,
                        "title": req_data.get("title") or "",
                        "media_url": req_data.get("media_url") or "",
                        "isVideo": bool(req_data.get("isVideo")),
                        "time": record["time"],
                        "duration": record["duration"],
                        "updated": record["updated"],
                    }
                    feed_data["episodes"] = episodes
                    # 进度POST顺带携带的播放速率同步更新
                    if rate_valid:
                        feed_data["rate"] = rate
                elif filter_value in ("unplayed", "played", "all"):
                    # 筛选选项保存(未播放/已播放/全部), 默认全部
                    feed_data["filter"] = filter_value
                else:
                    # 播放速率保存(按xml独立)
                    feed_data["rate"] = rate
                if "episodes" not in feed_data:
                    feed_data["episodes"] = {}
                history[feed_url] = feed_data
                try:
                    self.save_playback_history(history_path, history)
                except Exception as e:
                    self.print_out("playback-history", 500)
                    response.status = 500
                    return {"error": f"保存播放进度失败: {e}"}
                return {"message": "已保存"}
            # GET 返回全部播放进度, 文件不存在或内容损坏时返回空字典
            return self.read_playback_history(history_path)

    # 获取 JSON 数据，Bottle 会自动解析请求体中的 JSON 数据
    def getid(self):
        content = getid_data.get("content", "") if (getid_data := request.json) else ""
        response_message = get_channelid(content)
        self.print_out("channelid", 200)
        # 设置响应头为 application/json
        response.content_type = "application/json"
        return {"response": response_message}

    # 获取配置数据
    def getconfig(self):
        self.print_out("getconfig", 200)
        # 设置响应头为 application/json
        response.content_type = "application/json"
        # config_desc（podflow/__init__.py）随响应下发, 前端据此同步字段顺序/默认值/可选项/说明
        return {
            "response": gVar.config,
            "default_config": default_config,
            "config_desc": config_desc,
        }

    # 保存前端提交的最终配置数据
    def saveconfig(self):
        save_config = request.json
        # 提交的数据必须是JSON字典
        if not isinstance(save_config, dict):
            self.print_out("saveconfig", 400)
            response.status = 400
            # 设置响应头为 application/json
            response.content_type = "application/json"
            return {"error": "配置数据必须为JSON对象"}
        # address 由 url 与 port 自动生成, 只回显给前端, 不写入配置文件
        file_config = {key: value for key, value in save_config.items() if key != "address"}
        # 与启动时读取的是同一个配置文件, 主循环每轮 build_original(False) 会重新加载
        config_file = parse.config or "config.json"
        try:
            #save_configs(file_config, config_file)
            save_configs(file_config, "config_save.json")
        except (OSError, TypeError) as error:
            self.print_out("saveconfig", 500)
            response.status = 500
            # 设置响应头为 application/json
            response.content_type = "application/json"
            return {"error": f"配置文件写入失败: {error}"}
        write_log(f"配置已保存至{config_file}")
        self.print_out("saveconfig", 200)
        # 设置响应头为 application/json
        response.content_type = "application/json"
        return save_config

    # --- 新增 SSE 流处理路由 ---
    def stream(self):
        response.content_type = "application/json"
        response.set_header("Cache-Control", "no-cache")
        response.set_header("Access-Control-Allow-Origin", "*")
        
        if not hasattr(gVar, "index_message"):
            current_state = {
                "http": [],
                "podflow": [],
                "schedule": {},
                "download": [],
            }
        else:
            current_state = gVar.index_message
            for key in ["http", "podflow", "schedule", "download"]:
                if key not in current_state:
                    current_state[key] = (
                        [] if key in ["http", "podflow", "download"] else {}
                    )
        
        # 直接返回 JSON 字符串，立即释放线程
        return json.dumps(current_state)
    
# 设置及获取 YouTube Cookie 配置数据
    def youtube_cookie_setting(self):
        if request.method == "POST":
            req_data = request.json or {}
            enabled = req_data.get("enabled")
            if not isinstance(enabled, bool):
                self.print_out("youtube-cookie-setting", 400)
                response.status = 400
                # 设置响应头为 application/json
                response.content_type = "application/json"
                return {"error": "enabled 必须为布尔值"}
            
            gVar.youtube_cookie_switch = enabled
            # 根据传入的布尔值打出不同的操作日志
            if enabled:
                self.print_out("youtube🍪-on", 200)
            else:
                self.print_out("youtube🍪-off", 200)

        # 设置响应头为 application/json
        response.content_type = "application/json"
        return {
            "enabled": getattr(gVar, "youtube_cookie_switch", False),
            "cookie_available": bool(getattr(gVar, "youtube_cookie", None)),
        }

    # 获取倒计时，或跳过等待并立即进入下一次更新。
    def favorite_update_status(self):
        # 自定义媒体下载期间视为忙碌, 按钮禁用且跳过等待请求被拒绝
        busy = gVar.custom_media_progress is not None
        if request.method == "POST":
            if not gVar.favorite_update_active or busy:
                response.status = 409
                response.content_type = "application/json"
                return {"error": "当前没有正在执行的倒计时"}
            gVar.favorite_update_skip_wait.set()
            self.print_out("favorite-update-immediate", 200)

        response.content_type = "application/json"
        return {
            "active": gVar.favorite_update_active and not busy,
            "next_run": gVar.favorite_update_next_run,
        }
    
    def timestamp(self):
        response.content_type = "application/json"
        return {"timestamp": int(time.time())}

    # 读取或保存 YouTube Cookie 文件
    def youtube_cookie_file(self):
        cookie_path = os.path.join(os.getcwd(), "channel_data", "yt_dlp_youtube.txt")
        response.content_type = "application/json"

        if request.method == "GET":
            # 读取 Cookie 文件，不存在则返回空字符串
            if os.path.exists(cookie_path):
                with open(cookie_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = ""
            self.print_out("youtube🍪-read", 200)
            return {"content": content}

        if request.method == "POST":
            try:
                req_data = request.json or {}
                content = req_data.get("content", "")
                # 确保 channel_data 文件夹存在
                folder_build("channel_data")
                # 保存 Cookie 文件
                file_save(content, "yt_dlp_youtube.txt", "channel_data")
                # 更新全局 Cookie 可用状态
                gVar.youtube_cookie = bool(content.strip())
                self.print_out("youtube🍪-save", 200)
                return {"message": "Cookie 文件保存成功"}
            except Exception as e:
                self.print_out("youtube🍪-save", 500)
                response.status = 500
                return {"error": f"保存失败: {str(e)}"}

    # 将查询结果格式化为 4 格缩进并保留换行(字典/列表等结构化数据)
    def format_debug_output(self, value):
        # 字符串原样输出, 保留其中已有的缩进与换行
        if isinstance(value, str):
            return value
        # None 及数字/布尔等标量直接给出字面量
        if value is None or isinstance(value, (bool, int, float)):
            return repr(value)
        try:
            # 结构化数据按 JSON 风格输出: 每级缩进 4 个空格, 保留换行
            return json.dumps(value, indent=4, ensure_ascii=False, default=repr)
        except (TypeError, ValueError):
            # 无法 JSON 序列化(如循环引用)时退回 pprint, 同样 4 格缩进
            return pprint.pformat(value, indent=4, width=100, sort_dicts=False)

    # 隐藏测试页面: 执行输入的 Python 变量或代码段并返回格式化结果
    # 由命令行参数 --debug-variable 控制开关, 未启用时仅返回关闭状态/拒绝执行
    def debug_history(self):
        response.content_type = "application/json"
        history_path = os.path.join(os.getcwd(), "channel_data", "debug_history.jsonl")

        if request.method == "GET":
            items = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.rstrip("\n\r")
                            if not line:
                                continue
                            try:
                                items.append(json.loads(line))
                            except Exception:
                                continue
                except Exception as e:
                    self.print_out("debug-history", 500)
                    response.status = 500
                    return {"error": f"读取历史记录失败: {e}"}
            return {"items": items}

        if request.method == "POST":
            if not parse.debug_variable:
                self.print_out("debug-history", 404)
                response.status = 404
                return {"error": "未启用变量查询功能(需命令行参数 --debug-variable)"}
            req_data = self.get_request_json()
            code = req_data.get("code")
            output = req_data.get("output")
            if not isinstance(code, str) or not isinstance(output, str):
                self.print_out("debug-history", 400)
                response.status = 400
                return {"error": "无效的历史记录数据"}
            item = {
                "id": hashlib.sha1((code + output + str(time.time())).encode()).hexdigest()[:16],
                "code": code,
                "output": output,
                "timestamp": int(time.time()),
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            # 如果最新一条历史记录与本次完全相同则不重复写入
            try:
                if os.path.exists(history_path):
                    with open(history_path, "r", encoding="utf-8") as f:
                        last_item = None
                        for line in f:
                            line = line.rstrip("\n\r")
                            if not line:
                                continue
                            try:
                                last_item = json.loads(line)
                            except Exception:
                                continue
                        if last_item is not None:
                            if last_item.get("code") == code and last_item.get("output") == output:
                                self.print_out("debug-history-skip-duplicate", 200)
                                return {"message": "重复记录已跳过", "item": last_item, "skipped": True}
            except Exception:
                pass
            try:
                with open(history_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            except Exception as e:
                self.print_out("debug-history", 500)
                response.status = 500
                return {"error": f"保存历史记录失败: {e}"}
            self.print_out("debug-history-save", 200)
            return {"message": "已保存", "item": item}

        if request.method == "DELETE":
            if not parse.debug_variable:
                self.print_out("debug-history", 404)
                response.status = 404
                return {"error": "未启用变量查询功能(需命令行参数 --debug-variable)"}
            req_data = self.get_request_json()
            item_id = req_data.get("id")
            if not isinstance(item_id, str):
                self.print_out("debug-history", 400)
                response.status = 400
                return {"error": "缺少历史记录ID"}
            if not os.path.exists(history_path):
                return {"items": []}
            items = []
            changed = False
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.rstrip("\n\r")
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue
                        if obj.get("id") == item_id:
                            changed = True
                            continue
                        items.append(obj)
            except Exception as e:
                self.print_out("debug-history", 500)
                response.status = 500
                return {"error": f"读取历史记录失败: {e}"}
            if changed:
                try:
                    with open(history_path, "w", encoding="utf-8") as f:
                        for obj in items:
                            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                except Exception as e:
                    self.print_out("debug-history", 500)
                    response.status = 500
                    return {"error": f"保存历史记录失败: {e}"}
            self.print_out("debug-history-delete", 200)
            return {"items": items, "removed": changed}

        response.status = 405
        return {"error": "不支持的请求方法"}

    def debug_variable(self):
        response.content_type = "application/json"
        # GET 请求仅返回开关状态, 供前端决定是否启用三连击触发
        if request.method == "GET":
            return {"enabled": bool(parse.debug_variable)}
        if not parse.debug_variable:
            self.print_out("debug-variable", 404)
            response.status = 404
            return {"error": "未启用变量查询功能(需命令行参数 --debug-variable)"}
        req_data = self.get_request_json()
        code = req_data.get("code", "")
        if not isinstance(code, str) or not code.strip():
            self.print_out("debug-variable", 400)
            response.status = 400
            return {"error": "请输入Python变量或代码段"}
        # 查询命名空间: 当前模块全局变量(包含 gVar、parse 等)
        namespace = dict(vars(sys.modules[__name__]))
        stdout = io.StringIO()
        try:
            try:
                # 优先按表达式求值, 支持直接输入变量名(如 gVar.config)
                with contextlib.redirect_stdout(stdout):
                    value = eval(code, namespace)
            except SyntaxError:
                # 含赋值/语句的代码段改用 exec 执行, 并捕获 print 输出
                with contextlib.redirect_stdout(stdout):
                    exec(code, namespace)
                output = stdout.getvalue()
            else:
                printed = stdout.getvalue()
                # 表达式已通过 print 输出内容时, 不再追加无意义的 None
                if value is None and printed:
                    output = printed
                else:
                    output = printed + self.format_debug_output(value)
        except Exception:
            # 执行出错时把完整堆栈写入输出框, 便于排查
            output = traceback.format_exc()
        self.print_out("debug-variable", 200)
        return {"output": output}

    def playlist(self):
        channelid_ids = gVar.channelid_youtube_ids | gVar.channelid_bilibili_ids
        playlist_data = {}
        address = gVar.config["address"]
        address = re.sub(r"(http://)([^/:]+):80(?=/|$)", r"\1\2", address)
        # 自定义媒体rss存在且有内容, 且列表中存在已完成媒体时, 添加至播放列表最前面
        custom_media_xml = "channel_rss/custom_media.xml"
        if (
            os.path.exists(custom_media_xml)
            and os.path.getsize(custom_media_xml) > 0
            and any(
                media.get("status") == "completed"
                for media in read_custom_media()[0]
            )
        ):
            if token := gVar.config["token"]:
                url = f"{address}/channel_rss/custom_media.xml?token={token}"
            else:
                url = f"{address}/channel_rss/custom_media.xml"
            playlist_data["自定义媒体"] = url
        for channelid, name in channelid_ids.items():
            if token := gVar.config["token"]:
                url = f"{address}/channel_rss/{channelid}.xml?token={token}"
            else:
                url = f"{address}/channel_rss/{channelid}.xml"
            playlist_data[name] = url
        response.content_type = "application/json"
        self.print_out("playlist", 200)
        return playlist_data

    # 获取请求中的 JSON 数据字典
    def get_request_json(self):
        try:
            req_data = request.json or {}
        except Exception:
            return {}
        return req_data if isinstance(req_data, dict) else {}

    # 纠正自定义媒体下标, 下标无效时返回 None
    def correct_media_index(self, index, media_list):
        try:
            index = int(index)
        except (TypeError, ValueError):
            return None
        if index < 0 or index >= len(media_list):
            return None
        return index

    # 画质转数字用于比较, 后台写入非数字时按0处理, 避免列表接口报错
    def correct_media_quality(self, quality):
        try:
            return int(quality)
        except (TypeError, ValueError):
            return 0

    # 查重: 相同链接仅保留一条, 视频优先于音频, 视频画质高者优先, 且保持原有位置
    # 返回(处理方式, 下标): append新增 / update覆盖原条目 / ignore忽略本次提交
    # 下标为 None 表示列表中还没有该链接
    # 原条目抓取失败(status为failed)时同样覆盖, 便于配好cookie后重新提交重试
    def custom_media_target(self, media_list, media_url, media_type, media_quality):
        for media_index, media_item in enumerate(media_list):
            if media_item.get("url") != media_url:
                continue
            item_type = media_item.get("type")
            if media_item.get("status") == "failed" or (
                media_type == "mp4"
                and (
                    item_type == "m4a"
                    or self.correct_media_quality(media_quality)
                    > self.correct_media_quality(media_item.get("quality"))
                )
            ):
                return "update", media_index
            return "ignore", media_index
        return "append", None

    # 已存在相同且不更优的媒体, 忽略本次提交的响应
    def custom_media_repeat(self, media_type, media_list, media_index):
        self.print_out(f"custom-media {media_type} repeat", 200)
        return {
            "message": "该媒体已存在, 且画质不高于已添加的媒体",
            "data": media_list[media_index],
            "index": media_index,
            "count": len(media_list),
            "added": False,
        }

    # 校验网页提交的版本号, 防止用旧内容覆盖后台已更新的数据
    # 未提交rev时不做校验(兼容旧页面), 提交且与当前不一致时返回True表示冲突
    def media_rev_conflict(self, req_data, current_rev):
        client_rev = req_data.get("rev")
        if not isinstance(client_rev, str):
            return False
        return client_rev != current_rev

    # 版本号冲突的409响应, 同时回传最新列表, 便于网页直接重载
    def media_rev_conflict_response(self):
        media_list, current_rev = read_custom_media()
        self.print_out("custom-media", 409)
        response.status = 409
        return {
            "error": "列表已被后台更新, 请重试",
            "conflict": True,
            "list": media_list,
            "rev": current_rev,
            "busy": bool(getattr(gVar, "custom_media_busy", False)),
        }

    # 设置后台忙碌标记(网页据此禁用所有操作按钮)
    def custom_media_lock(self):
        response.content_type = "application/json"
        req_data = self.get_request_json()
        # GET 仅查询当前状态
        if request.method == "GET":
            return {"busy": bool(getattr(gVar, "custom_media_busy", False))}
        busy = req_data.get("busy")
        if not isinstance(busy, bool):
            self.print_out("custom-media-lock", 400)
            response.status = 400
            return {"error": "busy需为布尔值"}
        gVar.custom_media_busy = busy
        self.print_out(f"custom-media-lock {str(busy).lower()}", 200)
        return {"message": "忙碌标记已更新", "busy": busy}

    # 读取或添加自定义媒体(网页提交的下载任务)
    def custom_media(self):
        # 自定义媒体的媒体格式/画质/音频轨道语言可选值, 取自 config_desc 的 channel.youtube 定义,
        # 与「修改运行配置」页共用同一份数据(config_desc), 避免两处各维护一套可选值
        youtube_channel_desc = config_desc["channel"]["youtube"]
        # 媒体格式候选(m4a音频/mp4视频), 及旧列表数据中 audio/video → 新取值的映射
        custom_media_type = [
            option["value"] for option in youtube_channel_desc["media"]["options"]
        ]
        # 画质候选(144p - 4320p, 仅媒体格式为 mp4 时生效)
        custom_media_quality = [
            option["value"] for option in youtube_channel_desc["quality"]["options"]
        ]
        # 音频轨道语言候选(两位语言代码)及其默认值
        custom_media_audio_track_language = [
            option["value"]
            for option in youtube_channel_desc["audio_track_language"]["options"]
        ]
        custom_media_language_default = youtube_channel_desc["audio_track_language"][
            "default"
        ]
        # 自定义媒体支持的平台, 仅允许YouTube及哔哩哔哩的视频链接
        custom_media_hostname = ["youtube.com", "youtu.be", "bilibili.com", "b23.tv"]
        # 从粘贴的文本中提取链接, 兼容【标题】链接 复制打开哔哩哔哩…等应用的分享文本
        custom_media_url_pattern = re.compile(
            r"https?://[^\s\"'<>()（）【】\[\]，。、！？；：]+"
        )
        # 规范化后的视频链接格式, 与 normalize_video_url 的输出保持一致
        # 用于过滤非视频页面(频道/收藏夹等)及链接前后多余的字符
        custom_media_video_pattern = re.compile(
            r"^(?:https://www\.youtube\.com/watch\?v=[\w-]{11}"
            r"|https://www\.bilibili\.com/video/(?:BV\w{10}|av\d+)/)$"
        )
        # 设置响应头为 application/json
        response.content_type = "application/json"
        # GET 请求返回已添加的自定义媒体列表
        if request.method == "GET":
            media_list, current_rev = read_custom_media()
            return {
                "list": media_list,
                "count": len(media_list),
                "rev": current_rev,
                "busy": bool(getattr(gVar, "custom_media_busy", False)),
                # 下发三个下拉(desc数据源自config_desc的channel.youtube), 供前端构建及校验
                "desc": {
                    key: youtube_channel_desc[key]
                    for key in ("media", "quality", "audio_track_language")
                },
            }
        # POST 请求添加自定义媒体至列表文件
        req_data = self.get_request_json()
        # 从粘贴内容中提取链接(兼容分享文本), 再格式化(统一YouTube及哔哩哔哩的多种链接格式)
        raw_url = str(req_data.get("url", "")).strip()
        url_match = custom_media_url_pattern.search(raw_url)
        media_url, video_id = normalize_video_url(url_match.group(0) if url_match else raw_url)
        media_type = str(req_data.get("type", "")).strip()
        media_quality = str(req_data.get("quality", "")).strip()
        # 音频轨道语言: 未提交时按 config_desc 的默认值兜底(与频道配置口径一致)
        media_language = (
            str(req_data.get("audio_track_language", "")).strip()
            or custom_media_language_default
        )
        if not media_url:
            self.print_out("custom-media", 400)
            response.status = 400
            return {"error": "请填写媒体链接"}
        if not media_url.startswith(("http://", "https://")):
            self.print_out("custom-media", 400)
            response.status = 400
            return {"error": "媒体链接需以 http:// 或 https:// 开头"}
        # 校验格式化后的链接: 仅接受YouTube及哔哩哔哩的视频链接, 并过滤多余字符
        if not custom_media_video_pattern.match(media_url):
            self.print_out("custom-media", 400)
            response.status = 400
            media_hostname = urlparse(media_url).netloc.lower()
            if "b23.tv" in media_hostname:
                # 短链需联网解析, 解析失败时无法取到视频ID
                return {"error": "b23.tv短链解析失败, 请改用完整的视频链接"}
            if any(hostname in media_hostname for hostname in custom_media_hostname):
                # 平台正确但未取到视频ID, 多为频道/收藏夹等非视频页面
                return {"error": "链接中未识别到视频ID, 请粘贴纯视频链接"}
            return {"error": "仅支持YouTube及哔哩哔哩的视频链接"}
        if media_type not in custom_media_type:
            self.print_out("custom-media", 400)
            response.status = 400
            return {"error": "请选择正确的媒体格式(m4a音频或mp4视频)"}
        if media_type == "mp4":
            if media_quality not in custom_media_quality:
                self.print_out("custom-media", 400)
                response.status = 400
                return {"error": "请选择正确的视频画质(144p - 4320p)"}
        else:
            # 音频格式无需画质
            media_quality = ""
        if media_language not in custom_media_audio_track_language:
            self.print_out("custom-media", 400)
            response.status = 400
            return {"error": "请选择正确的音频轨道语言"}
        # 将链接、媒体格式、画质及音频轨道语言以字典形式添加至列表, 状态默认为准备中
        custom_media_message = {
            "url": media_url,
            "type": media_type,
            "quality": media_quality,
            "audio_track_language": media_language,
            "status": "preparing",
            "id": video_id,
        }
        # 读取列表并校验版本号, 冲突时放弃本次写入, 避免用旧内容覆盖后台已更新的数据
        media_list, current_rev = read_custom_media()
        if self.media_rev_conflict(req_data, current_rev):
            return self.media_rev_conflict_response()
        # 查重: 相同链接仅保留一条, 视频优先于音频, 视频画质高者优先, 且保持原有位置
        # 抓取媒体信息需要联网, 先判一次可让"已存在"的提交直接返回, 免去无谓等待
        action, media_index = self.custom_media_target(
            media_list, media_url, media_type, media_quality
        )
        if action == "ignore":
            return self.custom_media_repeat(media_type, media_list, media_index)
        # 联网抓取 title 等字段, 耗时数秒至数十秒, 失败时条目状态记为 failed
        media_fields, fail_reason = get_custom_media_info(
            media_url, video_id, media_type, media_quality, media_language
        )
        # 抓取期间列表可能已被后台写入, 重新读取最新列表再落盘以保留其修改
        # 此处按最新内容合并即可, 不再比对版本号, 否则会白费刚才的抓取
        media_list, current_rev = read_custom_media()
        action, media_index = self.custom_media_target(
            media_list, media_url, media_type, media_quality
        )
        if action == "ignore":
            return self.custom_media_repeat(media_type, media_list, media_index)
        if fail_reason is None:
            # 抓取到的字段全部写入, 状态保持准备中, 等待后台下载流程更新
            custom_media_message.update(media_fields)
        else:
            # 抓取失败同样保留条目, 状态改写为失败, 网页据 fail_reason 提示失败原因
            custom_media_message["status"] = "failed"
            custom_media_message["error"] = fail_reason
        if action == "update":
            # 整条覆盖以保持原位置, 旧的进度等字段已不适用, 需重新处理
            media_list[media_index] = custom_media_message
        else:
            media_list.append(custom_media_message)
        save_custom_media(media_list)
        if fail_reason:
            self.print_out(f"custom-media {media_type} format-failed", 200)
        elif action == "update":
            self.print_out(f"custom-media {media_type} update", 200)
        else:
            self.print_out(f"custom-media-{media_type}", 200)
        return {
            "message": "已更新相同媒体" if action == "update" else "添加成功",
            "data": custom_media_message,
            "index": media_index,
            "count": len(media_list),
            "added": True,
            # 抓取失败时回传原因, 由网页显示在操作提示区
            "fail_reason": fail_reason,
        }

    # 排序自定义媒体
    def custom_media_reorder(self):
        # 设置响应头为 application/json
        response.content_type = "application/json"
        req_data = self.get_request_json()
        media_list, current_rev = read_custom_media()
        if self.media_rev_conflict(req_data, current_rev):
            return self.media_rev_conflict_response()
        old_index = self.correct_media_index(req_data.get("old_index"), media_list)
        if old_index is None:
            self.print_out("custom-media-reorder", 404)
            response.status = 404
            return {"error": "待排序的自定义媒体不存在"}
        new_index = req_data.get("new_index")
        try:
            new_index = int(new_index)
        except (TypeError, ValueError):
            self.print_out("custom-media-reorder", 400)
            response.status = 400
            return {"error": "目标位置无效"}
        if new_index < 0 or new_index >= len(media_list):
            self.print_out("custom-media-reorder", 400)
            response.status = 400
            return {"error": "目标位置超出范围"}
        # 移动指定媒体至目标位置
        media_list.insert(new_index, media_list.pop(old_index))
        save_custom_media(media_list)
        self.print_out("custom-media-reorder", 200)
        return {
            "message": "排序成功",
            "count": len(media_list),
        }

    # 删除自定义媒体
    def custom_media_remove(self):
        # 设置响应头为 application/json
        response.content_type = "application/json"
        req_data = self.get_request_json()
        media_list, current_rev = read_custom_media()
        if self.media_rev_conflict(req_data, current_rev):
            return self.media_rev_conflict_response()
        media_index = self.correct_media_index(req_data.get("index"), media_list)
        if media_index is None:
            self.print_out("custom-media-remove", 404)
            response.status = 404
            return {"error": "自定义媒体不存在"}
        media_message = media_list.pop(media_index)
        save_custom_media(media_list)
        self.print_out("custom-media-remove", 200)
        return {
            "message": "删除成功",
            "data": media_message,
            "count": len(media_list),
        }

bottle_app_instance = bottle_app()
