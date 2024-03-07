import subprocess
import threading
import time

# 运行简单的 HTTP 服务器
server_process = subprocess.Popen(["python3", "-m", "RangeHTTPServer"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def server_process_print(stop_flag):
    need_keep = ""
    while True:
        output = server_process.stdout.readline().decode().strip()
        if need_keep == "":
            need_keep = output
        else:
            need_keep += f"\n{output}"
        if stop_flag[0] == "keep":
            print(need_keep)
            need_keep = ""
        if stop_flag[0] == "end":
            break

def server_process_stop(stop_flag):
    time.sleep(10)  # 等待一段时间后终止服务器
    # 关闭 HTTP 服务器进程
    stop_flag[0] = "pause"
    time.sleep(30)
    stop_flag[0] = "keep"
    time.sleep(30)
    server_process.terminate()
    stop_flag[0] = "end"

# 创建共享的标志变量
stop_flag = ["keep"]

# 创建两个线程分别执行输出和终止操作
prepare_1 = threading.Thread(target=server_process_print, args=(stop_flag,))
prepare_2 = threading.Thread(target=server_process_stop, args=(stop_flag,))

# 启动两个线程
prepare_1.start()
prepare_2.start()

# 等待两个线程结束
prepare_1.join()
prepare_2.join()