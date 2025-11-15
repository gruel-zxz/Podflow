# podflow/basic/get_version_num.py
# coding: utf-8

from datetime import datetime
from podflow.basic.http_client import http_client


# 获取三方库版本号模块
def get_version_num(library, version_type):
    version_json = http_client(
        f"https://pypi.org/pypi/{library}/json", f"{library}", 2, 2
    )
    if version_json:
        version_json = version_json.json()
        version_update = version_json["info"]["version"]
        if version_type == "stable":
            return version_update
        elif version_type == "latest":
            version_releases = version_json["releases"]
            max_timestamp = 0.0
            version_release = version_update
            for releases_key, releases_value in version_releases.items():
                upload_time = releases_value[0]["upload_time"]
                # 转换为 datetime 对象
                dt = datetime.fromisoformat(upload_time)
                # 转换为 Unix 时间戳
                timestamp = dt.timestamp()
                if max_timestamp <= timestamp:
                    version_release = releases_key
                    max_timestamp = timestamp
            return version_release
        else:
            return None
    else:
        return None
