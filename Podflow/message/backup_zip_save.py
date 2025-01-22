# Podflow/message/backup_zip_save.py
# coding: utf-8

import zipfile
from datetime import datetime
from Podflow import gVar
from Podflow.basic.write_log import write_log
from Podflow.message.rss_create_hash import rss_create_hash


# xml备份保存模块
def backup_zip_save(file_content):
    def get_file_name():
        # 获取当前的具体时间
        current_time = datetime.now()
        # 格式化输出, 只保留年月日时分秒
        formatted_time = current_time.strftime("%Y%m%d%H%M%S")
        return f"{formatted_time}.xml"

    # 定义要添加到压缩包中的文件名和内容
    compress_file_name = "Podflow_backup.zip"
    # 生成新rss的哈希值
    hash_overall_rss = rss_create_hash(gVar.overall_rss)
    # 使用哈希值判断新老rss是否一致
    if hash_overall_rss == gVar.hash_rss_original:
        judging_save = True
        write_log("频道无更新内容将不进行备份")
    else:
        judging_save = False
    while not judging_save:
        # 获取要写入压缩包的文件名
        file_name_str = get_file_name()
        # 打开压缩文件, 如果不存在则创建
        with zipfile.ZipFile(compress_file_name, "a") as zipf:
            # 设置压缩级别为最大
            zipf.compression = zipfile.ZIP_LZMA
            zipf.compresslevel = 9
            # 检查文件是否已存在于压缩包中
            if file_name_str not in zipf.namelist():
                # 将文件内容写入压缩包
                zipf.writestr(file_name_str, file_content)
                judging_save = True
            else:
                # 如果文件已存在, 输出提示信息
                print(f"{file_name_str}已存在于压缩包中, 重试中...")
