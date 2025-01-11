# Podflow/basic/split_dict.py
# coding: utf-8


# 字典拆分模块
def split_dict(data, chunk_size=100, firse_item_only=False):
    if chunk_size == 0:
        return [{}]
    end_value = chunk_size if firse_item_only else len(data)
    chunks = []
    for i in range(0, end_value, chunk_size):
        chunk = dict(list(data.items())[i:i+chunk_size])
        chunks.append(chunk)
    return chunks
