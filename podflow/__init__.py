# podflow/__init__.py
# coding: utf-8

# 默认参数
default_config = {
    "preparation_per_count": 100,  # 获取媒体信息每组数量
    "completion_count": 100,  # 媒体缺失时最大补全数量
    "retry_count": 5,  # 媒体下载重试次数
    "url": "http://127.0.0.1",  # HTTP共享地址
    "port": 8000,  # HTTP共享端口
    "port_in_url": True,  # HTTP共享地址是否包含端口
    "httpfs": False,  # HTTP共享日志
    "title": "Podflow",  # 博客的名称
    "filename": "Podflow",  # 主XML的文件名称
    "link": "https://github.com/gruel-zxz/podflow",  # 博客主页
    "description": "在iOS平台上借助workflow和a-shell搭建专属的播客服务器。",  # 博客信息
    "icon": "https://raw.githubusercontent.com/gruel-zxz/podflow/main/Podflow.png",  # 博客图标
    "category": "TV &amp; Film",  # 博客类型
    "token": "",  # token认证, 如为null或""将不启用token
    "delete_incompletement": False,  # 是否删除下载中断媒体(下载前处理流程)
    "remove_media": True,  # 是否删除无用的媒体文件
    "upload": False,  # 是否将长期媒体进行上传
    "channelid_youtube": {  # Youtube频道列表
        "youtube": {
            "update_size": 15,  # 每次获取频道媒体数量
            "id": "UCBR8-60-B28hp2BmDPdntcQ",  # 频道ID
            "title": "YouTube",  # 频道名称
            "quality": "480",  # 媒体分辨率(仅在media为视频时有效)
            "last_size": 50,  # 媒体保留数量
            "media": "m4a",  # 下载媒体类型
            "DisplayRSSaddress": False,  # 是否在Print中显示子博客地址
            "InmainRSS": True,  # 是否在主博客中
            "QRcode": False,  # 是否显示子博客地址二维码(仅在DisplayRSSaddress为True时有效)
            "BackwardUpdate": False,  # 是否向后更新
            "BackwardUpdate_size": 3,  # 向后更新数量(仅在BackwardUpdate为True时有效)
            "want_retry_count": 8,  # 媒体获取失败后多少次后重试(小于等于该数量时将一直重试)
            "title_change": [  # 标题文本修改(默认为无, 可多个条件，以列表形式存在)
                {  # match和url参数至少有一个, 如都有将同时生效
                    "mode": "add-left",  # 修改模式(add-left: 开头添加, add-right: 结尾添加, replace: 内容替换)
                    "match": "",  # 需要匹配的规则(为正则表达式)
                    "url": "https://www.youtube.com/playlist?list=...",  # 播放列表网址(只适用于YouTube频道, 并且不适用replace模式, 选择后会失效)
                    "text": "",  # 需要替换或添加的文本
                },
                {
                    "mode": "add-right",
                    "match": "",
                    "url": "",
                    "text": "",
                },
            ],
            "NoShorts": False,  # 是否不下载Shorts媒体
        },
    },
    "channelid_bilibili": {  # 哔哩哔哩频道列表
        "哔哩哔哩弹幕网": {
            "update_size": 25,
            "id": "8047632",
            "title": "哔哩哔哩弹幕网",
            "quality": "480",
            "last_size": 100,
            "media": "m4a",
            "DisplayRSSaddress": False,
            "InmainRSS": True,
            "QRcode": False,
            "BackwardUpdate": False,
            "BackwardUpdate_size": 3,
            "want_retry_count": 8,
            "title_change": {
                "mode": "replace",
                "match": "",
                "text": "",
            },
            "AllPartGet": False,  # 是否提前获取分P或互动视频(建议update_size大于5时使用, 如果该变量不存在时, 默认update_size大于5时开启)
        },
    },
}
# 如果InmainRSS为False或频道有更新则无视DisplayRSSaddress的状态, 都会变为True。


# 全局变量
class Application_gVar:
    def __init__(self):
        self.config = {}  # 配置文件字典
        self.channelid_youtube = {}  # YouTube频道字典
        self.channelid_bilibili = {}  # 哔哩哔哩频道字典
        self.channelid_youtube_ids = {}  # YouTube频道ID字典
        self.channelid_youtube_ids_original = {}  # 原始YouTube频道ID字典
        self.channelid_bilibili_ids = {}  # 哔哩哔哩频道ID字典
        self.channelid_bilibili_ids_original = {}  # 原始哔哩哔哩频道ID字典

        self.server_process_print_flag = ["keep"]  # httpserver进程打印标志列表
        self.update_generate_rss = True  # 更新并生成rss布朗值
        self.displayed_QRcode = []  # 已显示二维码列表

        self.bilibili_data = {}  # 哔哩哔哩data字典
        self.youtube_cookie = {}  # YouTube cookie字典
        self.channelid_youtube_ids_update = {}  # 需更新的YouTube频道字典
        self.youtube_content_ytid_update = {}  # 需下载YouTube视频字典
        self.youtube_content_ytid_backward_update = {}  # 向后更新需下载YouTube视频字典
        self.channelid_youtube_rss = {}  # YouTube频道最新Rss Response字典
        self.channelid_bilibili_ids_update = {}  # 需更新的哔哩哔哩频道字典
        self.bilibili_content_bvid_update = {}  # 需下载哔哩哔哩视频字典
        self.channelid_bilibili_rss = {}  # 哔哩哔哩频道最新Rss Response字典
        self.bilibili_content_bvid_backward_update = {}  # 向后更新需下载哔哩哔哩视频字典
        self.video_id_failed = []  # YouTube&哔哩哔哩视频下载失败列表
        self.video_id_update_format = {}  # YouTube和哔哩哔哩视频下载的详细信息字典
        self.hash_rss_original = ""  # 原始rss哈希值文本
        self.xmls_original = {}  # 原始xml信息字典
        self.xmls_original_fail = []  # 未获取原始xml频道列表
        self.youtube_xml_get_tree = {}  # YouTube频道简介和图标字典
        self.all_youtube_content_ytid = {}  # 所有YouTube视频id字典
        self.all_bilibili_content_bvid = {}  # 所有哔哩哔哩视频id字典
        self.all_items = {}  # 更新后所有item明细字典
        self.overall_rss = ""  # 更新后的rss文本
        self.make_up_file_format = {}  # 补全缺失媒体字典
        self.make_up_file_format_fail = {}  # 补全缺失媒体失败字典

        self.upload_original = []  # 原始上传信息字典
        self.upload_data = {}  # 上传用户账号密码字典

        self.shortcuts_url = {}  # 输出至shortcut的url字典
        
        self.index_message = {  # 图形界面显示信息字典
            "podflow": [],  # 主窗口信息列表
            "http": [],  # httpfs窗口信息列表
            "enter": True,  # 是否换行
        }


# 参数变量
class Application_parse:
    def __init__(self):
        self.shortcuts_url_original = []
        self.argument = ""
        self.update_num = -1
        self.time_delay = 0
        self.config = ""
        self.period = 1
        self.file = ""
        self.httpfs = False
        self.index = False


# 创建 Application 类的实例
gVar = Application_gVar()
parse = Application_parse()
