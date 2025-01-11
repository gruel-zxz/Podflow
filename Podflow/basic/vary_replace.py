# Podflow/basic/vary_replace.py
# coding: utf-8

import re


# 批量正则表达式替换删除模块
def vary_replace(varys, text):
    for vary in varys:
        text = re.sub(vary, "", text)
    return text
