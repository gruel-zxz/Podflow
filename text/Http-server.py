import subprocess
import time

# 启动 RangeHTTPServer
server_process = subprocess.Popen(["python3", "-m", "http.server", "--cgi"])
# 延时
time.sleep(60)
# 关闭服务器
server_process.terminate()

