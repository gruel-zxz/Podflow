# Podflow/upload/login.py
# coding: utf-8

import os
import json
import uuid
import hashlib
from Podflow import gVar
from Podflow.basic.file_save import file_save


def get_login():
    try:
        with open("channel_data/upload_login.json", "r") as file:
            upload_data = file.read()
        gVar.upload_data = json.loads(upload_data)
    except Exception:
        file_save(gVar.upload_data, "upload_login.json", "channel_data")


def create():
    new_username = str(uuid.uuid4())
    while new_username in gVar.upload_data:
        new_username = str(uuid.uuid4())
    new_password = hashlib.sha256(os.urandom(64)).hexdigest()
    gVar.upload_data[new_username] = new_password
    file_save(gVar.upload_data, "upload_login.json", "channel_data")
    return new_username, new_password
