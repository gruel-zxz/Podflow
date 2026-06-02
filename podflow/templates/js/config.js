// /templates/js/config.js

document.addEventListener('DOMContentLoaded', () => {
    const configContainer = document.getElementById('configContainer');
    const refreshConfigBtn = document.getElementById('refreshConfigBtn');
    const saveConfigBtn = document.getElementById('saveConfigBtn');
    const configStatus = document.getElementById('configStatus');
    const configPage = document.getElementById('pageConfig');

    let currentConfig = null; // 用于存储当前加载的配置

    // --- Helper Function: 创建表单元素 ---
    function createInputElement(key, value, path) {
        const itemDiv = document.createElement('div');
        itemDiv.classList.add('config-item');

        const label = document.createElement('label');
        label.htmlFor = `config-${path}`;
        label.textContent = `${key}:`;
        itemDiv.appendChild(label);

        let input;
        const inputId = `config-${path}`;

        if (typeof value === 'boolean') {
            input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = value;
            input.id = inputId;
            input.dataset.path = path; // 存储路径用于保存
            input.dataset.type = 'boolean';
            // Checkbox 需要特殊布局，将其放在label后面
            label.style.display = 'inline-block'; // 让label和checkbox在同一行
            input.style.marginLeft = '10px';
            itemDiv.appendChild(input);
        } else if (typeof value === 'number') {
            input = document.createElement('input');
            input.type = 'number';
            input.value = value;
            input.id = inputId;
            input.dataset.path = path;
            input.dataset.type = 'number';
             // 对于整数，设置 step="1"
            if (Number.isInteger(value)) {
                input.step = "1";
            } else {
                 input.step = "any"; // 允许小数
            }
            itemDiv.appendChild(document.createElement('br')); // 换行
            itemDiv.appendChild(input);
        } else if (key === 'media' && path.includes('channelid_')) { // media 类型特殊处理为下拉框
            input = document.createElement('select');
            input.id = inputId;
            input.dataset.path = path;
             input.dataset.type = 'string'; // 本质是字符串
             const options = ['m4a', 'mp4', 'webm']; // 可能的媒体类型
            options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt;
                option.textContent = opt;
                if (opt === value) {
                    option.selected = true;
                }
                input.appendChild(option);
            });
            itemDiv.appendChild(document.createElement('br'));
            itemDiv.appendChild(input);
        }
        // mode 字段现在可能出现在嵌套的 title_change 中，路径会包含 title_change
        else if (key === 'mode' && path.includes('.title_change[')) { // title_change 数组项内部的 mode 特殊处理为下拉框
            input = document.createElement('select');
            input.id = inputId;
            input.dataset.path = path;
            input.dataset.type = 'string';
            const options = ['add-left', 'add-right', 'replace'];
            options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt;
                option.textContent = opt;
                if (opt === value) {
                    option.selected = true;
                }
                input.appendChild(option);
            });
            itemDiv.appendChild(document.createElement('br'));
            itemDiv.appendChild(input);
        }
        else { // 默认为文本输入
            input = document.createElement('input');
            input.type = 'text'; // 或 'url' 如果需要验证
            if (key === 'link' || key === 'icon' || (key === 'url' && !path.includes('.title_change['))) {
                 input.type = 'url';
            }
            input.value = value;
            input.id = inputId;
            input.dataset.path = path;
            input.dataset.type = 'string';
            itemDiv.appendChild(document.createElement('br'));
            itemDiv.appendChild(input);
        }

        // 为基本的文本/数字/URL输入添加类方便样式控制
        if (input.tagName === 'INPUT' && (input.type === 'text' || input.type === 'number' || input.type === 'url')) {
             input.classList.add('config-input-text');
        } else if (input.tagName === 'SELECT') {
             input.classList.add('config-input-select');
        }


        return itemDiv;
    }

    // --- Helper Function: 创建按钮 ---
    function createButton(text, className, onClick) {
        const button = document.createElement('button');
        button.textContent = text;
        button.classList.add('config-button', className);
        button.type = 'button'; // 防止触发表单提交
        button.addEventListener('click', onClick);
        return button;
    }

     // --- Helper Function: 生成唯一临时 key ---
    function generateTempKey(prefix = 'temp_') {
        // 使用当前时间戳和随机字符串生成一个足够唯一的临时 key
        return `${prefix}${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
    }


    // --- Helper Function: 递归渲染配置 ---
    function renderConfig(data, parentElement, currentPath = '') {
        // 清空当前容器，准备重新渲染
        parentElement.innerHTML = '';

        Object.entries(data).forEach(([key, value]) => {
            const path = currentPath ? `${currentPath}.${key}` : key;

            if (key === 'channelid_youtube' || key === 'channelid_bilibili') {
                const sectionDiv = document.createElement('div');
                sectionDiv.classList.add('collapsible-section');
                sectionDiv.dataset.path = path;
                sectionDiv.dataset.type = 'object';

                const header = document.createElement('div');
                header.classList.add('collapsible-header');
                header.innerHTML = `<span class="section-title">${key}:</span> <span class="toggle-icon">▶️</span>`; // 初始图标

                // ** 添加“添加频道”按钮 **
                const addChannelBtn = createButton('添加', 'add-button', (e) => {
                    e.stopPropagation(); // 阻止点击按钮时触发折叠/展开
                    addChannel(path);
                });
                header.appendChild(addChannelBtn);


                header.addEventListener('click', () => {
                    const content = sectionDiv.querySelector('.collapsible-content');
                    const icon = header.querySelector('.toggle-icon');
                    const isHidden = content.classList.toggle('hidden');
                    header.classList.toggle('expanded', !isHidden); // 添加/删除 expanded 类
                    icon.textContent = isHidden ? '▶️' : '🔽'; // 切换图标
                });
                sectionDiv.appendChild(header);

                const contentDiv = document.createElement('div');
                contentDiv.classList.add('collapsible-content', 'hidden'); // 默认隐藏

                // 确保 value 是一个对象，即使为空也要显示添加按钮
                if (value && typeof value === 'object') {
                    const channelKeys = Object.keys(value);
                    if (channelKeys.length > 0) {
                        channelKeys.forEach((channelKey) => {
                            const channelConfig = value[channelKey];
                            // 使用一个稳定的 key 用于 DOM 元素的 data-path。
                            // 当从后端加载时，使用真实的 channelKey；
                            // 当添加新频道时，使用临时 key。
                            // 在 collectConfigData 时再根据 input[name="id"] 的 value 来构建最终 JSON。
                            const domKey = channelConfig._tempKey || channelKey; // 优先使用临时 key 如果存在
                            const channelPath = `${path}.${domKey}`;


                            const channelSectionDiv = document.createElement('div');
                            channelSectionDiv.classList.add('collapsible-section', 'channel-item'); // 添加 channel-item 类方便识别
                            channelSectionDiv.dataset.path = channelPath; // 使用 DOM key 作为 data-path
                            channelSectionDiv.dataset.type = 'object';


                            const channelHeader = document.createElement('div');
                            channelHeader.classList.add('collapsible-header');

                            // 获取用户输入的 ID 值，如果存在，用于显示
                            const currentIdValue = channelConfig?.id ?? domKey; // 优先显示 id 值，否则显示 domKey

                            channelHeader.innerHTML = `
                                <span>
                                    <span class="channel-display-key">${currentIdValue}</span>
                                </span>
                                <span class="toggle-icon">▶️</span>`;

                            // ** 添加“删除频道”按钮 **
                            const deleteChannelBtn = createButton('删除', 'delete-button', (e) => {
                                e.stopPropagation(); // 阻止点击按钮时触发折叠/展开
                                deleteChannel(path, channelKey); // 删除时使用真实的 channelKey
                            });
                            channelHeader.appendChild(deleteChannelBtn);


                            channelHeader.addEventListener('click', (e) => {
                                e.stopPropagation(); // 防止点击内部 Header 时触发外部 Header 的事件
                                const channelContent = channelSectionDiv.querySelector('.collapsible-content');
                                const icon = channelHeader.querySelector('.toggle-icon');
                                const isHidden = channelContent.classList.toggle('hidden');
                                header.classList.toggle('expanded', !isHidden); // 切换外部 header 的 expanded 状态
                                channelHeader.classList.toggle('expanded', !isHidden); // 切换内部 header 的 expanded 状态
                                icon.textContent = isHidden ? '▶️' : '🔽';
                            });
                            channelSectionDiv.appendChild(channelHeader);

                            const channelContentDiv = document.createElement('div');
                            channelContentDiv.classList.add('collapsible-content', 'hidden'); // 默认隐藏详细配置

                            // 递归渲染频道内部配置
                            // 创建一个临时对象用于渲染，不包含 _tempKey
                            const channelConfigForRender = { ...channelConfig };
                            delete channelConfigForRender._tempKey;
                            renderConfig(channelConfigForRender, channelContentDiv, channelPath);

                            // ** 在频道内部添加 title_change 渲染逻辑 **
                            const titleChangeArray = channelConfigForRender.title_change;
                             if (Array.isArray(titleChangeArray)) {
                                const titleChangePath = `${channelPath}.title_change`; // 新的 title_change 路径
                                const titleChangeListDiv = document.createElement('div');
                                titleChangeListDiv.classList.add('title-change-list');
                                titleChangeListDiv.dataset.path = titleChangePath;
                                titleChangeListDiv.dataset.type = 'array';

                                const titleChangeLabel = document.createElement('label');
                                titleChangeLabel.textContent = `标题修改规则:`;
                                titleChangeListDiv.appendChild(titleChangeLabel);

                                // ** 添加频道内部的“添加规则”按钮 **
                                const addRuleBtn = createButton('添加规则', 'add-button', (e) => {
                                     e.stopPropagation();
                                     addTitleChangeRule(titleChangePath); // 传递频道内部的 title_change 路径
                                });
                                titleChangeListDiv.appendChild(addRuleBtn);


                                if (titleChangeArray.length > 0) {
                                    titleChangeArray.forEach((item, index) => {
                                        const itemPath = `${titleChangePath}[${index}]`; // 数组项的路径
                                        const itemDiv = document.createElement('div');
                                        itemDiv.classList.add('title-change-item');
                                        itemDiv.dataset.path = itemPath; // 存储数组项的路径
                                        itemDiv.dataset.type = 'object';
                                        itemDiv.innerHTML = `<strong>规则 ${index + 1}:</strong>`; // 标示第几个规则

                                        // ** 添加频道内部的“删除规则”按钮 **
                                        const deleteRuleBtn = createButton('删除', 'delete-button', (e) => {
                                             e.stopPropagation();
                                             deleteTitleChangeRule(titleChangePath, index); // 传递频道内部的 title_change 路径和索引
                                        });
                                        itemDiv.appendChild(deleteRuleBtn);

                                        // 渲染数组中每个对象的属性
                                        renderConfig(item, itemDiv, itemPath);
                                        titleChangeListDiv.appendChild(itemDiv);
                                    });
                                } else {
                                     if (titleChangeListDiv.childElementCount <= 2) { // label 和 add button
                                        titleChangeListDiv.innerHTML += '<p style="font-style: italic; color: #777; margin-left: 10px;">无标题修改规则。点击上方“添加规则”按钮。</p>';
                                    }
                                }
                                 channelContentDiv.appendChild(titleChangeListDiv); // 将 title_change 列表添加到频道内容中
                             }


                            channelSectionDiv.appendChild(channelContentDiv);

                            contentDiv.appendChild(channelSectionDiv);
                        });
                    } else {
                         contentDiv.innerHTML = '<p style="font-style: italic; color: #777; margin-left: 10px;">无配置或配置为空。请点击“添加”按钮。</p>';
                    }
                } else {
                    contentDiv.innerHTML = '<p style="font-style: italic; color: #777; margin-left: 10px;">数据格式错误或无配置。请点击“添加”按钮。</p>';
                }


                sectionDiv.appendChild(contentDiv);
                parentElement.appendChild(sectionDiv);

            }
            // ** 移除全局 title_change 的处理 **
            // else if (key === 'title_change' && Array.isArray(value)) { ... }
            // 此部分已被移动到频道内部处理

            else if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
                // 处理其他嵌套对象 (如果需要)
                const subSectionDiv = document.createElement('div');
                subSectionDiv.classList.add('config-subsection'); // 可以添加特定样式
                subSectionDiv.style.marginLeft = '15px'; // 缩进
                subSectionDiv.style.borderLeft = '2px solid #eee';
                subSectionDiv.style.paddingLeft = '10px';
                subSectionDiv.dataset.path = path;
                subSectionDiv.dataset.type = 'object';

                const label = document.createElement('label');
                label.textContent = `${key}:`;
                subSectionDiv.appendChild(label);
                renderConfig(value, subSectionDiv, path); // 递归渲染
                parentElement.appendChild(subSectionDiv);

            } else {
                // 基本类型 (string, number, boolean, null)
                const inputElement = createInputElement(key, value, path);
                parentElement.appendChild(inputElement);
            }
        });
    }

    // --- Function: 添加频道 ---
    function addChannel(sectionPath) { // e.g., 'media.channelid_youtube'
        if (!currentConfig) return;

        const pathParts = sectionPath.split('.');
        let target = currentConfig;
        for (const part of pathParts) {
            if (!target[part]) {
                 target[part] = {}; // 如果路径不存在，创建对象
            }
            target = target[part];
        }

        const tempKey = generateTempKey('new_channel_'); // 使用临时 key 作为内部标识
        // 添加一个默认的频道配置对象，包含临时 key 和空的 title_change 数组
        target[tempKey] = {
            _tempKey: tempKey, // 存储临时 key 用于 DOM 渲染和查找
            id: '', // 用户需要填写的 ID
            name: '',
            media: 'm4a',
            link: '',
            icon: '',
            description: '',
            title_change: [] // 添加空的 title_change 数组
        };

        // 重新渲染配置表单
        renderConfig(currentConfig, configContainer);
         // 展开新添加的频道部分 (可选)
         const newChannelElement = configContainer.querySelector(`.channel-item[data-path="${sectionPath}.${tempKey}"]`);
        if(newChannelElement) {
            const header = newChannelElement.querySelector('.collapsible-header');
            if (header) header.click(); // 模拟点击展开
             // 滚动到新添加的元素位置 (可选)
            newChannelElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // --- Function: 删除频道 ---
    function deleteChannel(sectionPath, channelKey) { // e.g., 'media.channelid_youtube', 'channel_abc' or 'new_channel_123...'
         if (!currentConfig) return;

         const pathParts = sectionPath.split('.');
         let target = currentConfig;
         for (const part of pathParts) {
            if (!target[part]) {
                 console.error("删除频道失败: 路径不存在", sectionPath);
                 return;
            }
            target = target[part];
         }

         if (target[channelKey]) {
             // 如果是临时 key，并且用户未输入 ID，直接删除无需确认
             const isTempKey = channelKey.startsWith('new_channel_');
             const confirmMsg = isTempKey ? `确定要删除新的频道条目吗?` : `确定要删除频道 "${target[channelKey].id || channelKey}" 吗?`;

             if (isTempKey || confirm(confirmMsg)) {
                delete target[channelKey];
                 // 重新渲染配置表单
                renderConfig(currentConfig, configContainer);
             }
         } else {
             console.error("删除频道失败: 频道 key 不存在", channelKey);
         }
    }


    // --- Function: 添加标题修改规则 ---
    // 此函数现在需要知道是哪个频道下的 title_change
    function addTitleChangeRule(titleChangePath) { // e.g., 'media.channelid_youtube.some_channel_key.title_change'
        if (!currentConfig) return;

        const pathParts = titleChangePath.split('.');
         let target = currentConfig;
         for (let i = 0; i < pathParts.length; i++) {
             const part = pathParts[i];
              // 处理数组索引 [index]
             const match = part.match(/^([^\[]+)\[(\d+)\]$/);
             if (match) {
                 const arrayKey = match[1];
                 const index = parseInt(match[2]);
                 if (!target[arrayKey] || !Array.isArray(target[arrayKey]) || index >= target[arrayKey].length) {
                      console.error("添加规则失败: 路径中的数组或索引无效", titleChangePath);
                      return;
                 }
                 target = target[arrayKey][index];
             } else {
                 if (!target[part]) {
                      // 如果路径不存在，并且是 title_change 本身，创建数组
                      if (i === pathParts.length - 1 && part === 'title_change') {
                          target[part] = [];
                      } else {
                           console.error("添加规则失败: 路径不存在", titleChangePath);
                           return;
                      }
                 } else if (i === pathParts.length - 1 && part === 'title_change' && !Array.isArray(target[part])) {
                     console.error("添加规则失败: 目标路径不是数组", titleChangePath);
                     return;
                 }
                  target = target[part];
             }
         }


        // 目标 target 现在是 title_change 数组
        // 添加一个默认的规则对象
        target.push({
            pattern: '',
            mode: 'replace', // 默认模式
            value: ''
        });

        // 重新渲染配置表单
        renderConfig(currentConfig, configContainer);
         // 滚动到新添加的规则位置 (可选)
        // 需要找到对应的频道 item，然后找到 title_change list，再找到最后一个 rule item
        const channelItemElement = configContainer.querySelector(`.channel-item[data-path="${titleChangePath.substring(0, titleChangePath.lastIndexOf('.'))}"]`);
        if(channelItemElement) {
             const ruleItems = channelItemElement.querySelectorAll('.title-change-item');
            if (ruleItems.length > 0) {
                 ruleItems[ruleItems.length - 1].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }

    // --- Function: 删除标题修改规则 ---
    // 此函数现在需要知道是哪个频道下的 title_change 数组以及要删除的索引
    function deleteTitleChangeRule(titleChangePath, index) { // e.g., 'media.channelid_youtube.some_channel_key.title_change', 0
        if (!currentConfig) return;

        const pathParts = titleChangePath.split('.');
         let target = currentConfig;
          for (let i = 0; i < pathParts.length; i++) {
             const part = pathParts[i];
              // 处理数组索引 [index]
             const match = part.match(/^([^\[]+)\[(\d+)\]$/);
             if (match) {
                 const arrayKey = match[1];
                 const arrIndex = parseInt(match[2]);
                  if (!target[arrayKey] || !Array.isArray(target[arrayKey]) || arrIndex >= target[arrayKey].length) {
                       console.error("删除规则失败: 路径中的数组或索引无效", titleChangePath);
                       return;
                  }
                  target = target[arrayKey][arrIndex];
             } else {
                if (!target[part] || !Array.isArray(target[part])) {
                     console.error("删除规则失败: 路径不是数组或不存在", titleChangePath);
                     return;
                 }
                 target = target[part];
             }
         }
        // 目标 target 现在是 title_change 数组

        if (index >= 0 && index < target.length) {
             if (confirm(`确定要删除规则 ${index + 1} 吗?`)) {
                target.splice(index, 1);
                 // 重新渲染配置表单
                renderConfig(currentConfig, configContainer);
             }
        } else {
             console.error("删除规则失败: 无效索引", index);
        }
    }


    // --- Helper Function: 从表单收集数据并重建 JSON ---
    function collectConfigData() {
        const newConfig = {};
        // 从顶层开始构建，找到主要的 section（如 media）
         configContainer.querySelectorAll(':scope > .collapsible-section, :scope > .config-subsection').forEach(sectionElement => {
            const path = sectionElement.dataset.path; // e.g., 'media'
            const key = path.split('.')[0]; // Get the top-level key

             if (sectionElement.classList.contains('collapsible-section') && (key === 'media')) {
                 // Handle the media section specifically to traverse into channelid_
                 const mediaObj = {};
                 newConfig[key] = mediaObj;
                 sectionElement.querySelectorAll(':scope > .collapsible-content > .collapsible-section').forEach(channelSection => {
                     const channelSectionPath = channelSection.dataset.path; // e.g., 'media.channelid_youtube' or 'media.channelid_bilibili'
                     const channelListKey = channelSectionPath.split('.').pop(); // e.g., 'channelid_youtube'
                      if (!mediaObj[channelListKey]) {
                          mediaObj[channelListKey] = {};
                      }

                     channelSection.querySelectorAll(':scope > .collapsible-content > .collapsible-section.channel-item').forEach(channelItemElement => {
                          // ** 特殊处理频道项 **
                          // 找到内部的 'id' 输入框，用其值作为 key
                         const idInput = channelItemElement.querySelector('[data-path$=".id"]'); // 查找路径以 ".id" 结尾的输入框
                         const channelId = idInput ? idInput.value.trim() : null; // 获取用户输入的 ID

                         if (channelId) {
                             const channelObj = {};
                              // 递归收集频道内部的配置
                              const channelContentDiv = channelItemElement.querySelector('.collapsible-content');
                              if (channelContentDiv) {
                                  // Collect data recursively from within the channel content
                                  // Pass the full path including the temporary key for nested items' data-path lookups
                                  reconstructObject(channelContentDiv, channelObj, channelItemElement.dataset.path);

                                   // Avoid adding _tempKey to the final output
                                   delete channelObj._tempKey;
                                  mediaObj[channelListKey][channelId] = channelObj;
                              } else {
                                 console.warn(`Channel item content not found for path: ${channelItemElement.dataset.path}`);
                              }

                         } else {
                             console.warn(`Skipping channel with empty ID in path: ${channelItemElement.dataset.path}`);
                         }
                     });
                 });


             } else if (sectionElement.dataset.type === 'object') {
                 // Handle other top-level objects
                 const subObj = {};
                 newConfig[key] = subObj;
                  // Recursively collect data from within this subsection
                 reconstructObject(sectionElement, subObj, path);
             }
              // Note: Top-level non-object/array items are collected by reconstructObject called from here
         });


         // Recursive helper to collect data from a given parent element starting at a path
         function reconstructObject(parentElement, currentObj, pathPrefix = '') {
              // Collect direct children inputs within config-item divs
             parentElement.querySelectorAll(`:scope > .config-item`).forEach(itemDiv => {
                  const input = itemDiv.querySelector('[data-path]');
                  if (input) {
                     const path = input.dataset.path;
                      // Ensure this input belongs to the current object/array item based on pathPrefix
                      // Examples: pathPrefix="media.channelid_youtube.temp_abc", path="media.channelid_youtube.temp_abc.name" -> key="name"
                      // Examples: pathPrefix="media.channelid_youtube.temp_abc.title_change[0]", path="media.channelid_youtube.temp_abc.title_change[0].pattern" -> key="pattern"
                      // Examples: pathPrefix="", path="global_setting" -> key="global_setting"
                      if (path === pathPrefix || path.startsWith(pathPrefix + '.') || path.match(new RegExp(`^${pathPrefix}\\[\\d+\\]`))) {
                          let relativePath = path.substring(pathPrefix.length > 0 ? pathPrefix.length + 1 : 0);
                          // If the path looks like "title_change[0].pattern", split by '.' first
                          const pathParts = relativePath.split('.');
                          const key = pathParts[0]; // Get the first part as the key for the current level

                          // Handle array indices within the key itself (e.g., title_change[0])
                          const keyMatch = key.match(/^([^\[]+)\[(\d+)\]$/);
                           if (keyMatch) {
                               // This case is handled when iterating through .title-change-item sections, not here
                               // Inputs within array items will have a path like title_change[0].pattern
                                // We need to ensure the recursive call correctly builds the array item first
                           } else {
                                // Simple key
                                 if (!relativePath.includes('[') && !relativePath.includes('.')) { // Only direct keys relative to pathPrefix
                                    const type = input.dataset.type;
                                    let value;
                                     if (input.tagName === 'INPUT') {
                                        if (type === 'boolean') value = input.checked;
                                        else if (type === 'number') value = parseFloat(input.value) || (input.value === '0' ? 0 : null);
                                        else value = input.value;
                                    } else if (input.tagName === 'SELECT') {
                                        value = input.value;
                                    }
                                    currentObj[key] = value;
                                 }
                           }
                      }
                  }
             });

             // Collect direct children sections or lists recursively
              parentElement.querySelectorAll(`:scope > .collapsible-section, :scope > .config-subsection, :scope > .title-change-list`).forEach(sectionElement => {
                  const path = sectionElement.dataset.path;
                  // Ensure this section belongs to the current object/array item based on pathPrefix
                   if (path === pathPrefix || path.startsWith(pathPrefix + '.') || path.match(new RegExp(`^${pathPrefix}\\[\\d+\\]`))) {

                       let relativePath = path.substring(pathPrefix.length > 0 ? pathPrefix.length + 1 : 0);
                       const pathParts = relativePath.split('.');
                       const key = pathParts[0]; // Get the first part as the key for the current level

                       // Handle array indices in the key (e.g., title_change[0])
                       const keyMatch = key.match(/^([^\[]+)\[(\d+)\]$/);

                       if (sectionElement.classList.contains('channel-item')) {
                           // Channel items are handled at the higher level (inside media.channelid_*)
                           // Do nothing here to avoid processing them again
                       } else if (sectionElement.classList.contains('title-change-list')) {
                           // ** Special handling for nested title_change array **
                            const listKey = key; // 'title_change'
                            const listArray = [];
                             sectionElement.querySelectorAll(':scope > .title-change-item').forEach(itemDiv => {
                                 const itemPath = itemDiv.dataset.path; // e.g., media.channelid_youtube.temp_abc.title_change[0]
                                 const itemObj = {};
                                 // Recursively collect data for the array item
                                 reconstructObject(itemDiv, itemObj, itemPath);
                                listArray.push(itemObj);
                             });
                             currentObj[listKey] = listArray;

                       } else if (sectionElement.dataset.type === 'object' && !keyMatch) {
                           // Handle other nested objects (subsections)
                           const subObj = {};
                           currentObj[key] = subObj;
                           reconstructObject(sectionElement, subObj, path); // Recursively collect data
                       } else if (keyMatch && sectionElement.dataset.type === 'object') {
                           // This is an item within an array (like title_change[0]), handled above
                           // Ensure it's not double-processed
                       }
                   }
              });

            return currentObj;
         }

         // Cleanup temporary keys from the collected data before returning
          function cleanTempKeys(obj) {
              if (Array.isArray(obj)) {
                  return obj.map(cleanTempKeys);
              } else if (typeof obj === 'object' && obj !== null) {
                  const newObj = {};
                  for (const key in obj) {
                      if (key !== '_tempKey') {
                          newObj[key] = cleanTempKeys(obj[key]);
                      }
                  }
                  return newObj;
              }
              return obj;
          }


         // Note: The main collection loop outside this helper starts the process
         // The result is already in newConfig

         // Final cleanup of temporary keys
         return cleanTempKeys(newConfig);
    }


    // --- Function: 加载配置 ---
    async function loadConfig() {
        configContainer.innerHTML = '<p>正在加载配置...</p>';
        configStatus.textContent = '';
        saveConfigBtn.disabled = true; // 禁用保存按钮直到加载完成
        refreshConfigBtn.disabled = true; // 禁用刷新按钮直到加载完成

        try {
            const response = await fetch('/getconfig');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            currentConfig = await response.json(); // 保存原始配置
             // 在加载的配置中为现有频道添加临时 key，以便 renderConfig 正确处理
             // 这对于删除现有频道条目是必要的，因为 deleteChannel 使用的是 currentConfig 中的 key
             // 同时确保每个频道有 title_change 数组，即使是空的
             if (currentConfig?.media?.channelid_youtube) {
                 for (const key in currentConfig.media.channelid_youtube) {
                      currentConfig.media.channelid_youtube[key]._tempKey = key;
                      if (!Array.isArray(currentConfig.media.channelid_youtube[key].title_change)) {
                           currentConfig.media.channelid_youtube[key].title_change = [];
                      }
                 }
             }
             if (currentConfig?.media?.channelid_bilibili) {
                 for (const key in currentConfig.media.channelid_bilibili) {
                      currentConfig.media.channelid_bilibili[key]._tempKey = key;
                       if (!Array.isArray(currentConfig.media.channelid_bilibili[key].title_change)) {
                           currentConfig.media.channelid_bilibili[key].title_change = [];
                      }
                 }
             }

            configContainer.innerHTML = ''; // 清空加载提示
            renderConfig(currentConfig, configContainer);
            saveConfigBtn.disabled = false; // 启用保存按钮
        } catch (error) {
            console.error('加载配置失败:', error);
            configContainer.innerHTML = `<p style="color: red;">加载配置失败: ${error.message}</p>`;
            currentConfig = null; // 清除可能不完整的配置
        } finally {
             refreshConfigBtn.disabled = false; // 总是重新启用刷新按钮
        }
    }

    // --- Function: 保存配置 ---
    async function saveConfig() {
        const updatedConfig = collectConfigData();
        console.log("Collected config:", JSON.stringify(updatedConfig, null, 2)); // 打印收集到的数据以供调试

        configStatus.textContent = '正在保存...';
        configStatus.style.color = 'orange';
        saveConfigBtn.disabled = true;
        refreshConfigBtn.disabled = true;

        try {
            // *** 假设你的保存端点是 /saveconfig ***
            const response = await fetch('/saveconfig', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedConfig, null, 2), // 格式化 JSON 便于后端读取和调试
            });

            if (!response.ok) {
                // 尝试读取错误信息
                let errorMsg = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json(); // 假设后端返回 JSON 错误信息
                    errorMsg = errorData.detail || errorData.message || JSON.stringify(errorData);
                } catch (e) {
                    // If response is not JSON or reading fails
                    errorMsg = await response.text() || errorMsg;
                }

                throw new Error(errorMsg);
            }

            // 保存成功后可以重新加载，以确认更改生效
            configStatus.textContent = '配置保存成功！正在刷新...';
            configStatus.style.color = 'green';
            // 稍作延迟再加载，让用户看到成功信息
            setTimeout(loadConfig, 1500);

        } catch (error) {
            console.error('保存配置失败:', error);
            configStatus.textContent = `保存失败: ${error.message}`;
            configStatus.style.color = 'red';
            saveConfigBtn.disabled = false; // 重新启用保存按钮
            refreshConfigBtn.disabled = false; // 重新启用刷新按钮
        }
    }

    // --- 事件监听 ---
    refreshConfigBtn.addEventListener('click', loadConfig);
    saveConfigBtn.addEventListener('click', saveConfig);

    // --- 页面切换逻辑 (集成到 index.js 的 showPage 中) ---
    // 不再独立监听菜单点击，由 index.js 统一管理
    // 配置页面的加载/渲染通过暴露给全局的函数由 index.js 调用
    window.podflowConfig = {
        onShow: function() {
            if (!currentConfig) {
                loadConfig();
            } else {
                // 确保临时 keys 存在
                if (currentConfig?.media?.channelid_youtube) {
                    for (const key in currentConfig.media.channelid_youtube) {
                        if (!currentConfig.media.channelid_youtube[key]._tempKey) {
                            currentConfig.media.channelid_youtube[key]._tempKey = key;
                        }
                        if (!Array.isArray(currentConfig.media.channelid_youtube[key].title_change)) {
                            currentConfig.media.channelid_youtube[key].title_change = [];
                        }
                    }
                }
                if (currentConfig?.media?.channelid_bilibili) {
                    for (const key in currentConfig.media.channelid_bilibili) {
                        if (!currentConfig.media.channelid_bilibili[key]._tempKey) {
                            currentConfig.media.channelid_bilibili[key]._tempKey = key;
                        }
                        if (!Array.isArray(currentConfig.media.channelid_bilibili[key].title_change)) {
                            currentConfig.media.channelid_bilibili[key].title_change = [];
                        }
                    }
                }
                renderConfig(currentConfig, configContainer);
            }
        }
    };

    // --- Menu toggle button logic (由 index.js 统一管理，此处不再重复绑定) ---
    // index.js 已经处理了 toggleMenu 逻辑

     // --- Initial load ---
    // 配置页面的初始加载由 index.js 的 showPage 触发，此处不做自动加载
});