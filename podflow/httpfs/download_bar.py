# podflow/httpfs/download_bar.py

from podflow import gVar
from podflow.httpfs.progress_bar import progress_update


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
    # 自定义媒体下载时开关开启, 按下载进度同步推进主进度条(常规下载时为None, 行为不变)
    progress = gVar.custom_media_progress
    if progress is not None:
        if mod == 0:  # 新的下载单元开始, 视频单元分视频流与音频流两次下载, 音频单元仅一次
            progress["subs_total"] = 2 if file.endswith(".mp4") else 1
            progress["subs_done"] = 0
            progress["last_per"] = 0.0
            progress["unit_credited"] = 0.0
        elif mod == 1 and gVar.index_message["download"]:
            if per < progress["last_per"]:  # 分流切换(视频流→音频流)
                progress["subs_done"] += 1
            progress["last_per"] = per
            # 当前单元进度 = (已完成分流数 + 当前分流百分比) / 分流总数
            unit_progress = min(
                (progress["subs_done"] + per) / progress["subs_total"], 1.0
            )
            if unit_progress > progress["unit_credited"]:
                # 按单元份额增加主进度条, 且不超过100%
                remaining = 1.0 - gVar.index_message["schedule"][1]
                progress_update(
                    min(
                        (unit_progress - progress["unit_credited"])
                        * progress["share"],
                        remaining,
                    ),
                    added=True,
                )
                progress["unit_credited"] = unit_progress
        elif mod == 2 and gVar.index_message["download"]:
            # 下载结束(成功/失败)时计满当前单元剩余份额, 保证主进度条最终到达100%
            if progress["unit_credited"] < 1.0:
                progress_update(
                    (1 - progress["unit_credited"]) * progress["share"], added=True
                )
                progress["unit_credited"] = 1.0
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
