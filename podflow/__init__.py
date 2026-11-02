# podflow/__init__.py
# coding: utf-8

import threading
import copy

# default_config 不再手工维护, 由下方 config_desc 自动生成（唯一来源）。
#   生成函数: build_default_config()（见文件末尾）
#   初始频道: config_desc["_init_channels"] 声明首启写入 config.json 的频道名
#   出厂初值: config_desc 各条目的 "init"（与 "default" 不同时给出, 如频道 id/title/title_change）
# 如果InmainRSS为False或频道有更新则无视DisplayRSSaddress的状态, 都会变为True。


# 前端「修改运行配置」页的字段显示定义（config.js 据此渲染与校验, 唯一来源）:
#   default : 默认值(新建频道模板 / 补齐缺失字段时使用; 无 default 表示该字段不写入默认配置)
#   init    : 可选, 出厂初值(仅当与 default 不同时给出; 用于生成 default_config,
#             如示例频道的 id/title/title_change); default_config 由本字典自动生成
#   type    : 字段类型: int / bool / str / url / select / array / regex / object
#   options : type 为 select 时的候选值(元素可为字符串或 {value, label})
#   readonly: 是否只读(仅后台生成, 前端不可编辑)
#   desc    : 字段说明(field-hint)
# 约束条件(全部来自本字典, config.js 不做任何硬编码), 可用的条件键:
#   min / max  : int 的范围
#   pattern    : str / url 需匹配的正则(写为 Python 原始字符串 r"...")
#   min_length : str 的最小长度
#   required   : 必填字段(缺少时报错, 如频道 id)
#   when       : {key, value} 仅当所在对象[key] === value 时才校验该字段(如 BackwardUpdate_size / quality 依赖 media)
#   mode_in    : {key, values, msg} 仅当所在对象[key] 属于 values 时该字段才有效
#                (如 rule.url 依赖 rule.mode, 不支持 replace 模式)
#   websites   : 字段仅对列出的网站生效(如 rule.url 仅适用于 youtube)
#   warn       : 校验失败仅提示, 不阻止保存
#   allow_empty: 值为 true 时, 空字符串视为合法(未填写的可选字段, 如 title_change_rule.url)
#   err_if     : {key, value} 校验失败时, 若所在对象[key] === value 则报错(msg_err),
#                否则仅提示(msg)（兼容旧声明; 新字段统一用 when / when_show 表达生效条件）
#   msg/msg_err: 校验失败时的提示文本(缺省按约束自动生成, 如 int 的范围 / select 的选项列表)
#   trim_to    : 保存前将字段值截取为 pattern 匹配到的部分
#                (主 url 仅保留 协议://主机; youtube id 截取前 24 位)
#   min_field  : 保存前将 int 字段值取 max(自身, 所在对象[min_field])（last_size 不小于 update_size）
#   force      : {when_key, when_value, set} 保存前当所在对象[when_key] === when_value 时,
#                强制该字段值为 set（InmainRSS 为 False 时 DisplayRSSaddress 强制为 True）
#   label      : 可选, 规则类列表字段的小节标题(如 title_change 为「标题修改规则」)
#   rules      : 可选, type 为 array 的规则列表字段, 声明其元素字段定义所在的作用域
#                (顶层键名, 如 title_change_rule); 无 rules 的 array 仅作只读 JSON 展示
#   schema     : 可选, type 为 object(嵌套配置对象)时, 声明子对象字段定义所在的作用域
#                (顶层键名, 同规则作用域规则); 不声明时子字段按当前作用域定义展示/校验
# 规则作用域(顶层除 main/channel 外的键, 如 title_change_rule):
#   - 以 "_" 开头的键为元数据, 不会渲染为字段; 其中 _meta 可声明元素的必备结构:
#     {require: [必含字段], any_of: [[至少含其一的一组字段]], message: 不满足时的提示}
# 添加/删除配置项时只需改本字典: default_config 由本字典自动生成（build_default_config）;
# 新增字段给出 default（及有需要时的 init）即可, 首启 config.json 会随之一致。
# 首启写入 config.json 的初始频道名由 config_desc["_init_channels"] 声明。
config_desc = {
    # 首启写入 config.json 的初始频道（站点名 -> 频道名列表）; "_" 开头为元数据, 前端不渲染
    "_init_channels": {
        "youtube": ["youtube"],
        "bilibili": ["哔哩哔哩弹幕网"],
    },
    "main": {
        "title": {"default": "Podflow", "type": "str", "desc": "播客的名称"},
        "filename": {"default": "Podflow", "type": "str", "desc": "主XML的文件名称"},
        "link": {
            "default": "https://github.com/gruel-zxz/podflow",
            "type": "url",
            "pattern": r"^(https?|ftp)://[^\s/$.?#].[^\s]*$",
            "msg": "需为有效网址（以 http://、https:// 或 ftp:// 开头）",
            "desc": "播客主页",
        },
        "description": {
            "default": "在iOS平台上借助workflow和a-shell搭建专属的播客服务器。",
            "type": "str",
            "desc": "播客信息",
        },
        "icon": {
            "default": "https://raw.githubusercontent.com/gruel-zxz/podflow/main/Podflow.png",
            "type": "url",
            "pattern": r"^(https?|ftp)://[^\s/$.?#].[^\s]*$",
            "msg": "需为有效网址（以 http://、https:// 或 ftp:// 开头）",
            "desc": "播客图标",
        },
        "category": {
            "default": "TV &amp; Film",
            "type": "select",
            "desc": "播客类型",
            # 存入配置的是英文 value（含 & 的选项存转义形式, 与 xml_rss 输出一致）;
            # label 为「英文 中文」, 前端下拉里中文灰显（见 config.js 自定义双语下拉）
            "options": [
                {"value": "Arts", "label": "Arts 艺术"},
                {"value": "Business", "label": "Business 商务"},
                {"value": "Comedy", "label": "Comedy 喜剧"},
                {"value": "Education", "label": "Education 教育"},
                {"value": "Fiction", "label": "Fiction 小说"},
                {"value": "Government", "label": "Government 政府"},
                {"value": "History", "label": "History 历史"},
                {
                    "value": "Health &amp; Fitness",
                    "label": "Health & Fitness 健康与健身",
                },
                {"value": "Kids &amp; Family", "label": "Kids & Family 儿童与家庭"},
                {"value": "Leisure", "label": "Leisure 休闲"},
                {"value": "Music", "label": "Music 音乐"},
                {"value": "News", "label": "News 新闻"},
                {
                    "value": "Religion &amp; Spirituality",
                    "label": "Religion & Spirituality 宗教与心灵",
                },
                {"value": "Science", "label": "Science 科学"},
                {
                    "value": "Society &amp; Culture",
                    "label": "Society & Culture 社会与文化",
                },
                {"value": "Sports", "label": "Sports 体育"},
                {"value": "Technology", "label": "Technology 科技"},
                {"value": "True Crime", "label": "True Crime 犯罪纪实"},
                {"value": "TV &amp; Film", "label": "TV & Film 电视与电影"},
            ],
        },
        "preparation_per_count": {
            "default": 100,
            "type": "int",
            "min": 1,
            "desc": "获取媒体信息每组数量",
        },
        "completion_count": {
            "default": 100,
            "type": "int",
            "min": 0,
            "desc": "媒体缺失时最大补全数量",
        },
        "retry_count": {
            "default": 2,
            "type": "int",
            "min": 1,
            "desc": "媒体下载重试次数",
        },
        "url": {
            "default": "http://127.0.0.1",
            "type": "url",
            "pattern": r"^(https?|ftp)://[^/\s:]+",
            "trim_to": "match",
            "msg": "需以 http://、https:// 或 ftp:// 开头",
            "desc": "HTTP共享地址",
        },
        "port": {
            "default": 80,
            "type": "int",
            "min": 0,
            "max": 65535,
            "desc": "HTTP共享端口",
        },
        "port_in_url": {
            "default": True,
            "type": "bool",
            "desc": "HTTP共享地址是否包含端口",
        },
        "httpfs": {"default": False, "type": "bool", "desc": "HTTP共享日志"},
        "token": {
            "default": "",
            "type": "str",
            "desc": "token认证, 如为null或空字符串将不启用token",
        },
        "delete_incompletement": {
            "default": True,
            "type": "bool",
            "desc": "是否删除下载中断媒体(下载前处理流程)",
        },
        "remove_media": {
            "default": True,
            "type": "bool",
            "desc": "是否删除无用的媒体文件",
        },
        "upload": {"default": False, "type": "bool", "desc": "是否将长期媒体进行上传"},
        "upload_ip": {
            "default": "",
            "type": "str",
            "when_show": {"key": "upload", "value": True},
            "desc": "长期媒体进行上传服务器地址(可不写, 会自动搜索, 无法搜索请填写)",
        },
        "youtube_download_span": {
            "default": 30,
            "type": "int",
            "min": 0,
            "desc": "YouTube下载间隔时间",
        },
    },
    "channel": {
        "youtube": {
            "title": {
                "default": "",
                "init": "YouTube",
                "type": "str",
                "sync_key": True,
                "desc": "频道名称(修改后同步为频道名 key; 与其它频道 key 重复时需手动修改 key)",
            },
            "id": {
                "default": "",
                "init": "UCBR8-60-B28hp2BmDPdntcQ",
                "type": "str",
                "required": True,
                "pattern": r"^UC.{22}",
                "min_length": 24,
                "trim_to": "match",
                "msg": "YouTube 频道 ID 需以 UC 开头且不少于 24 位",
                "desc": "频道ID",
            },
            "update_size": {
                "default": 15,
                "type": "int",
                "min": 1,
                "desc": "每次获取频道媒体数量",
            },
            "last_size": {
                "default": 50,
                "type": "int",
                "min": 1,
                "min_field": "update_size",
                "desc": "媒体保留数量",
            },
            "media": {
                "default": "m4a",
                "type": "select",
                "options": [
                    {"value": "m4a", "label": "m4a 音频"},
                    {"value": "mp4", "label": "mp4 视频"},
                ],
                "desc": "下载媒体类型",
            },
            "quality": {
                "default": "1080",
                "type": "select",
                "when": {"key": "media", "value": "mp4"},
                "when_show": {"key": "media", "value": "mp4"},
                "msg": "media 为 mp4 时分辨率需为可用选项",
                "options": [
                    {"value": "144", "label": "144p 极低画质(极省流量)"},
                    {"value": "180", "label": "180p 超低画质"},
                    {"value": "216", "label": "216p 极低分档"},
                    {"value": "240", "label": "240p 流畅画质"},
                    {"value": "360", "label": "360p 标清(SD)"},
                    {"value": "480", "label": "480p 清晰(标清)"},
                    {"value": "720", "label": "720p 高清(HD)"},
                    {"value": "1080", "label": "1080p 全高清(FHD)"},
                    {"value": "1440", "label": "1440p 超高清2K(QHD)"},
                    {"value": "2160", "label": "2160p 超高清4K(UHD)"},
                    {"value": "4320", "label": "4320p 极清8K(FUHD)"},
                ],
                "desc": "媒体分辨率(仅在media为视频时有效)",
            },
            "InmainRSS": {"default": True, "type": "bool", "desc": "是否在主播客中"},
            "DisplayRSSaddress": {
                "default": False,
                "type": "bool",
                "force": {"when_key": "InmainRSS", "when_value": False, "set": True},
                "when_show": {"key": "InmainRSS", "value": True},
                "desc": "是否在Print中显示子播客地址",
            },
            "QRcode": {
                "default": False,
                "type": "bool",
                "force": {
                    "when_key": "DisplayRSSaddress",
                    "when_value": False,
                    "set": False,
                },
                "when_show": {"key": "DisplayRSSaddress", "value": True},
                "desc": "是否显示子播客地址二维码(仅在DisplayRSSaddress为True时有效)",
            },
            "BackwardUpdate": {
                "default": False,
                "type": "bool",
                "desc": "是否向后更新",
            },
            "BackwardUpdate_size": {
                "default": 3,
                "type": "int",
                "min": 1,
                "when": {"key": "BackwardUpdate", "value": True},
                "when_show": {"key": "BackwardUpdate", "value": True},
                "msg": "向后更新时需为大于 0 的整数",
                "desc": "向后更新数量(仅在BackwardUpdate为True时有效)",
            },
            "want_retry_count": {
                "default": 25,
                "type": "int",
                "min": 1,
                "desc": "媒体获取失败后多少次后重试(小于等于该数量时将一直重试)",
            },
            "audio_track_language": {
                "default": "zh",
                "type": "select",
                "msg": "语言代码无效（需为两位语言代码，如 zh）",
                # label 为「语言代码 中文名」, 前端下拉里中文灰显（见 config.js 自定义双语下拉）;
                # 存入配置的仍是两位语言代码 value, 与 correct_channelid 的校验保持一致
                "options": [
                    {"value": "af", "label": "af 南非荷兰语"},
                    {"value": "ar", "label": "ar 阿拉伯语"},
                    {"value": "az", "label": "az 阿塞拜疆语"},
                    {"value": "be", "label": "be 白俄罗斯语"},
                    {"value": "bg", "label": "bg 保加利亚语"},
                    {"value": "bn", "label": "bn 孟加拉语"},
                    {"value": "bs", "label": "bs 波斯尼亚语"},
                    {"value": "ca", "label": "ca 加泰罗尼亚语"},
                    {"value": "cs", "label": "cs 捷克语"},
                    {"value": "cy", "label": "cy 威尔士语"},
                    {"value": "da", "label": "da 丹麦语"},
                    {"value": "de", "label": "de 德语"},
                    {"value": "el", "label": "el 希腊语"},
                    {"value": "en", "label": "en 英语"},
                    {"value": "eo", "label": "eo 世界语"},
                    {"value": "es", "label": "es 西班牙语"},
                    {"value": "et", "label": "et 爱沙尼亚语"},
                    {"value": "eu", "label": "eu 巴斯克语"},
                    {"value": "fa", "label": "fa 波斯语"},
                    {"value": "fi", "label": "fi 芬兰语"},
                    {"value": "fr", "label": "fr 法语"},
                    {"value": "ga", "label": "ga 爱尔兰语"},
                    {"value": "gl", "label": "gl 加利西亚语"},
                    {"value": "gu", "label": "gu 古吉拉特语"},
                    {"value": "he", "label": "he 希伯来语"},
                    {"value": "hi", "label": "hi 印地语"},
                    {"value": "hr", "label": "hr 克罗地亚语"},
                    {"value": "ht", "label": "ht 海地克里奥尔语"},
                    {"value": "hu", "label": "hu 匈牙利语"},
                    {"value": "hy", "label": "hy 亚美尼亚语"},
                    {"value": "id", "label": "id 印尼语"},
                    {"value": "is", "label": "is 冰岛语"},
                    {"value": "it", "label": "it 意大利语"},
                    {"value": "ja", "label": "ja 日语"},
                    {"value": "ka", "label": "ka 格鲁吉亚语"},
                    {"value": "kk", "label": "kk 哈萨克语"},
                    {"value": "km", "label": "km 高棉语"},
                    {"value": "kn", "label": "kn 卡纳达语"},
                    {"value": "ko", "label": "ko 韩语"},
                    {"value": "ku", "label": "ku 库尔德语"},
                    {"value": "ky", "label": "ky 吉尔吉斯语"},
                    {"value": "la", "label": "la 拉丁语"},
                    {"value": "lb", "label": "lb 卢森堡语"},
                    {"value": "lo", "label": "lo 老挝语"},
                    {"value": "lt", "label": "lt 立陶宛语"},
                    {"value": "lv", "label": "lv 拉脱维亚语"},
                    {"value": "mk", "label": "mk 马其顿语"},
                    {"value": "ml", "label": "ml 马拉雅拉姆语"},
                    {"value": "mn", "label": "mn 蒙古语"},
                    {"value": "mo", "label": "mo 摩尔多瓦语"},
                    {"value": "mr", "label": "mr 马拉地语"},
                    {"value": "ms", "label": "ms 马来语"},
                    {"value": "mt", "label": "mt 马耳他语"},
                    {"value": "nb", "label": "nb 书面挪威语"},
                    {"value": "ne", "label": "ne 尼泊尔语"},
                    {"value": "nl", "label": "nl 荷兰语"},
                    {"value": "nn", "label": "nn 新挪威语"},
                    {"value": "no", "label": "no 挪威语"},
                    {"value": "pa", "label": "pa 旁遮普语"},
                    {"value": "pl", "label": "pl 波兰语"},
                    {"value": "pt", "label": "pt 葡萄牙语"},
                    {"value": "ro", "label": "ro 罗马尼亚语"},
                    {"value": "ru", "label": "ru 俄语"},
                    {"value": "si", "label": "si 僧伽罗语"},
                    {"value": "sk", "label": "sk 斯洛伐克语"},
                    {"value": "sl", "label": "sl 斯洛文尼亚语"},
                    {"value": "sq", "label": "sq 阿尔巴尼亚语"},
                    {"value": "sr", "label": "sr 塞尔维亚语"},
                    {"value": "sv", "label": "sv 瑞典语"},
                    {"value": "sw", "label": "sw 斯瓦希里语"},
                    {"value": "ta", "label": "ta 泰米尔语"},
                    {"value": "te", "label": "te 泰卢固语"},
                    {"value": "th", "label": "th 泰语"},
                    {"value": "tl", "label": "tl 他加禄语"},
                    {"value": "tr", "label": "tr 土耳其语"},
                    {"value": "uk", "label": "uk 乌克兰语"},
                    {"value": "ur", "label": "ur 乌尔都语"},
                    {"value": "uz", "label": "uz 乌兹别克语"},
                    {"value": "vi", "label": "vi 越南语"},
                    {"value": "xh", "label": "xh 科萨语"},
                    {"value": "yi", "label": "yi 意第绪语"},
                    {"value": "zh", "label": "zh 中文"},
                    {"value": "zu", "label": "zu 祖鲁语"},
                ],
                "desc": "音频轨道语言(默认为中文)",
            },
            "title_change": {
                "default": [],
                "init": [
                    {
                        "mode": "add-left",
                        "match": "",
                        "url": "https://www.youtube.com/playlist?list=...",
                        "text": "",
                    },
                    {
                        "mode": "add-right",
                        "match": "",
                        "url": "",
                        "text": "",
                    },
                ],
                "type": "array",
                "rules": "title_change_rule",
                "label": "标题修改规则",
                "desc": "标题文本修改(默认为无, 可多个条件，以列表形式存在)",
            },
            "NoShorts": {
                "default": False,
                "type": "bool",
                "desc": "是否跳过Shorts短视频",
            },
            "Favorite": {
                "default": False,
                "type": "bool",
                "desc": "是否为特别关注(特别关注频道在有更新时不受延迟等待的影响, 会立即更新)",
            },
        },
        "bilibili": {
            "title": {
                "default": "",
                "init": "哔哩哔哩弹幕网",
                "type": "str",
                "sync_key": True,
                "desc": "频道名称(修改后同步为频道名 key; 与其它频道 key 重复时需手动修改 key)",
            },
            "id": {
                "default": "",
                "init": "8047632",
                "type": "str",
                "required": True,
                "pattern": r"^\d+$",
                "msg": "Bilibili 频道 ID 需为纯数字",
                "desc": "频道ID",
            },
            "update_size": {
                "default": 25,
                "type": "int",
                "min": 1,
                "desc": "每次获取频道媒体数量",
            },
            "last_size": {
                "default": 100,
                "type": "int",
                "min": 1,
                "min_field": "update_size",
                "desc": "媒体保留数量",
            },
            "media": {
                "default": "m4a",
                "type": "select",
                "options": [
                    {"value": "m4a", "label": "m4a 音频"},
                    {"value": "mp4", "label": "mp4 视频"},
                    ],
                "desc": "下载媒体类型",
            },
            "quality": {
                "default": "1080",
                "type": "select",
                "when": {"key": "media", "value": "mp4"},
                "when_show": {"key": "media", "value": "mp4"},
                "msg": "media 为 mp4 时分辨率需为可用选项",
                "options": [
                    {"value": "144", "label": "144p 极低画质(极省流量)"},
                    {"value": "180", "label": "180p 超低画质"},
                    {"value": "216", "label": "216p 极低分档"},
                    {"value": "240", "label": "240p 流畅画质"},
                    {"value": "360", "label": "360p 标清(SD)"},
                    {"value": "480", "label": "480p 清晰(标清)"},
                    {"value": "720", "label": "720p 高清(HD)"},
                    {"value": "1080", "label": "1080p 全高清(FHD)"},
                    {"value": "1440", "label": "1440p 超高清2K(QHD)"},
                    {"value": "2160", "label": "2160p 超高清4K(UHD)"},
                    {"value": "4320", "label": "4320p 极清8K(FUHD)"},
                ],
                "desc": "媒体分辨率(仅在media为视频时有效)",
            },
            "InmainRSS": {"default": True, "type": "bool", "desc": "是否在主播客中"},
            "DisplayRSSaddress": {
                "default": False,
                "type": "bool",
                "force": {"when_key": "InmainRSS", "when_value": False, "set": True},
                "when_show": {"key": "InmainRSS", "value": True},
                "desc": "是否在Print中显示子播客地址",
            },
            "QRcode": {
                "default": False,
                "type": "bool",
                "force": {
                    "when_key": "DisplayRSSaddress",
                    "when_value": False,
                    "set": False,
                },
                "when_show": {"key": "DisplayRSSaddress", "value": True},
                "desc": "是否显示子播客地址二维码(仅在DisplayRSSaddress为True时有效)",
            },
            "BackwardUpdate": {
                "default": False,
                "type": "bool",
                "desc": "是否向后更新",
            },
            "BackwardUpdate_size": {
                "default": 3,
                "type": "int",
                "min": 1,
                "when": {"key": "BackwardUpdate", "value": True},
                "when_show": {"key": "BackwardUpdate", "value": True},
                "msg": "向后更新时需为大于 0 的整数",
                "desc": "向后更新数量(仅在BackwardUpdate为True时有效)",
            },
            "want_retry_count": {
                "default": 8,
                "type": "int",
                "min": 1,
                "desc": "媒体获取失败后多少次后重试(小于等于该数量时将一直重试)",
            },
            "title_change": {
                "default": [],
                "init": {"mode": "replace", "match": "", "text": ""},
                "type": "array",
                "rules": "title_change_rule",
                "label": "标题修改规则",
                "desc": "标题文本修改(默认为无, 可多个条件，以列表或字典形式存在)",
            },
            "AllPartGet": {
                "default": False,
                "type": "bool",
                "desc": "是否提前获取分P或互动视频(建议update_size大于5时使用, 如果该变量不存在时, 默认update_size大于5时开启)",
            },
            "part_sequence": {
                "default": True,
                "type": "bool",
                "desc": "分P或互动视频是否按顺序显示",
            },
            "Favorite": {
                "default": False,
                "type": "bool",
                "desc": "是否为特别关注(特别关注频道在有更新时不受延迟等待的影响, 会立即更新)",
            },
        },
    },
    "title_change_rule": {
        "_meta": {
            "require": ["mode", "text"],
            "any_of": [["url", "match"]],
            "message": "需包含 mode、text 以及 match 或 url，否则可能被后台忽略",
        },
        "mode": {
            "default": "add-left",
            "type": "select",
            "warn": True,
            "options": [
                {"value": "add-left", "label": "add-left 开头添加"},
                {"value": "add-right", "label": "add-right 结尾添加"},
                {"value": "replace", "label": "replace 内容替换"},
            ],
            "desc": "修改模式(add-left: 开头添加, add-right: 结尾添加, replace: 内容替换)",
        },
        "match": {
            "default": "",
            "type": "regex",
            "desc": "需要匹配的规则(为正则表达式), 无效正则将被忽略",
        },
        "url": {
            "default": "",
            "type": "url",
            "warn": True,
            "allow_empty": True,
            "pattern": r"^https://www\.youtube\.com/playlist\?list=PL[0-9a-zA-Z_-]{32}",
            "mode_in": {
                "key": "mode",
                "values": ["add-left", "add-right"],
                "msg": "播放列表网址仅在 add-left / add-right 模式下有效",
            },
            "websites": ["youtube"],
            "msg": "需为 YouTube 播放列表网址（playlist?list=PL+32 位字符）",
            "desc": "播放列表网址(只适用于YouTube频道, 并且不适用replace模式, 选择后会失效)",
        },
        "text": {"default": "", "type": "str", "desc": "需要替换或添加的文本"},
    },
}


# default_config 由 config_desc 生成（唯一来源）:
#   字段值取 entry["init"]（出厂初值, 如频道 id/title/title_change），否则 entry["default"]；
#   两者都无则跳过该字段。
#   频道按 config_desc["_init_channels"] 声明的初始频道名生成, 值为该站点字段的 init/default。
def build_default_config(desc):
    config = {}
    for key, entry in desc["main"].items():
        if key.startswith("_"):
            continue
        if "init" in entry:
            config[key] = copy.deepcopy(entry["init"])
        elif "default" in entry:
            config[key] = copy.deepcopy(entry["default"])
    for site, site_desc in desc["channel"].items():
        if site.startswith("_"):
            continue
        for name in desc.get("_init_channels", {}).get(site, []):
            channel = {}
            for key, entry in site_desc.items():
                if key.startswith("_"):
                    continue
                if "init" in entry:
                    channel[key] = copy.deepcopy(entry["init"])
                elif "default" in entry:
                    channel[key] = copy.deepcopy(entry["default"])
            config.setdefault(f"channelid_{site}", {})[name] = channel
    return config


# 默认参数（由 config_desc 生成, 与 config_desc 保持单一来源）
default_config = build_default_config(config_desc)


# 全局变量
class Application_gVar:
    def __init__(self):
        self.config = {}  # 配置文件字典
        self.original_config = {}  # 原始配置文件字典
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
        self.bilibili_content_bvid_backward_update = (
            {}
        )  # 向后更新需下载哔哩哔哩视频字典
        self.video_id_failed = []  # YouTube&哔哩哔哩视频下载失败列表
        self.video_id_update_format = {}  # YouTube和哔哩哔哩视频下载的详细信息字典
        self.custom_media_busy = (
            False  # 后台是否正在处理自定义媒体(为True时网页禁用所有操作按钮)
        )
        self.custom_media_progress = (
            None  # 自定义媒体下载的进度开关及份额信息(为None时下载条不影响主进度条)
        )
        self.hash_rss_original = ""  # 原始rss哈希值文本
        self.xmls_original = {}  # 原始xml信息字典
        self.xmls_original_fail = []  # 未获取原始xml频道列表
        self.xmls_quantity = {}  # xml数量字典
        self.youtube_xml_get_tree = {}  # YouTube频道简介和图标字典
        self.all_youtube_content_ytid = {}  # 所有YouTube视频id字典
        self.all_bilibili_content_bvid = {}  # 所有哔哩哔哩视频id字典
        self.all_items = {}  # 更新后所有item明细字典
        self.overall_rss = ""  # 更新后的rss文本
        self.make_up_file_format = {}  # 补全缺失媒体字典
        self.make_up_file_format_fail = {}  # 补全缺失媒体失败字典

        self.upload_original = []  # 原始上传信息列表
        self.upload_data = {}  # 上传用户账号密码字典
        self.upload_json = {}  # 上传登陆账号密码字典
        self.upload_stop = False  # 上传停止布尔值
        self.upload_message = []  # 上传用户媒体信息列表
        self.youtube_cookie_switch = False  # 是否默认使用 YouTube cookie布尔值
        self.favorite_update_skip_wait = threading.Event()  # 跳过特别关注等待并立即更新
        self.favorite_update_active = False  # 特别关注等待是否正在运行
        self.favorite_update_next_run = None  # 下次常规更新的 Unix 时间戳

        self.shortcuts_url = {}  # 输出至shortcut的url字典

        self.index_message = {  # 图形界面显示信息字典
            "podflow": [],  # 主窗口信息列表
            "http": [],  # httpfs窗口信息列表
            "enter": True,  # 是否换行
            "schedule": [0, "准备中"],  # 进度条信息列表
            "download": [],  # 下载信息列表
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
        self.save = []
        self.skip_update = False
        self.debug_variable = (
            False  # 是否启用隐藏的变量查询测试页(连续点击三次 version-info 打开)
        )


# 创建 Application 类的实例
gVar = Application_gVar()
parse = Application_parse()
