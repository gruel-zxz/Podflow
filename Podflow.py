# %%
import os
import json

default_config = {"channelid": {"YouTube": {"update_size": 1, "id": "UCBR8-60-B28hp2BmDPdntcQ", "title": "YouTube", "quality": "720", "last_size": 1, "media": "m4a"}}}

# 检查当前文件夹中是否存在config.json文件
if not os.path.exists('config.json'):
    # 如果文件不存在，创建并写入默认字典
    with open('config.json', 'w') as file:
        json.dump(default_config, file)
    print("不存在配置文件，已新建，添加频道")
else:
    # 如果文件存在，读取字典并保存到config变量中
    with open('config.json', 'r') as file:
        config = json.load(file)
    print(config)

# %%
channelid = config['channelid']
print(channelid)


