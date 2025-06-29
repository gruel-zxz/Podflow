# podflow/basic/random_sequence.py
# coding: utf-8

import random


def random_sequence(n):
    arr = list(range(n))  # 生成0到n-1的列表
    random.shuffle(arr)   # 原地随机打乱列表顺序
    return arr            # 返回打乱后的列表
