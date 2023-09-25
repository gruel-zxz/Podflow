import subprocess
import time

# 启动 RangeHTTPServer
server_process = subprocess.Popen(["python3", "-m", "http.server", "--cgi"])

# 延时三分钟
time.sleep(180)

# 关闭服务器
server_process.terminate()

