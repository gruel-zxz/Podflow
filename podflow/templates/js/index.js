(function() {
    // --- 缓存常用 DOM 节点 ---
    // 菜单相关
    const menu = document.getElementById('menu');
    const toggleMenuBtn = document.getElementById('toggleMenu');
    const menuBackdrop = document.getElementById('menuBackdrop');
    // 页面容器
    const pages = {
        pageChannel: document.getElementById('pageChannel'),
        pageMessage: document.getElementById('pageMessage'),
        pageConfig: document.getElementById('pageConfig')
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
    const alwaysUseYoutubeCookie = document.getElementById('alwaysUseYoutubeCookie');
    const youtubeCookieStatus = document.getElementById('youtubeCookieStatus');
    const immediateUpdateBtn = document.getElementById('immediateUpdateBtn');
    const favoriteUpdateCountdown = document.getElementById('favoriteUpdateCountdown');
    const toggleConfigDisplay = document.getElementById('toggleConfigDisplay');
    const configContent = document.getElementById('configContent');

    // --- 状态变量 ---
    let lastMessage = { schedule: [], podflow: [], http: [], download: [] }; // 缓存上一次的消息数据
    let userScrolled = { // 分别跟踪每个滚动区域的用户滚动状态
        messageArea: false,
        messageHttp: false,
        messageDownload: false
    };
    let eventSource = null; // 用于存储 EventSource 实例
    let reconnectAttempts = 0; // 重连尝试次数
    let reconnectTimer = null; // 重连定时器
    const MAX_RECONNECT_ATTEMPTS = 10; // 最大重连次数
    const BASE_RECONNECT_DELAY = 1000; // 基础重连延迟 (ms)
    let favoriteUpdateNextRun = null;
    let serverOffset = 0; // 记录服务器时间与本地时间的毫秒偏差

    function renderFavoriteUpdateCountdown() {
        if (!favoriteUpdateCountdown) return;
        if (!favoriteUpdateNextRun) {
            favoriteUpdateCountdown.textContent = '倒计时：更新运行中';
            return;
        }

        // 使用 Date.now() + serverOffset 校准当前服务器毫秒时间
        const adjustedNowMs = Date.now() + serverOffset;
        
        // 计算剩余秒数 (favoriteUpdateNextRun 为秒级时间戳)
        const remaining = Math.max(0, Math.ceil(favoriteUpdateNextRun - adjustedNowMs / 1000));

        const hours = String(Math.floor(remaining / 3600)).padStart(2, '0');
        const minutes = String(Math.floor((remaining % 3600) / 60)).padStart(2, '0');
        const seconds = String(Math.floor(remaining % 60)).padStart(2, '0');
        favoriteUpdateCountdown.textContent = `倒计时：${hours}:${minutes}:${seconds}`;
    }

    // 辅助函数：同步一次服务器时间偏差
    async function syncServerOffset() {
        try {
            const startTime = Date.now();
            const res = await fetch('/timestamp');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const { timestamp: serverTimeSec } = await res.json();
            
            // 考虑单程网络延迟估计 (RTT / 2)
            const networkLatency = (Date.now() - startTime) / 2;
            const serverTimeMs = serverTimeSec * 1000 + networkLatency;
            
            // 计算偏差：服务端毫秒数 - 客户端毫秒数
            serverOffset = serverTimeMs - Date.now();
        } catch (error) {
            console.error('同步服务器时间偏差失败:', error);
        }
    }

    async function loadFavoriteUpdateStatus() {
        try {
            // 并行请求状态与服务器时间戳，减少等待时长
            const [statusRes] = await Promise.all([
                fetch('/favorite-update-status'),
                syncServerOffset()
            ]);

            if (!statusRes.ok) throw new Error(`HTTP ${statusRes.status}`);
            const data = await statusRes.json();
            
            favoriteUpdateNextRun = data.next_run;
            if (immediateUpdateBtn) immediateUpdateBtn.disabled = !data.active;
            renderFavoriteUpdateCountdown();
        } catch (error) {
            console.error('加载特别关注状态失败:', error);
            favoriteUpdateNextRun = null;
            if (immediateUpdateBtn) immediateUpdateBtn.disabled = true;
            if (favoriteUpdateCountdown) favoriteUpdateCountdown.textContent = '倒计时：状态不可用';
        }
    }

    async function requestImmediateUpdate() {
        if (!immediateUpdateBtn) return;
        immediateUpdateBtn.disabled = true;
        try {
            const response = await fetch('/favorite-update-status', { method: 'POST' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            favoriteUpdateNextRun = null;
            renderFavoriteUpdateCountdown();
        } catch (error) {
            console.error('立即更新请求失败:', error);
            await loadFavoriteUpdateStatus();
        }
    }

    async function loadYoutubeCookieSetting() {
        if (!alwaysUseYoutubeCookie) return;
        try {
            const response = await fetch('/youtube-cookie-setting');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            alwaysUseYoutubeCookie.checked = data.enabled;
            alwaysUseYoutubeCookie.disabled = !data.cookie_available;
            if (youtubeCookieStatus) {
                youtubeCookieStatus.textContent = data.cookie_available
                    ? '（Cookie 可用）'
                    : '（Cookie 不可用，开关已禁用）';
            }
        } catch (error) {
            console.error('加载 YouTube Cookie 设置失败:', error);
            alwaysUseYoutubeCookie.disabled = true;
            if (youtubeCookieStatus) youtubeCookieStatus.textContent = '（设置加载失败）';
        }
    }

    async function saveYoutubeCookieSetting() {
        try {
            const response = await fetch('/youtube-cookie-setting', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: alwaysUseYoutubeCookie.checked })
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
        } catch (error) {
            console.error('保存 YouTube Cookie 设置失败:', error);
            alwaysUseYoutubeCookie.checked = !alwaysUseYoutubeCookie.checked;
            if (youtubeCookieStatus) youtubeCookieStatus.textContent = '（保存失败）';
        }
    }

    // --- 连接状态指示器 ---
    function updateConnectionStatus(status, message) {
        let indicator = document.getElementById('connection-status');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'connection-status';
            indicator.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;padding:6px 12px;text-align:center;font-size:13px;transition:opacity 0.3s;pointer-events:none;';
            document.body.appendChild(indicator);
        }
        if (status === 'connected') {
            indicator.style.backgroundColor = '#4caf50';
            indicator.style.color = '#fff';
            indicator.textContent = message || '✅ 已连接';
            // 2秒后自动隐藏
            setTimeout(() => { indicator.style.opacity = '0'; }, 2000);
        } else if (status === 'reconnecting') {
            indicator.style.backgroundColor = '#ff9800';
            indicator.style.color = '#fff';
            indicator.style.opacity = '1';
            indicator.textContent = message || `⚠️ 连接中断，正在重连 (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`;
        } else if (status === 'disconnected') {
            indicator.style.backgroundColor = '#f44336';
            indicator.style.color = '#fff';
            indicator.style.opacity = '1';
            indicator.innerHTML = message || '❌ 连接已断开 <button onclick="location.reload()" style="margin-left:8px;padding:2px 8px;border:none;border-radius:3px;cursor:pointer;">刷新页面</button>';
        } else {
            indicator.style.opacity = '0';
        }
    }

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
    function setMenuVisibility(isHidden) {
        menu.classList.toggle('hidden', isHidden);
        if (menuBackdrop) menuBackdrop.classList.toggle('visible', !isHidden && window.innerWidth <= 600);
        if (!toggleMenuBtn) return;
        toggleMenuBtn.setAttribute('aria-expanded', String(!isHidden));
        toggleMenuBtn.setAttribute('aria-label', isHidden ? '显示侧边栏' : '隐藏侧边栏');
    }

    function toggleMenu() {
        setMenuVisibility(!menu.classList.contains('hidden'));
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
            menu.querySelectorAll('li[data-page]').forEach(item => {
                item.classList.toggle('active', item.dataset.page === pageId);
            });

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

            // --- 配置页面加载 ---
            if (pageId === 'pageConfig' && window.podflowConfig) {
                window.podflowConfig.onShow();
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

    function resetMessageView() {
        lastMessage = { schedule: [], podflow: [], http: [], download: [] };
        userScrolled = {
            messageArea: false,
            messageHttp: false,
            messageDownload: false
        };

        if (mainProgress) mainProgress.style.width = '0%';
        if (progressStatus) progressStatus.textContent = '准备中';
        if (progressPercentage) progressPercentage.textContent = '0.00%';
        if (messageArea) {
            messageArea.innerHTML = '';
            messageArea.scrollTop = 0;
        }
        if (messageHttp) {
            messageHttp.innerHTML = '';
            messageHttp.scrollTop = 0;
        }
        if (messageDownload) {
            messageDownload.innerHTML = '';
            messageDownload.scrollTop = 0;
        }
        if (downloadLabel) downloadLabel.textContent = '';
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
     * 更新下载进度条区域（修复切页卡死与多任务更新 Bug）
     * @param {HTMLElement} container - 下载进度条容器 (messageDownload)
     * @param {Array[]} newMessages - 最新的下载信息数组
     * @param {Array[]} oldMessages - 上一次的下载信息数组
     */
    function appendBar(container, newMessages, oldMessages) {
        if (!container) return;

        const containerId = container.id;
        const newlength = newMessages.length;

        // 如果没有下载任务，清空区域并显示提示
        if (newlength === 0) {
            if (downloadLabel) downloadLabel.textContent = '暂无下载任务';
            container.innerHTML = '';
            userScrolled[containerId] = false;
            return;
        }

        if (downloadLabel) downloadLabel.textContent = '下载进度：';

        // 如果任务数量减少（如任务完成被移除），清空重绘
        if (container.children.length > newlength) {
            container.innerHTML = '';
        }

        // 遍历所有下载任务，更新已有节点或追加新节点
        for (let i = 0; i < newlength; i++) {
            const messageContent = newMessages[i];
            const [percentageText, time, speed, part, status, idname, nameText, file] = messageContent;
            const barIndex = i + 1;

            // 依据 ID 查找对应的进度条元素
            const progressElement = container.querySelector('#pbProgress' + barIndex);

            if (progressElement) {
                // 1. 已存在 DOM 节点：直接更新文本与进度条宽度
                const parent = progressElement.closest('.download-container');
                if (parent) {
                    const statusElement = parent.querySelector('#pbStatusText' + barIndex);
                    const percentageElement = parent.querySelector('#pbPercentageText' + barIndex);
                    const speedElement = parent.querySelector('#speedText' + barIndex);
                    const partElement = parent.querySelector('#partText' + barIndex);
                    const timeElement = parent.querySelector('#timeText' + barIndex);

                    progressElement.style.width = `${percentageText * 100}%`;
                    if (statusElement) statusElement.innerHTML = status;
                    if (percentageElement) percentageElement.innerHTML = `${(percentageText * 100).toFixed(2)}%`;
                    if (speedElement) speedElement.innerHTML = speed;
                    if (partElement) partElement.innerHTML = part;
                    if (timeElement) timeElement.innerHTML = time;
                }
            } else {
                // 2. 节点不存在：调用 addProgressBar 创建新的 DOM 节点并追加
                const downloadElement = addProgressBar(i, percentageText, time, speed, part, status, idname, nameText, file);
                container.appendChild(downloadElement);
            }
        }

        // 处理自动滚动
        if (newlength > oldlength && !userScrolled[containerId]) { // 如果是新增了进度条且用户没滚动
            container.scrollTop = 0; // 滚动到顶部
        } else if (wasAtBottom && !userScrolled[containerId]) { // 如果是更新现有条目且之前在底部
            container.scrollTop = container.scrollHeight; // 保持在底部
        }
    }


    // --- 短轮询 (Short Polling) 处理 ---
    let pollingTimer = null; // 用于存储 setInterval 句柄
    let isFetching = false;  // 请求锁：防止上一次请求未完成时重复发请求
    let failedCount = 0;     // 连续失败计数器

    /**
     * 处理从服务器获取到的 JSON 消息数据
     * @param {Object} data - 解析后的 JSON 对象
     */
    function handleStreamData(data) {
        // 确保 lastMessage 和 data 结构完整，提供默认值防止报错
        lastMessage = lastMessage || { schedule: [], podflow: [], http: [], download: [] };
        data.schedule = data.schedule || [];
        data.podflow = data.podflow || [];
        data.http = data.http || [];
        data.download = data.download || [];

        // 1. 更新主进度条
        if (JSON.stringify(data.schedule) !== JSON.stringify(lastMessage.schedule)) {
            updateProgress(data.schedule);
            lastMessage.schedule = data.schedule; // 更新缓存
        }

        // 2. 更新 Podflow 消息区域
        if (JSON.stringify(data.podflow) !== JSON.stringify(lastMessage.podflow)) {
            appendMessages(messageArea, data.podflow, lastMessage.podflow || []);
            lastMessage.podflow = [...data.podflow]; // 更新缓存
        }

        // 3. 更新 HTTP 消息区域
        if (JSON.stringify(data.http) !== JSON.stringify(lastMessage.http)) {
            appendMessages(messageHttp, data.http, lastMessage.http || []);
            lastMessage.http = [...data.http]; // 更新缓存
        }

        // 4. 更新下载进度条区域
        if (JSON.stringify(data.download) !== JSON.stringify(lastMessage.download)) {
            appendBar(messageDownload, data.download, lastMessage.download || []);
            lastMessage.download = [...data.download]; // 更新缓存
        }
    }

    /**
     * 向后端请求一次最新的状态数据
     */
    function fetchMessageStream() {
        // 1. 如果上一次请求还在处理中，跳过本次轮询，避免并发堆积
        if (isFetching) return;
        isFetching = true;

        fetch('/stream')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP 错误！状态码: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // 请求成功：只有之前弹出了警告时，才恢复为“已连接”
                if (failedCount >= 3) {
                    reconnectAttempts = 0;
                    updateConnectionStatus('connected');
                }
                failedCount = 0; // 重置连续失败计数
                handleStreamData(data);
            })
            .catch(error => {
                console.warn('获取轮询数据单次失败 (可能偶发延迟):', error);
                failedCount++;

                // 2. 只有【连续失败 3 次】以上才判定为真正的网络中断并弹窗警告
                if (failedCount >= 3) {
                    reconnectAttempts++;
                    if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
                        updateConnectionStatus('reconnecting', `⚠️ 网络请求失败，正在重试 (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
                    } else {
                        updateConnectionStatus('disconnected');
                        stopMessageStream(); // 超过最大失败次数后停止轮询
                    }
                }
            })
            .finally(() => {
                isFetching = false; // 释放锁，允许下一次请求
            });
    }

    /**
     * 启动 0.25 秒（250ms）短轮询
     */
    function startMessageStream() {
        stopMessageStream();
        resetMessageView();

        console.log("启动短轮询，频率: 250ms/次 ...");
        
        failedCount = 0;
        isFetching = false;

        // 立即执行一次
        fetchMessageStream();

        // 每 250ms 检查并发起轮询
        pollingTimer = setInterval(fetchMessageStream, 250);
        updateConnectionStatus('connected');
    }

    /**
     * 停止短轮询
     */
    function stopMessageStream() {
        if (pollingTimer) {
            clearInterval(pollingTimer);
            pollingTimer = null;
            console.log("短轮询已停止。");
        }
        reconnectAttempts = 0;
        failedCount = 0;
        isFetching = false;
        updateConnectionStatus(''); // 隐藏状态指示器
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
    if (menuBackdrop) {
        menuBackdrop.addEventListener('click', () => setMenuVisibility(true));
    }

    // --- 初始化 ---
    // 根据屏幕宽度初始化菜单状态
    if (window.innerWidth <= 600) {
        setMenuVisibility(true);
    } else {
        setMenuVisibility(menu.classList.contains('hidden'));
    }

    // 初始化时显示默认页面 (例如消息页面)
    showPage('pageMessage');
    loadYoutubeCookieSetting();
    loadFavoriteUpdateStatus();
    setInterval(renderFavoriteUpdateCountdown, 1000);
    setInterval(loadFavoriteUpdateStatus, 15000);

    if (alwaysUseYoutubeCookie) {
        alwaysUseYoutubeCookie.addEventListener('change', saveYoutubeCookieSetting);
    }
    if (immediateUpdateBtn) {
        immediateUpdateBtn.addEventListener('click', requestImmediateUpdate);
    }
    if (toggleConfigDisplay && configContent) {
        toggleConfigDisplay.addEventListener('click', () => {
            const isCollapsed = configContent.classList.toggle('hidden');
            toggleConfigDisplay.setAttribute('aria-expanded', String(!isCollapsed));
        });
    }

    // --- 页面可见性检测：标签页切回前台后自动恢复轮询 ---
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            // 当且仅当处于消息页面且定时器未启动时恢复
            if (!pollingTimer && pages.pageMessage && pages.pageMessage.style.display !== 'none') {
                console.log("页面重新可见，重新恢复 0.25 秒短轮询...");
                reconnectAttempts = 0;
                startMessageStream();
            }
        } else {
            // 页面切到后台/隐藏时停止轮询，节省服务器与网络资源
            stopMessageStream();
        }
    });

})(); // IIFE 结束
