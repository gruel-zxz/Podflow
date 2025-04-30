(function() {
    // --- 缓存常用 DOM 节点 ---
    // 菜单相关
    const menu = document.getElementById('menu');
    const toggleMenuBtn = document.getElementById('toggleMenu');
    // 页面容器
    const pages = {
        pageChannel: document.getElementById('pageChannel'),
        pageMessage: document.getElementById('pageMessage')
    };
    // Channel ID 相关表单
    const inputForm = document.getElementById('inputForm');
    const inputOutput = document.getElementById('inputOutput');
    const pasteBtn = document.getElementById('pasteBtn');
    const copyBtn = document.getElementById('copyBtn');
    const clearBtn = document.getElementById('clearBtn');
    // 主进度条相关
    const mainProgress = document.getElementById('mainProgress');
    const progressStatus = document.getElementById('progressStatus');
    const progressPercentage = document.getElementById('progressPercentage');
    // 消息显示区域
    const messageArea = document.getElementById('messageArea'); // Podflow 消息
    const messageHttp = document.getElementById('messageHttp'); // HTTP 消息
    const messageDownload = document.getElementById('messageDownload'); // 下载进度条容器
    const downloadLabel = document.getElementById('downloadLabel'); // 下载进度标题 (假设存在)

    // --- 状态变量 ---
    let lastMessage = { schedule: [], podflow: [], http: [], download: [] }; // 缓存上一次的消息数据
    let userScrolled = { // 分别跟踪每个滚动区域的用户滚动状态
        messageArea: false,
        messageHttp: false,
        messageDownload: false
    };
    let eventSource = null; // 用于存储 EventSource 实例

    // --- 二维码生成 ---
    /**
     * 为指定的 DOM 容器生成二维码
     * @param {HTMLElement} container - 要生成二维码的容器元素，需要有 data-url 属性
     */
    function generateQRCodeForNode(container) {
        const rootStyles = getComputedStyle(document.documentElement);
        const textColor = rootStyles.getPropertyValue('--text-color').trim();
        const inputBg = rootStyles.getPropertyValue('--input-bg').trim();
        const url = container.dataset.url;
        container.innerHTML = ''; // 清空容器
        if (url) {
            try {
                new QRCode(container, {
                    text: url,
                    width: 220,
                    height: 220,
                    colorDark: textColor,
                    colorLight: inputBg,
                    correctLevel: QRCode.CorrectLevel.L
                });
            } catch (e) {
                console.error("生成二维码失败:", e);
                container.textContent = '二维码生成失败';
            }
        } else {
            container.textContent = 'URL 未提供';
        }
    }

    // --- 菜单控制 ---
    /**
     * 切换侧边菜单的显示/隐藏状态
     */
    function toggleMenu() {
        menu.classList.toggle('hidden');
        const isHidden = menu.classList.contains('hidden');
        toggleMenuBtn.style.left = isHidden ? '0px' : 'var(--menu-width)';
        toggleMenuBtn.textContent = isHidden ? '❯' : '❮';
    }

    /**
     * 根据页面 ID 显示对应的页面内容，并管理 SSE 连接
     * @param {string} pageId - 'pageChannel' 或 'pageMessage'
     */
    function showPage(pageId) {
        // 隐藏所有页面
        Object.values(pages).forEach(page => page.style.display = 'none');

        // 显示目标页面
        if (pages[pageId]) {
            pages[pageId].style.display = 'block';

            // 手机模式下，切换页面时自动隐藏菜单
            if (window.innerWidth <= 600 && !menu.classList.contains('hidden')) {
                toggleMenu();
            }

            // --- SSE 连接管理 ---
            if (pageId === 'pageMessage') {
                startMessageStream(); // 显示消息页面时，启动 SSE 连接
            } else {
                stopMessageStream(); // 切换到其他页面时，关闭 SSE 连接
            }
        } else {
            console.warn(`未找到 ID 为 "${pageId}" 的页面`);
        }
    }

    // --- 滚动处理 ---
    /**
     * 监听滚动事件，判断用户是否手动滚动了消息区域
     * @param {Event} event - 滚动事件对象
     */
    function onUserScroll(event) {
        const element = event.target;
        const containerId = element.id; // 获取滚动容器的ID
        if (userScrolled.hasOwnProperty(containerId)) { // 确保是我们关心的容器
            // 判断是否滚动到接近底部 (增加 10px 容差)
            const isNearBottom = element.scrollHeight - element.scrollTop <= element.clientHeight + 10;
            userScrolled[containerId] = !isNearBottom; // 如果没在底部，则标记为用户已滚动
        }
    }

    // --- 消息处理 ---
    /**
     * 更新主进度条的状态和百分比
     * @param {Array} scheduleData - 包含状态和进度的数组，例如 ["状态", 0.5]
     */
    function updateProgress(scheduleData) {
        if (Array.isArray(scheduleData) && scheduleData.length === 2) {
            const [status, progress] = scheduleData;
            const percentage = progress * 100;

            // 确保 DOM 元素存在
            if (!mainProgress || !progressStatus || !progressPercentage) {
                console.warn("进度条相关 DOM 元素未找到");
                return;
            }

            if (status === "准备中" || status === "构建中") {
                mainProgress.style.width = `${percentage}%`;
                progressStatus.textContent = status;
                progressPercentage.textContent = `${percentage.toFixed(2)}%`;
            } else if (status === "已完成") {
                mainProgress.style.width = '100%';
                progressStatus.textContent = '已完成';
                progressPercentage.textContent = '100.00%'; // 保持格式一致
            }
            // 可以选择性地处理其他状态或进度为 null/undefined 的情况
        } else {
                // console.warn("接收到的进度数据格式不正确:", scheduleData);
        }
    }

    /**
     * 创建单个消息元素的 DOM 结构
     * @param {string} message - 包含 HTML 的消息字符串
     * @returns {HTMLDivElement} - 创建的消息元素
     */
    function createMessageElement(message) {
        const div = document.createElement('div');
        // 使用 innerHTML，因为消息内容可能包含 HTML 标签 (如二维码容器)
        div.innerHTML = message;
        div.className = 'message'; // 假设 'message' 是单个消息的样式类
        return div;
    }

    /**
     * 处理消息元素内部的二维码容器
     * @param {HTMLElement} element - 包含 .qrcode-container 的父元素
     */
    function processQRCodeContainers(element) {
        const qrContainers = element.querySelectorAll('.qrcode-container');
        qrContainers.forEach(container => {
            if (container.dataset.url) {
                generateQRCodeForNode(container);
            } else {
                console.log('容器中未提供 URL，跳过二维码生成:', container);
                container.textContent = '未提供二维码 URL';
            }
        });
    }

    /**
     * 更新消息显示区域 (Podflow / HTTP)，保留向上更新四行的逻辑
     * @param {HTMLElement} container - 消息容器元素 (messageArea 或 messageHttp)
     * @param {string[]} newMessages - 最新的消息数组
     * @param {string[]} oldMessages - 上一次的消息数组
     */
    function appendMessages(container, newMessages, oldMessages) {
        if (!container) return; // 防御性编程

        const containerId = container.id;
        const wasAtBottom = !userScrolled[containerId] && (container.scrollHeight - container.scrollTop <= container.clientHeight + 10);
        const newLength = newMessages.length;
        const oldLength = oldMessages.length;

        // --- 主要逻辑：比较新旧消息，更新 DOM ---
        if (newLength === oldLength && newLength > 0) {
            // --- 长度相同：检查最后几条消息是否有变化 ---
            let replaceCount = 1; // 默认只检查最后一条
            const lastMessageContent = newMessages[newLength - 1];
            // 特殊逻辑：如果最后一条消息包含特定文本，则检查最后四条
            if (lastMessageContent.includes("未扫描") || lastMessageContent.includes("二维码超时, 请重试")) {
                replaceCount = Math.min(4, newLength); // 最多检查4条或数组长度
            }

            // 从后往前比较并替换变化的元素
            for (let i = 0; i < replaceCount; i++) {
                const index = newLength - 1 - i;
                const newMessage = newMessages[index];
                const oldMessage = oldMessages[index];

                if (newMessage !== oldMessage) {
                    const div = createMessageElement(newMessage);
                    processQRCodeContainers(div); // 处理二维码
                    const childToReplace = container.children[index];
                    if (childToReplace) {
                        container.replaceChild(div, childToReplace);
                    } else {
                        // 如果预期的子元素不存在（理论上不应发生），则追加
                        console.warn(`试图替换索引 ${index} 的子元素，但未找到。将追加。`);
                        container.appendChild(div);
                    }
                }
            }
        } else if (newLength > oldLength) {
            // --- 新消息比旧消息多 ---
            // 1. 如果旧消息存在，替换旧消息数组中最后一条对应的 DOM 元素
            if (oldLength > 0) {
                const replaceIndex = oldLength - 1;
                const newMessageToReplace = newMessages[replaceIndex];
                const oldMessageToCompare = oldMessages[replaceIndex];

                // 仅当内容实际改变时才替换
                if (newMessageToReplace !== oldMessageToCompare) {
                    const div = createMessageElement(newMessageToReplace);
                    processQRCodeContainers(div); // 处理二维码
                    const childToReplace = container.children[replaceIndex]; // 替换对应索引的元素
                    if (childToReplace) {
                        container.replaceChild(div, childToReplace);
                    } else {
                        console.warn(`试图替换索引 ${replaceIndex} 的子元素，但未找到。`);
                        // 此处可以选择追加或其他错误处理
                    }
                }
            }

            // 2. *** 优化点：使用 DocumentFragment 批量追加新增的消息 ***
            const fragment = document.createDocumentFragment();
            for (let i = oldLength; i < newLength; i++) {
                const div = createMessageElement(newMessages[i]);
                processQRCodeContainers(div); // 处理二维码
                fragment.appendChild(div);
            }
            container.appendChild(fragment); // 一次性追加所有新消息

        } else if (newLength < oldLength) {
            // --- 新消息比旧消息少（通常意味着列表被清空或重置）---
            // 简单处理：清空容器，重新添加所有新消息
            console.log("新消息数量少于旧消息，将重新渲染整个列表。");
            container.innerHTML = ''; // 清空
            const fragment = document.createDocumentFragment();
            newMessages.forEach(msg => {
                const div = createMessageElement(msg);
                processQRCodeContainers(div);
                fragment.appendChild(div);
            });
            container.appendChild(fragment);
            // 重置滚动状态，因为内容完全变了
            userScrolled[containerId] = false;
        }

        // --- 自动滚动到底部 ---
        if (wasAtBottom && !userScrolled[containerId]) {
            container.scrollTop = container.scrollHeight;
        }
    }


    // --- 下载进度条处理 ---
    /**
     * 创建单个下载进度条的 DOM 结构 (!!! 内部逻辑未修改 !!!)
     * @param {number} i - 索引
     * @param {number} percentageText - 进度百分比 (0-1)
     * @param {string} time - 剩余时间
     * @param {string} speed - 下载速度
     * @param {string} part - 分片信息
     * @param {string} status - 状态文本
     * @param {string} idname - 标识名称
     * @param {string} nameText - 文件名 (可能需要滚动)
     * @param {string} file - 文件后缀或类型
     * @returns {HTMLDivElement} - 创建的进度条容器元素
     */
    function addProgressBar(i, percentageText, time, speed, part, status, idname, nameText, file){
        const download = document.createElement('div');
        download.className = 'download-container';
        // 创建 idname 文本节点（只创建一次）
        const idnameText = document.createElement('div');
        idnameText.className = 'scroll-text'; // 可能也需要滚动？根据 CSS 定义
    idnameText.innerHTML = '  ' + idname; // 前导空格？
        // 创建文件信息部分
        const fileInfo = document.createElement('div');
        fileInfo.className = 'scroll'; // 类名可能与滚动有关
        const filesuffix = document.createElement('div');
        filesuffix.className = 'scroll-suffix';
        filesuffix.innerHTML = file;
        // 创建滚动文本区域
        const scroll = document.createElement('div');
        scroll.className = 'scroll-container';
        const namebar = document.createElement('div');
        namebar.className = 'scroll-content';
        const filename = document.createElement('div');
        filename.className = 'scroll-text';
        filename.innerHTML = nameText;
        // 组合元素
        namebar.appendChild(filename);
        scroll.appendChild(namebar);
        fileInfo.appendChild(scroll);
        fileInfo.appendChild(filesuffix);
        download.appendChild(idnameText);
        download.appendChild(fileInfo);
        // 延迟测量文本宽度，决定是否滚动 (!!! 原始逻辑 !!!)
        setTimeout(() => {
        const contentWidth = filename.scrollWidth;  // 单份文本宽度
            const containerWidth = scroll.clientWidth;
            if (contentWidth > containerWidth) {
                // 需要滚动，添加第二份文本实现无缝滚动
                const filename1 = document.createElement('div');
                filename1.className = 'scroll-text';
                filename1.innerHTML = nameText;
                namebar.appendChild(filename1);
                // 重新计算宽度，这次是双倍宽度中的单份宽度用于计算时间
                const singleContentWidth = namebar.scrollWidth / 2;
                const scrollSpeed = 30; // 滚动速度 (像素/秒)
                const duration = singleContentWidth / scrollSpeed;
                namebar.style.animationDuration = duration + 's';
                // 延迟添加滚动类
                setTimeout(() => {
                        namebar.classList.add('scrolling');
                }, 1500); // 1.5秒延迟
            } else {
                // 不需要滚动，确保移除动画类和样式
                namebar.classList.remove('scrolling');
                namebar.style.animationDuration = '';
            }
        }, 0); // 使用 setTimeout 0ms 延迟，等待浏览器渲染后测量
        // 进度条部分
        const pbBar = document.createElement('div');
        pbBar.className = 'pb-bar';
        const pbProgress = document.createElement('div');
        pbProgress.className = 'pb-progress pb-animated'; // 假设有动画效果
        pbProgress.style.width = `${percentageText * 100}%`;
        pbProgress.id = 'pbProgress' + (i+1); // ID 基于索引
        const pbStatusText = document.createElement('div');
        pbStatusText.className = 'pb-status-text';
        pbStatusText.innerHTML = status;
        pbStatusText.id = 'pbStatusText' + (i+1);
        const pbPercentageText = document.createElement('div');
        pbPercentageText.className = 'pb-percentage-text';
        pbPercentageText.innerHTML = `${(percentageText * 100).toFixed(2)}%`;
        pbPercentageText.id = 'pbPercentageText' + (i+1);
        pbBar.appendChild(pbProgress);
        pbBar.appendChild(pbStatusText);
        pbBar.appendChild(pbPercentageText);
        download.appendChild(pbBar);
        // 速度、分片、时间部分
        const speedContainer = document.createElement('div'); // 使用 div 而非 table 可能更灵活
        speedContainer.className = 'scroll';
        const speedText = document.createElement('div');
        speedText.className = 'speed-text';
        speedText.innerHTML = speed;
        speedText.id = 'speedText' + (i+1);
        const partText = document.createElement('div');
        partText.className = 'speed-text';
        partText.innerHTML = part;
        partText.id = 'partText' + (i+1);
        const timeText = document.createElement('div');
        timeText.className = 'time-text';
        timeText.innerHTML = time;
        timeText.id = 'timeText' + (i+1);
        speedContainer.appendChild(speedText);
        speedContainer.appendChild(partText);
        speedContainer.appendChild(timeText);
        download.appendChild(speedContainer);
        return download;
    }

    /**
     * 更新下载进度条区域 (!!! 内部逻辑未修改 !!!)
     * @param {HTMLElement} container - 下载进度条容器 (messageDownload)
     * @param {Array[]} newMessages - 最新的下载信息数组，每个元素是 [percentage, time, speed, part, status, idname, nameText, file]
     * @param {Array[]} oldMessages - 上一次的下载信息数组
     */
    function appendBar(container, newMessages, oldMessages) {
        if (!container) return; // 防御

        const containerId = container.id;
        const wasAtBottom = !userScrolled[containerId] && (container.scrollHeight - container.scrollTop <= container.clientHeight + 10);
        const newlength = newMessages.length;
        const oldlength = oldMessages.length;

        // --- 原始逻辑开始 ---
        if (newlength > 0) {
            if (downloadLabel) downloadLabel.textContent = '下载进度：'; // 更新标题

            // --- 更新已存在的进度条 (对应旧消息列表中的最后一项) ---
            if (oldlength !== 0) {
                // 假设进度条是按顺序添加的，旧消息的最后一个对应容器中的第一个子元素（因为是 insertBefore(firstChild)）
                // 或者需要更可靠的方式定位？如果 ID 总是连续且从1开始，可以查找 #pbProgress{oldlength} 的父元素
                // 这里我们假设原始逻辑依赖于 DOM 结构顺序
                const childToUpdate = container.children[0]; // 找到对应旧列表最后一项的DOM元素

                if(childToUpdate) {
                    const newMessage = newMessages[oldlength - 1];
                    const oldMessage = oldMessages[oldlength - 1];

                    // 比较整个数组是否相同可能更可靠，或者比较关键字段
                    if (JSON.stringify(newMessage) !== JSON.stringify(oldMessage)) {
                        const [percentageText, time, speed, part, status] = newMessage; // 只需要更新这些字段
                        const progressElement = childToUpdate.querySelector('#pbProgress' + oldlength);
                        const statusElement = childToUpdate.querySelector('#pbStatusText' + oldlength);
                        const percentageElement = childToUpdate.querySelector('#pbPercentageText' + oldlength);
                        const speedElement = childToUpdate.querySelector('#speedText' + oldlength);
                        const partElement = childToUpdate.querySelector('#partText' + oldlength);
                        const timeElement = childToUpdate.querySelector('#timeText' + oldlength);

                        if (progressElement) progressElement.style.width = `${percentageText * 100}%`;
                        if (statusElement) statusElement.innerHTML = status;
                        if (percentageElement) percentageElement.innerHTML = `${(percentageText * 100).toFixed(2)}%`;
                        if (speedElement) speedElement.innerHTML = speed;
                        if (partElement) partElement.innerHTML = part;
                        if (timeElement) timeElement.innerHTML = time;
                    }
                } else {
                    console.warn(`appendBar: 尝试更新旧进度条 #${oldlength} 时未找到对应的 DOM 元素。`);
                }
            }

            // --- 添加新的进度条 ---
            if (newlength !== oldlength) {
                // *** 优化点：同样可以使用 DocumentFragment 批量添加 ***
                const fragment = document.createDocumentFragment();
                for (let i = oldlength; i < newlength; i++) {
                    const messageContent = newMessages[i];
                    // 解构赋值，确保顺序正确
                    const [percentageText, time, speed, part, status, idname, nameText, file] = messageContent;
                    // 调用未修改的 addProgressBar 来创建元素
                    const downloadElement = addProgressBar(i, percentageText, time, speed, part, status, idname, nameText, file);
                    fragment.appendChild(downloadElement);
                }
                // 使用 insertBefore 将新的进度条批量插入到容器顶部
                container.insertBefore(fragment, container.firstChild);
            }
        } else {
                // 如果新消息为空，可以选择清空进度条区域或显示提示
            if (downloadLabel) downloadLabel.textContent = '暂无下载任务';
            // container.innerHTML = ''; // 清空旧的进度条
        }
        // --- 原始逻辑结束 ---

        // --- 自动滚动到底部 (对于进度条区域，通常是希望看到最新的，即顶部，所以可能不需要自动滚动到底部) ---
        // 如果确实需要滚动到底部（显示旧的在上面）：
        // if (wasAtBottom && !userScrolled[containerId]) {
    //   container.scrollTop = container.scrollHeight;
        // }
        // 如果希望保持在顶部看到新添加的：
        if (newlength > oldlength && !userScrolled[containerId]) { // 如果是新增了进度条且用户没滚动
            container.scrollTop = 0; // 滚动到顶部
        } else if (wasAtBottom && !userScrolled[containerId]) { // 如果是更新现有条目且之前在底部
            container.scrollTop = container.scrollHeight; // 保持在底部
        }
    }


    // --- SSE (Server-Sent Events) 处理 ---
    /**
     * 启动 SSE 连接，接收服务器推送的消息
     */
    function startMessageStream() {
        // 如果已存在连接，先关闭
        if (eventSource) {
            console.log("SSE 连接已存在，将重新启动...");
            eventSource.close();
        }

        console.log("正在启动 SSE 连接到 /stream ...");
        eventSource = new EventSource('/stream');

        // 监听 'message' 事件 (默认事件)
        eventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);

                // --- 使用接收到的数据更新 UI ---
                // 确保 lastMessage 和 data 结构完整，提供默认值防止错误
                lastMessage = lastMessage || { schedule: [], podflow: [], http: [], download: [] };
                data.schedule = data.schedule || [];
                data.podflow = data.podflow || [];
                data.http = data.http || [];
                data.download = data.download || [];

                // 1. 更新主进度条
                // 使用 stringify 比较是为了简单深比较，对于小对象性能影响不大
                if (JSON.stringify(data.schedule) !== JSON.stringify(lastMessage.schedule)) {
                    updateProgress(data.schedule);
                    lastMessage.schedule = data.schedule; // 更新缓存
                }

                // 2. 更新 Podflow 消息区域
                if (JSON.stringify(data.podflow) !== JSON.stringify(lastMessage.podflow)) {
                    appendMessages(messageArea, data.podflow, lastMessage.podflow || []);
                    lastMessage.podflow = [...data.podflow]; // 更新缓存 (使用浅拷贝)
                }

                // 3. 更新 HTTP 消息区域
                if (JSON.stringify(data.http) !== JSON.stringify(lastMessage.http)) {
                    appendMessages(messageHttp, data.http, lastMessage.http || []);
                    lastMessage.http = [...data.http]; // 更新缓存 (使用浅拷贝)
                }

                // 4. 更新下载进度条区域
                if (JSON.stringify(data.download) !== JSON.stringify(lastMessage.download)) {
                    appendBar(messageDownload, data.download, lastMessage.download || []);
                    lastMessage.download = [...data.download]; // 更新缓存 (使用浅拷贝)
                }

            } catch (error) {
                console.error('处理 SSE 消息失败:', error, '原始数据:', event.data);
            }
        };

        // 监听错误事件
        eventSource.onerror = function(error) {
            console.error('SSE 连接发生错误:', error);
            // EventSource 默认会自动尝试重连，通常不需要手动处理
            // 如果需要彻底停止，可以在这里关闭
            // eventSource.close();
            // eventSource = null;
            // 可以考虑在这里添加 UI 提示，告知用户连接中断
        };

        // 监听连接打开事件 (可选)
        eventSource.onopen = function() {
            console.log("SSE 连接已成功建立。");
            // 连接成功后，可能需要立即获取一次全量数据？或者依赖于服务器推送
        };

        console.log("SSE 事件监听器已设置。");
    }

    /**
     * 停止 SSE 连接
     */
    function stopMessageStream() {
        if (eventSource) {
            eventSource.close(); // 关闭连接
            eventSource = null; // 清除引用
            console.log("SSE 连接已关闭。");
        }
    }

    // --- 事件监听器绑定 ---
    // 滚动事件 (确保所有相关容器都监听)
    if (messageArea) messageArea.addEventListener('scroll', onUserScroll);
    if (messageHttp) messageHttp.addEventListener('scroll', onUserScroll);
    if (messageDownload) messageDownload.addEventListener('scroll', onUserScroll); // 添加 messageDownload 的监听

    // Channel ID 表单异步提交
    if (inputForm) {
        inputForm.addEventListener('submit', function(event) {
            event.preventDefault(); // 阻止表单默认提交行为
            const content = inputOutput.value.trim(); // 获取并去除首尾空格
            if (!content) {
                alert('请输入内容！');
                return;
            }
            // 可以添加一个加载状态提示
            console.log("正在提交内容获取 Channel ID...");
            fetch('getid', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json' // 明确希望接收 JSON
                },
                body: JSON.stringify({ content: content }) // 发送 JSON 数据
            })
            .then(response => {
                if (!response.ok) {
                    // 如果服务器返回错误状态码，尝试读取错误信息
                    return response.json().catch(() => {
                        // 如果无法解析 JSON 错误体，抛出通用错误
                        throw new Error(`网络响应错误: ${response.status} ${response.statusText}`);
                    }).then(errorData => {
                        // 如果解析成功，抛出包含服务器信息的错误
                        throw new Error(errorData.error || `请求失败: ${response.status}`);
                    });
                }
                return response.json(); // 解析成功的 JSON 响应
            })
            .then(data => {
                if (data && data.response) {
                     inputOutput.value = data.response; // 更新输入框内容
                    console.log("成功获取 Channel ID:", data.response);
                } else {
                    console.warn("服务器响应格式不正确:", data);
                    alert('服务器返回数据格式错误！');
                }
            })
            .catch(error => {
                console.error('获取 Channel ID 请求失败:', error);
                alert(`请求失败：${error.message || '请检查网络或联系管理员'}`);
            });
        });
    }

    // 粘贴按钮
    if (pasteBtn) {
        pasteBtn.addEventListener('click', function() {
            if (navigator.clipboard && navigator.clipboard.readText) {
                navigator.clipboard.readText()
                    .then(text => {
                        inputOutput.value = text;
                        inputOutput.focus(); // 粘贴后聚焦
                    })
                    .catch(err => {
                        console.warn("通过 navigator.clipboard 读取剪贴板失败:", err);
                        alert("无法自动读取剪贴板，请手动粘贴 (Ctrl+V)！");
                        inputOutput.focus(); // 提示后聚焦，方便手动粘贴
                    });
            } else {
                // 备选方案 (可能在非 HTTPS 或旧浏览器中需要)
                try {
                    inputOutput.focus();
                    // execCommand 已不推荐使用，但作为后备
                    if (!document.execCommand('paste')) {
                        throw new Error('execCommand paste failed');
                    }
                } catch (err) {
                    console.warn("execCommand 粘贴失败:", err);
                    alert("您的浏览器不支持自动粘贴，请手动操作 (Ctrl+V)！");
                    inputOutput.focus();
                }
            }
        });
    }

    // 复制按钮
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            const textToCopy = inputOutput.value;
            if (!textToCopy) return; // 没有内容则不复制

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(textToCopy)
                    .then(() => {
                        // 可以给用户一个成功的视觉反馈，例如按钮变色或提示
                        console.log("内容已复制到剪贴板");
                        // alert("已复制！"); // 或者使用更友好的提示方式
                    })
                    .catch(err => {
                        console.warn("通过 navigator.clipboard 写入剪贴板失败:", err);
                        alert("自动复制失败，请手动选择文本后按 Ctrl+C 复制！");
                        inputOutput.select(); // 选中内容方便手动复制
                    });
            } else {
                // 备选方案
                try {
                    inputOutput.select(); // 选中输入框中的文本
                    if (!document.execCommand('copy')) { // 执行复制命令
                        throw new Error('execCommand copy failed');
                    }
                    console.log("内容已通过 execCommand 复制");
                    // alert("已复制！");
                } catch (err) {
                    console.warn("execCommand 复制失败:", err);
                    alert("您的浏览器不支持自动复制，请手动选择文本后按 Ctrl+C 复制！");
                    inputOutput.select();
                }
            }
        });
    }

    // 清空按钮
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            inputOutput.value = '';
            inputOutput.focus(); // 清空后聚焦
        });
    }

    // 菜单项点击事件 (使用事件委托)
    if (menu) {
        menu.addEventListener('click', function(event) {
            // 确保点击的是 LI 元素且具有 data-page 属性
            const target = event.target.closest('li[data-page]');
            if (target) {
                const pageId = target.dataset.page;
                showPage(pageId); // 调用页面切换函数
            }
        });
    }

    // 菜单切换按钮
    if (toggleMenuBtn) {
        toggleMenuBtn.addEventListener('click', toggleMenu);
    }

    // --- 初始化 ---
    // 根据屏幕宽度初始化菜单状态
    if (window.innerWidth <= 600) {
        menu.classList.add('hidden');
        toggleMenuBtn.style.left = '0px';
        toggleMenuBtn.textContent = '❯';
    } else {
        // 确保大屏幕下按钮初始状态正确 (如果默认不是展开的话)
        if (menu.classList.contains('hidden')) {
            toggleMenuBtn.style.left = '0px';
            toggleMenuBtn.textContent = '❯';
        } else {
            toggleMenuBtn.style.left = 'var(--menu-width)';
            toggleMenuBtn.textContent = '❮';
        }
    }

    // 初始化时显示默认页面 (例如消息页面)
    showPage('pageMessage');

})(); // IIFE 结束