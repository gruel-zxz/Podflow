from bottle import Bottle, run, static_file, abort, redirect, request
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import threading
import os
import signal
import time
import hashlib
from datetime import datetime
from bottle import response
import sys

# 预设 Token
Shutdown_VALID_TOKEN = "shut"
VALID_TOKEN = ""  # 你的 Token
bottle_filename = "Podflow"
channelid_bilibili_ids = {'326499679': '哔哩哔哩漫画', '21738912391': '测试', '3393923': '无无无无语森', '1839002753': '鹿火CAVY', '122879': '敖厂长', '9448580': 'NOV姐姐'}
channelid_youtube_ids = {'UCBR8-60-B28hp2BmDPdntcQ': 'youtube', 'UCghLs6s95LrBWOdlZUCH4qw': 'stone记', 'UC3elWG-AxVvIF2_xPQb1rkQ': '四季妈妈—小龙', 'UCMUnInmOkrWN4gof9KlhNmQ': '老高與小茉 Mr & Mrs Gao', 'UCp1nO1bgVwks9b5EhKQGVag': '幻海航行--science fiction', 'UCXWy8yrS4WKhzbp36lW214w': '绝密研究所', 'UCmOVUFkam162EJ48KfQaIyg': 'stone pistol', 'UC85kpcAcVipOQQ7EEHbX55w': '佬K奇谈', 'UC9RS8EzXdRJyYDkwtcsWOuA': 'TenGuSan', 'UCXWy8yrS4WKhzbp36lW2141': '测试', 'UC-hTwjkGlNB5vyR6qccXr7A': '王竹子的SM教学频道', 'UCjcqM5ojQOnQSo0-PbADPgQ': 'BracedLife'}
server_process_print_flag = ["keep"]

app = Bottle()

# 定义要共享的文件路径
shared_files = {
    bottle_filename: f'{bottle_filename}.xml',
    f'{bottle_filename}.xml': f'{bottle_filename}.xml',
    bottle_filename.lower(): f'{bottle_filename}.xml',
    f'{bottle_filename.lower()}.xml': f'{bottle_filename}.xml',
}

bottle_channelid = channelid_youtube_ids | channelid_bilibili_ids | {"channel_audiovisual/": "", "channel_rss/": ""}

# 打印列表
bottle_print = []

# 判断token是否正确模块
def token_judgment(token, VALID_TOKEN="", filename="", foldername=""):
    if foldername == 'channel_audiovisual/':
        if VALID_TOKEN == "" and token == hashlib.sha256(f"{filename}".encode()).hexdigest():
            return True
        elif token == hashlib.sha256(f"{VALID_TOKEN}/{filename}".encode()).hexdigest():
            return True
        else:
            return False
    else:
        if VALID_TOKEN == "":
            return True
        elif token == VALID_TOKEN:
            return True
        else:
            return False

@app.route('/')
def home():
    # 打印模块
    def print_out(status):
        # 获取客户端的 IP 地址
        client_ip = request.remote_addr
        # 获取请求的端口号
        client_port = request.environ.get('REMOTE_PORT')
        if client_port:
            client_ip = f"{client_ip}:{client_port}"
        bottle_print.append(f"{datetime.now().strftime('%H:%M:%S')}|{client_ip} / {status}")
        if server_process_print_flag[0] == "keep" and bottle_print:
            print('\n'.join(bottle_print))
    # 尝试从请求头检查 Token
    token = request.query.get('token')
    if token_judgment(token, VALID_TOKEN):
        print_out(200)
        return "hello world"
    else:
        print_out(401)
        abort(401, "Unauthorized: Invalid Token")

@app.route('/shutdown')
def shutdown():
    # 打印模块
    def print_out(status):
        # 获取客户端的 IP 地址
        client_ip = request.remote_addr
        # 获取请求的端口号
        client_port = request.environ.get('REMOTE_PORT')
        if client_port:
            client_ip = f"{client_ip}:{client_port}"
        bottle_print.append(f"{datetime.now().strftime('%H:%M:%S')}|{client_ip} shutdown {status}")
        if server_process_print_flag[0] == "keep" and bottle_print:
            print('\n'.join(bottle_print))
    # 尝试从请求头检查 Token
    token = request.query.get('token')
    if token_judgment(token, Shutdown_VALID_TOKEN):
        response.status = 200
        print_out(200)
        tornado_loop.add_callback(tornado_loop.stop)  # 使用 add_callback 确保安全停止
        return "Shutting down..."
    else:
        print_out(401)
        abort(401, "Unauthorized: Invalid Token")

@app.route('/favicon.ico')
def favicon():
    # 获取客户端的 IP 地址
    client_ip = request.remote_addr
    # 获取请求的端口号
    client_port = request.environ.get('REMOTE_PORT')
    if client_port:
        client_ip = f"{client_ip}:{client_port}"
    bottle_print.append(f"{datetime.now().strftime('%H:%M:%S')}|{client_ip} favicon.ico 303")
    if server_process_print_flag[0] == "keep" and bottle_print:
        print('\n'.join(bottle_print))
    return redirect('https://raw.githubusercontent.com/gruel-zxz/podflow/main/Podflow.png')

@app.route('/<filename:path>')
def serve_static(filename):
    # 尝试从请求头检查 Token
    token = request.query.get('token')
    # 打印模块
    def print_out(filename, status):
        # 获取客户端的 IP 地址
        client_ip = request.remote_addr
        # 获取请求的端口号
        client_port = request.environ.get('REMOTE_PORT')
        if client_port:
            client_ip = f"{client_ip}:{client_port}"
        # 将id替换为名称
        for bottle_channelid_key, bottle_channelid_value in bottle_channelid.items():
            filename = filename.replace(bottle_channelid_key, bottle_channelid_value)
            if status == 200 and request.headers.get('Range'):
                status = 206
        bottle_print.append(f"{datetime.now().strftime('%H:%M:%S')}|{client_ip} {filename} {status}")
        if server_process_print_flag[0] == "keep" and bottle_print:
            print('\n'.join(bottle_print))
    # 获取文件模块
    def file_exist(token, VALID_TOKEN, filename, foldername=""):
        if token_judgment(token, VALID_TOKEN, filename, foldername):
            if os.path.exists(filename):
                print_out(filename, 200)
                return static_file(filename, root=".")
            else:
                print_out(filename, 404)
                abort(404, "File not found")
        else:
            print_out(filename, 401)
            abort(401, "Unauthorized: Invalid Token")
    
    if filename in ['channel_audiovisual/', 'channel_rss/']:
        print_out(filename, 404)
        abort(404, "File not found")
    elif filename.startswith('channel_audiovisual/'):
        return file_exist(token, VALID_TOKEN, filename, "channel_audiovisual/")
    elif filename.startswith('channel_rss/') and filename.endswith(".xml"):
        return file_exist(token, VALID_TOKEN, filename)
    elif filename.startswith('channel_rss/'):
        return file_exist(token, VALID_TOKEN, f"{filename}.xml")
    elif filename in shared_files:
        return file_exist(token, VALID_TOKEN, shared_files[filename])
    else:
        print_out(filename, 404)
        abort(404, "File not found")

# 创建 Tornado HTTP 服务器
wsgi_app = WSGIContainer(app)
http_server = HTTPServer(wsgi_app)
http_server.listen(8080)

# 创建一个独立的 IOLoop 实例
tornado_loop = IOLoop()

# 定义一个函数来运行 Tornado 的 I/O 循环
def start_tornado():
    tornado_loop.start()

# 创建一个线程来运行 Tornado 事件循环
tornado_thread = threading.Thread(target=start_tornado)
tornado_thread.start()
tornado_thread.join()
print("Tornado server stopped.")