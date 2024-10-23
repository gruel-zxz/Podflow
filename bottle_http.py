from bottle import Bottle, run, static_file, abort, redirect, request
import os
import hashlib

app = Bottle()

# 定义要共享的文件路径
shared_files = {
    'Podflow': 'Podflow.xml',
    'Podflow.xml': 'Podflow.xml',
    'podflow': 'Podflow.xml',
    'podflow.xml': 'Podflow.xml',
}

# 预设 Token
VALID_TOKEN = ""  # 你的 Token

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
    # 尝试从请求头检查 Token
    token = request.query.get('token')
    if token_judgment(token, VALID_TOKEN):
        return "hello world"
    else:
        abort(401, "Unauthorized: Invalid Token")
        
@app.route('/favicon.ico')
def favicon():
    return redirect('https://raw.githubusercontent.com/gruel-zxz/podflow/main/Podflow.png')

@app.route('/<filename:path>')
def serve_static(filename):
    # 尝试从请求头检查 Token
    token = request.query.get('token')
    def file_exist(token, VALID_TOKEN, filename, foldername=""):
        if token_judgment(token, VALID_TOKEN, filename, foldername):
            if os.path.exists(filename):
                return static_file(filename, root=".")
            else:
                abort(404, "File not found")
        else:
            abort(401, "Unauthorized: Invalid Token")
    if filename in ['channel_audiovisual/', 'channel_rss/']:
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
        abort(404, "File not found")

def run_bottle():
    run(app, host='0.0.0.0', port=8000, debug=True, reloader=False, quiet=False)

run_bottle()
