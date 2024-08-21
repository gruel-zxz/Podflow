import http.server
import socketserver
import os
import re

def create_custom_http_server(port=8000, allowed_paths=["YouTube.xml", "channel_audiovisual", "channel_rss"]):
    class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        # 翻译路径方法，用于检查请求路径是否在允许的路径列表中
        def translate_path(self, path):
            # 获取当前请求路径的绝对路径
            result_path = super().translate_path(path)
            abs_result_path = os.path.abspath(result_path)
            # 检查请求路径是否在允许的路径列表中
            for allowed_path in allowed_paths:
                abs_allowed_path = os.path.abspath(allowed_path)
                if abs_result_path == abs_allowed_path or abs_result_path.startswith(abs_allowed_path + os.sep):
                    return abs_result_path
            return None  # 如果路径不在允许的路径列表中，返回None

        # 处理GET请求
        def do_GET(self):
            translated_path = self.translate_path(self.path)
            if translated_path is None:
                self.send_error(403, "Forbidden")  # 返回403禁止访问
                return

            # 检查请求的路径是否在允许的路径列表中
            if any(translated_path.startswith(os.path.abspath(allowed_path)) for allowed_path in allowed_paths):
                self.handle_range_request(translated_path)
            else:
                self.send_error(403, "Forbidden")

        # 处理范围请求
        def handle_range_request(self, file_path):
            range_header = self.headers.get('Range', None)
            if range_header:
                range_match = re.match(r'bytes=(\d+)-(\d+)?', range_header)
                if range_match:
                    first_byte, last_byte = range_match.groups()
                    first_byte = int(first_byte)
                    last_byte = int(last_byte) if last_byte else None
                    # 检查文件是否存在且合法
                    if not os.path.exists(file_path) or not os.path.isfile(file_path):
                        self.send_error(404, "File not found")
                        return
                    file_size = os.path.getsize(file_path)
                    if last_byte is None or last_byte >= file_size:
                        last_byte = file_size - 1
                    if first_byte >= file_size:
                        self.send_error(416, "Requested Range Not Satisfiable")
                        return
                    self.send_response(206)
                    self.send_header('Content-Type', self.guess_type(file_path))
                    self.send_header('Content-Range', f'bytes {first_byte}-{last_byte}/{file_size}')
                    self.send_header('Content-Length', str(last_byte - first_byte + 1))
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()
                    with open(file_path, 'rb') as f:
                        f.seek(first_byte)
                        self.wfile.write(f.read(last_byte - first_byte + 1))
                else:
                    self.send_error(400, "Bad Request")
            else:
                super().do_GET()

    print(f"Serving at port {port}")
    with socketserver.TCPServer(("", port), CustomHTTPRequestHandler) as httpd:
        httpd.serve_forever()

# 创建并运行自定义HTTP服务器，允许访问的路径为 "data" 和 "index.html"
create_custom_http_server(allowed_paths=["YouTube.xml", "channel_audiovisual", "channel_rss", "Podflow.xml"])
