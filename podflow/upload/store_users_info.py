# podflow/upload/store_users_info.py
# coding: utf-8

from podflow import gVar
from podflow.basic.file_save import file_save
from podflow.upload.find_media_index import find_media_index


def store_users_info(username,filename):
    index = find_media_index(gVar.upload_message, filename)
    if index == -1:
        gVar.upload_message.append(
            {
                "media_id": filename,
                "users": [username]
            }
        )
    elif username not in gVar.upload_message[index]["users"]:
        gVar.upload_message[index]["users"].append(username)
    else:
        return
    file_save(gVar.upload_message, "upload_message.json", "channel_data")
