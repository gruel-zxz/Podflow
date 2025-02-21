# Podflow/message/save_rss.py
# coding: utf-8

from Podflow import gVar
from Podflow.basic.qr_code import qr_code
from Podflow.message.xml_rss import xml_rss
from Podflow.basic.file_save import file_save
from Podflow.basic.write_log import write_log
from Podflow.message.backup_zip_save import backup_zip_save
from Podflow.message.display_qrcode_and_url import display_qrcode_and_url


# 保存rss文件模块
def save_rss():
    # 定义一个空列表，用于存储所有rss的items
    main_items = []
    # 遍历gVar.all_items字典，获取每个rss的输出目录和items_dict
    for output_dir, items_dict in gVar.all_items.items():
        # 获取items_dict中的各个字段
        title = items_dict["title"]
        link = items_dict["link"]
        description = items_dict["description"]
        category = items_dict["category"]
        icon = items_dict["icon"]
        items = items_dict["items"]
        # 调用file_save函数，将rss保存到指定目录
        file_save(
            xml_rss(title, link, description, category, icon, items),
            f"{output_dir}.xml",
            "channel_rss",
        )
        # 获取items_dict中的其他字段
        display_rss_address = items_dict["DisplayRSSaddress"]
        qrcode = items_dict["QRcode"]
        id_name = items_dict["ID_Name"]
        id_type = items_dict["type"]
        # 根据id_type获取对应的ids_update
        if id_type == "youtube":
            ids_update = gVar.channelid_youtube_ids_update
        elif id_type == "bilibili":
            ids_update = gVar.channelid_bilibili_ids_update
        else:
            ids_update = {}
        # 调用display_qrcode_and_url函数，显示rss地址和二维码
        display_qrcode_and_url(
            output_dir,
            display_rss_address,
            qrcode,
            id_name,
            ids_update,
        )
        # 如果items_dict中的InmainRSS字段为True，则将items添加到main_items列表中
        if items_dict["InmainRSS"]:
            main_items.append(items)

    # 生成主rss
    overall_rss = xml_rss(
        gVar.config["title"],
        gVar.config["link"],
        gVar.config["description"],
        gVar.config["category"],
        gVar.config["icon"],
        "\n".join(main_items),
    )

    # 保存主rss
    file_save(overall_rss, f"{gVar.config['filename']}.xml")

    # 获取gVar.config中的地址和文件名
    address = gVar.config["address"]
    filename = gVar.config["filename"]
    # 如果gVar.config中的token字段存在，则将token添加到overall_url中
    if token := gVar.config["token"]:
        overall_url = f"{address}/{filename}.xml?token={token}"
    else:
        overall_url = f"{address}/{filename}.xml"
    # 调用write_log函数，记录总播客已更新
    write_log("总播客已更新", f"地址:\n\033[34m{overall_url}\033[0m")
    # 如果gVar.displayed_QRcode中不包含"main"，则调用qr_code函数，显示总播客的二维码，并将"main"添加到gVar.displayed_QRcode中
    if "main" not in gVar.displayed_QRcode:
        qr_code(overall_url)
        gVar.displayed_QRcode.append("main")

    # 备份主rss
    backup_zip_save(overall_rss)
