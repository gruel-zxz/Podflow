# Podflow/httpfs/app_bottle.py
# coding: utf-8

import os
import hashlib
from datetime import datetime
import cherrypy
from bottle import Bottle, abort, redirect, request, static_file, response
from Podflow import gVar
from Podflow.upload.login import create
from Podflow.basic.write_log import write_log
from Podflow.upload.time_key import check_time_key


class bottle_app:
    # Bottle和Cherrypy初始化模块
    def __init__(self):
        self.app_bottle = Bottle()  # 创建 Bottle 应用
        self.bottle_print = []  # 存储打印日志
        self.setup_routes()  # 设置路由
        self.logname = "httpfs.log"  # 默认日志文件名
        self.http_fs = False

    def setup_routes(self, upload=False):
        # 设置/favicon.ico路由，回调函数为favicon
        self.app_bottle.route("/favicon.ico", callback=self.favicon)
        # 设置根路由，回调函数为home
        self.app_bottle.route("/", callback=self.home)
        # 设置/shutdown路由，回调函数为shutdown
        self.app_bottle.route("/shutdown", callback=self.shutdown)
        if upload:
            self.app_bottle.route("/newuser", callback=self.new_user)
            self.app_bottle.route("/login", callback=self.login)
        else:
            # 设置其他路由，回调函数为serve_static
            self.app_bottle.route("/<filename:path>", callback=self.serve_static)

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
    def add_bottle_print(self, client_ip, filename, status):
        # 后缀
        suffixs = [".mp4", ".m4a", ".xml", ".ico"]
        # 设置状态码对应的颜色
        status_colors = {
            200: "\033[32m",  # 绿色 (成功)
            401: "\033[31m",  # 红色 (未经授权)
            404: "\033[35m",  # 紫色 (未找到)
            303: "\033[33m",  # 黄色 (重定向)
            206: "\033[36m",  # 青色 (部分内容)
        }
        # 默认颜色
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
        self.bottle_print.append(f"{now_time}|{client_ip} {filename} {status}")

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
    def print_out(self, filename, status):
        client_ip = request.remote_addr
        client_port = request.environ.get("REMOTE_PORT")
        if client_port:
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
            cherrypy.engine.exit()  # 使用 CherryPy 提供的停止功能来关闭服务器
            return "Shutting down..."  # 返回关机响应
        else:
            self.print_out("shutdown", 401)  # 如果验证失败, 输出 401 状态
            abort(401, "Unauthorized: Invalid Token")  # 返回未经授权错误

    # 路由处理 favicon 请求
    def favicon(self):
        self.print_out("favicon.ico", 303)  # 输出访问 favicon 的日志
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
                    return static_file(filename, root=".")
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
        seed = "We need to generate an account password for uploading non one-time items that need to be saved."
        token = request.query.get("token")  # 获取请求中的 Token
        response.content_type = 'application/json'
        
        if check_time_key(token, seed):  # 验证 Token
            username, password = create()  # 生成用户名和密码
            self.print_out("newuser", 200)
            return {
                "code":0,
                "message":"Get New Username And Password Success",
                "data": {
                    "username": username,
                    "password": password,
                },
            }
        else:
            self.print_out("newuser", 401)
            return {
                "code":-1,
                "message":"Unauthorized: Invalid Token",
            }

    # 路由处理登陆请求
    def login(self):
        upload_data = gVar.upload_data
        username = request.query.get("username")
        password = request.query.get("password")
        if username in upload_data:
            if upload_data[username] == password:
                self.print_out("login", 200)
                return {
                    "code":0,
                    "message":"Login Success",
                }
            else:
                self.print_out("login", 401)
                return {
                    "code":-3,
                    "message":"Password Error",
                }
        else:
            self.print_out("login", 401)
            return {
                "code":-2,
                "message":"Username Error",
            }


bottle_app_instance = bottle_app()
