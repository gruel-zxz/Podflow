# podflow/basic/list_merge_tidy.py
# coding: utf-8


# 合并整形列表模块
def list_merge_tidy(list1, list2=None, length=None):
    if list2 is None:
        list2 = []
    final_list = []
    for item in list1 + list2:
        if item:
            item = item[:length]
        if item not in final_list:
            final_list.append(item)
    return final_list
