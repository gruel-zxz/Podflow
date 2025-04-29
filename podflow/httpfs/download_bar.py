# podflow/httpfs/download_bar.py
# coding: utf-8

from podflow import gVar


def download_bar(
    mod=0,
    per=0,
    retime="00:00",
    speed="   0.00 B",
    part="",
    status="准备中",
    idname="",
    nametext="",
    file="",
):
    if mod == 0:
        gVar.index_message["download"].append(
            [
                per,
                retime,
                speed,
                part,
                status,
                idname,
                nametext,
                file,
            ]
        )
    elif mod == 1 and gVar.index_message["download"]:
        gVar.index_message["download"][-1][0] = per
        gVar.index_message["download"][-1][1] = retime
        gVar.index_message["download"][-1][2] = speed
        gVar.index_message["download"][-1][3] = part
        gVar.index_message["download"][-1][4] = status
    elif mod == 2 and gVar.index_message["download"]:
        gVar.index_message["download"][-1][4] = status
