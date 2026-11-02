(function () {
  // --- 缓存常用 DOM 节点 ---
  // 菜单相关
  const menu = document.getElementById("menu");
  const toggleMenuBtn = document.getElementById("toggleMenu");
  const menuBackdrop = document.getElementById("menuBackdrop");
  // 页面容器
  const pages = {
    pageChannel: document.getElementById("pageChannel"),
    pageMessage: document.getElementById("pageMessage"),
    pageConfig: document.getElementById("pageConfig"),
    pageCustomMedia: document.getElementById("pageCustomMedia"),
    pageYoutubeCookie: document.getElementById("pageYoutubeCookie"),
    pageDebugVariable: document.getElementById("pageDebugVariable"),
  };
  // 隐藏测试页面(变量查询)相关
  const versionInfo = document.getElementById("version-info");
  const debugVariableInput = document.getElementById("debugVariableInput");
  const debugVariableBtn = document.getElementById("debugVariableBtn");
  const debugVariableOutput = document.getElementById("debugVariableOutput");
  const debugVariableHistory = document.getElementById("debugVariableHistory");
  const debugInputCopyBtn = document.getElementById("debugInputCopyBtn");
  const debugInputClearBtn = document.getElementById("debugInputClearBtn");
  const debugOutputCopyBtn = document.getElementById("debugOutputCopyBtn");
  // Channel ID 相关表单
  const inputForm = document.getElementById("inputForm");
  const inputOutput = document.getElementById("inputOutput");
  const pasteBtn = document.getElementById("pasteBtn");
  const copyBtn = document.getElementById("copyBtn");
  const clearBtn = document.getElementById("clearBtn");
  // 提交成功后用于跳转「修改运行配置」对应频道并自动新建频道
  const addChannelBtn = document.getElementById("addChannelBtn");
  // 主进度条相关
  const mainProgress = document.getElementById("mainProgress");
  const progressStatus = document.getElementById("progressStatus");
  const progressPercentage = document.getElementById("progressPercentage");
  // 消息显示区域
  const messageArea = document.getElementById("messageArea"); // Podflow 消息
  const messageHttp = document.getElementById("messageHttp"); // HTTP 消息
  const messageDownload = document.getElementById("messageDownload"); // 下载进度条容器
  const downloadLabel = document.getElementById("downloadLabel"); // 下载进度标题 (假设存在)
  const alwaysUseYoutubeCookie = document.getElementById(
    "alwaysUseYoutubeCookie",
  );
  const youtubeCookieStatus = document.getElementById("youtubeCookieStatus");
  const immediateUpdateBtn = document.getElementById("immediateUpdateBtn");
  const favoriteUpdateCountdown = document.getElementById(
    "favoriteUpdateCountdown",
  );

  // --- 状态变量 ---
  let lastMessage = { schedule: [], podflow: [], http: [], download: [] }; // 缓存上一次的消息数据
  let userScrolled = {
    // 分别跟踪每个滚动区域的用户滚动状态
    messageArea: false,
    messageHttp: false,
    messageDownload: false,
  };
  let eventSource = null; // 用于存储 EventSource 实例
  let reconnectAttempts = 0; // 重连尝试次数
  let reconnectTimer = null; // 重连定时器
  const MAX_RECONNECT_ATTEMPTS = 10; // 最大重连次数
  const BASE_RECONNECT_DELAY = 1000; // 基础重连延迟 (ms)
  let favoriteUpdateNextRun = null;
  let serverOffset = 0; // 记录服务器时间与本地时间的毫秒偏差
  let showExpectedRunTime = false; // 倒计时区域是否显示预计运行时间
  let expectedRunTimeTimer = null; // 预计运行时间自动切回倒计时的定时器
  const EXPECTED_RUN_TIME_DURATION = 10000; // 预计运行时间显示时长（10秒）
  let playlistOpen = false;
  let playlistCache = null;
  let playlistLoading = false;

  function renderFavoriteUpdateCountdown() {
    if (!favoriteUpdateCountdown) return;
    if (!favoriteUpdateNextRun) {
      favoriteUpdateCountdown.textContent = "倒计运行时间：更新运行中";
      return;
    }

    if (showExpectedRunTime) {
      // 显示预计运行时间（使用服务器时间校准后的本地时间，24小时制）
      const runMs = favoriteUpdateNextRun * 1000 + serverOffset;
      const runDate = new Date(runMs);
      const hours = String(runDate.getHours()).padStart(2, "0");
      const minutes = String(runDate.getMinutes()).padStart(2, "0");
      const seconds = String(runDate.getSeconds()).padStart(2, "0");
      favoriteUpdateCountdown.textContent = `预计运行时间：${hours}:${minutes}:${seconds}`;
      return;
    }

    // 使用 Date.now() + serverOffset 校准当前服务器毫秒时间
    const adjustedNowMs = Date.now() + serverOffset;

    // 计算剩余秒数 (favoriteUpdateNextRun 为秒级时间戳)
    const remaining = Math.max(
      0,
      Math.ceil(favoriteUpdateNextRun - adjustedNowMs / 1000),
    );

    const hours = String(Math.floor(remaining / 3600)).padStart(2, "0");
    const minutes = String(Math.floor((remaining % 3600) / 60)).padStart(
      2,
      "0",
    );
    const seconds = String(Math.floor(remaining % 60)).padStart(2, "0");
    favoriteUpdateCountdown.textContent = `倒计运行时间：${hours}:${minutes}:${seconds}`;
  }

  function resetExpectedRunTimeTimer() {
    if (expectedRunTimeTimer) {
      clearTimeout(expectedRunTimeTimer);
      expectedRunTimeTimer = null;
    }
  }

  function toggleExpectedRunTime() {
    showExpectedRunTime = !showExpectedRunTime;
    renderFavoriteUpdateCountdown();

    resetExpectedRunTimeTimer();
    if (showExpectedRunTime) {
      // 10秒后自动切回倒计时显示
      expectedRunTimeTimer = setTimeout(() => {
        showExpectedRunTime = false;
        renderFavoriteUpdateCountdown();
      }, EXPECTED_RUN_TIME_DURATION);
    }
  }

  // 辅助函数：同步一次服务器时间偏差
  async function syncServerOffset() {
    try {
      const startTime = Date.now();
      const res = await fetch("/timestamp");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { timestamp: serverTimeSec } = await res.json();

      // 考虑单程网络延迟估计 (RTT / 2)
      const networkLatency = (Date.now() - startTime) / 2;
      const serverTimeMs = serverTimeSec * 1000 + networkLatency;

      // 计算偏差：服务端毫秒数 - 客户端毫秒数
      serverOffset = serverTimeMs - Date.now();
    } catch (error) {
      console.error("同步服务器时间偏差失败:", error);
    }
  }

  async function loadFavoriteUpdateStatus() {
    try {
      // 并行请求状态与服务器时间戳，减少等待时长
      const [statusRes] = await Promise.all([
        fetch("/favorite-update-status"),
        syncServerOffset(),
      ]);

      if (!statusRes.ok) throw new Error(`HTTP ${statusRes.status}`);
      const data = await statusRes.json();

      favoriteUpdateNextRun = data.next_run;
      if (immediateUpdateBtn) immediateUpdateBtn.disabled = !data.active;
      renderFavoriteUpdateCountdown();
    } catch (error) {
      console.error("加载特别关注状态失败:", error);
      favoriteUpdateNextRun = null;
      if (immediateUpdateBtn) immediateUpdateBtn.disabled = true;
      if (favoriteUpdateCountdown)
        favoriteUpdateCountdown.textContent = "倒计运行时间：状态不可用";
    }
  }

  async function requestImmediateUpdate() {
    if (!immediateUpdateBtn) return;
    immediateUpdateBtn.disabled = true;
    try {
      const response = await fetch("/favorite-update-status", {
        method: "POST",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      favoriteUpdateNextRun = null;
      renderFavoriteUpdateCountdown();
    } catch (error) {
      console.error("立即更新请求失败:", error);
      await loadFavoriteUpdateStatus();
    }
  }

  async function loadYoutubeCookieSetting() {
    if (!alwaysUseYoutubeCookie) return;
    try {
      const response = await fetch("/youtube-cookie-setting");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      alwaysUseYoutubeCookie.checked = data.enabled;
      alwaysUseYoutubeCookie.disabled = !data.cookie_available;
      if (youtubeCookieStatus) {
        youtubeCookieStatus.textContent = data.cookie_available
          ? "（Cookie 可用）"
          : "（Cookie 不可用，开关已禁用）";
      }
    } catch (error) {
      console.error("加载 YouTube Cookie 设置失败:", error);
      alwaysUseYoutubeCookie.disabled = true;
      if (youtubeCookieStatus)
        youtubeCookieStatus.textContent = "（设置加载失败）";
    }
  }

  async function saveYoutubeCookieSetting() {
    try {
      const response = await fetch("/youtube-cookie-setting", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: alwaysUseYoutubeCookie.checked }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    } catch (error) {
      console.error("保存 YouTube Cookie 设置失败:", error);
      alwaysUseYoutubeCookie.checked = !alwaysUseYoutubeCookie.checked;
      if (youtubeCookieStatus) youtubeCookieStatus.textContent = "（保存失败）";
    }
  }

  // --- 连接状态指示器 ---
  function updateConnectionStatus(status, message) {
    let indicator = document.getElementById("connection-status");
    if (!indicator) {
      indicator = document.createElement("div");
      indicator.id = "connection-status";
      indicator.style.cssText =
        "position:fixed;top:0;left:0;right:0;z-index:9999;padding:6px 12px;text-align:center;font-size:13px;transition:opacity 0.3s;pointer-events:none;";
      document.body.appendChild(indicator);
    }
    if (status === "connected") {
      indicator.style.backgroundColor = "#4caf50";
      indicator.style.color = "#fff";
      indicator.textContent = message || "✅ 已连接";
      // 2秒后自动隐藏
      setTimeout(() => {
        indicator.style.opacity = "0";
      }, 2000);
    } else if (status === "reconnecting") {
      indicator.style.backgroundColor = "#ff9800";
      indicator.style.color = "#fff";
      indicator.style.opacity = "1";
      indicator.textContent =
        message ||
        `⚠️ 连接中断，正在重连 (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`;
    } else if (status === "disconnected") {
      indicator.style.backgroundColor = "#f44336";
      indicator.style.color = "#fff";
      indicator.style.opacity = "1";
      indicator.innerHTML =
        message ||
        '❌ 连接已断开 <button onclick="location.reload()" style="margin-left:8px;padding:2px 8px;border:none;border-radius:3px;cursor:pointer;">刷新页面</button>';
    } else {
      indicator.style.opacity = "0";
    }
  }

  // --- 二维码生成 ---
  /**
   * 为指定的 DOM 容器生成二维码
   * @param {HTMLElement} container - 要生成二维码的容器元素，需要有 data-url 属性
   */
  function generateQRCodeForNode(container) {
    const rootStyles = getComputedStyle(document.documentElement);
    const textColor = rootStyles.getPropertyValue("--text-color").trim();
    const inputBg = rootStyles.getPropertyValue("--input-bg").trim();
    const url = container.dataset.url;
    container.innerHTML = ""; // 清空容器
    if (url) {
      try {
        new QRCode(container, {
          text: url,
          width: 220,
          height: 220,
          colorDark: textColor,
          colorLight: inputBg,
          correctLevel: QRCode.CorrectLevel.L,
        });
      } catch (e) {
        console.error("生成二维码失败:", e);
        container.textContent = "二维码生成失败";
      }
    } else {
      container.textContent = "URL 未提供";
    }
  }

  // --- 菜单控制 ---
  /**
   * 切换侧边菜单的显示/隐藏状态
   */
  function setMenuVisibility(isHidden) {
    menu.classList.toggle("hidden", isHidden);
    if (menuBackdrop)
      menuBackdrop.classList.toggle(
        "visible",
        !isHidden && window.innerWidth <= 600,
      );
    if (!toggleMenuBtn) return;
    toggleMenuBtn.setAttribute("aria-expanded", String(!isHidden));
    toggleMenuBtn.setAttribute(
      "aria-label",
      isHidden ? "显示侧边栏" : "隐藏侧边栏",
    );
  }

  function toggleMenu() {
    setMenuVisibility(!menu.classList.contains("hidden"));
  }

  /**
   * 根据页面 ID 显示对应的页面内容，并管理 SSE 连接
   * @param {string} pageId - 'pageChannel' 或 'pageMessage'
   */
  function showPage(pageId) {
    // 隐藏所有页面
    Object.values(pages).forEach((page) => (page.style.display = "none"));

    // 显示目标页面
    if (pages[pageId]) {
      pages[pageId].style.display = "block";
      menu.querySelectorAll("li[data-page]").forEach((item) => {
        item.classList.toggle("active", item.dataset.page === pageId);
      });

      // 手机模式下，切换页面时自动隐藏菜单
      if (window.innerWidth <= 600 && !menu.classList.contains("hidden")) {
        toggleMenu();
      }

      // --- SSE 连接管理 ---
      if (pageId === "pageMessage") {
        startMessageStream(); // 显示消息页面时，启动 SSE 连接
      } else {
        stopMessageStream(); // 切换到其他页面时，关闭 SSE 连接
      }

      // --- 配置页面加载 ---
      if (pageId === "pageConfig" && window.podflowConfig) {
        window.podflowConfig.onShow();
      }

      // --- YouTube Cookie 文件页面加载 ---
      if (pageId === "pageYoutubeCookie" && window.podflowYoutubeCookie) {
        window.podflowYoutubeCookie.onShow();
      }

      // --- 自定义媒体页面加载 ---
      if (pageId === "pageCustomMedia" && window.podflowCustomMedia) {
        window.podflowCustomMedia.onShow();
      }
    } else {
      console.warn(`未找到 ID 为 "${pageId}" 的页面`);
    }
  }

  // ============================================================
  // 播客列表
  // ============================================================

  // 抽屉打开时隐藏整个右上角控件容器：若只隐藏按钮，看不见的 fixed 空容器
  // 仍会拦截同位置的抽屉关闭按钮的点击。
  function setPlaylistToggleHidden(hidden) {
    if (!playlistToggleBtn) return;
    const target =
      playlistToggleBtn.closest(".top-right-controls") || playlistToggleBtn;
    target.classList.toggle("drawer-hidden", hidden);
  }

  function openPlaylistDrawer() {
    if (!playlistDrawer || !playlistOverlay) return;

    playlistOpen = true;

    playlistDrawer.classList.add("active");
    playlistOverlay.classList.add("active");
    playlistDrawer.setAttribute("aria-hidden", "false");
    setPlaylistToggleHidden(true);

    loadPlaylist();
  }

  function closePlaylistDrawer() {
    if (!playlistDrawer || !playlistOverlay) return;

    playlistOpen = false;

    playlistDrawer.classList.remove("active");
    playlistOverlay.classList.remove("active");
    playlistDrawer.setAttribute("aria-hidden", "true");
    setPlaylistToggleHidden(false);
  }

  async function loadPlaylist() {
    if (!playlistBody || playlistLoading) return;

    playlistLoading = true;

    playlistBody.innerHTML = "";

    const status = document.createElement("div");
    status.className = "playlist-status";
    status.textContent = "正在加载列表…";
    playlistBody.appendChild(status);

    try {
      const response = await fetch("/playlist", {
        cache: "no-cache",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const dict = await response.json();

      if (!dict || typeof dict !== "object" || Array.isArray(dict)) {
        throw new Error("返回的不是有效的播放列表");
      }

      playlistCache = dict;
      renderPlaylist(dict);
    } catch (error) {
      console.warn("加载播客列表失败：", error);

      playlistBody.innerHTML = "";

      const status = document.createElement("div");
      status.className = "playlist-status";
      status.textContent = "列表刷新失败：" + error.message;
      playlistBody.appendChild(status);

      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "btn playlist-retry-btn";
      retry.textContent = "重试";

      retry.addEventListener("click", loadPlaylist);

      playlistBody.appendChild(retry);

      // 如果之前加载成功过，则继续显示旧列表
      if (playlistCache) {
        renderPlaylistItems(playlistCache);
      }
    } finally {
      playlistLoading = false;
    }
  }

  function renderPlaylist(dict) {
    if (!playlistBody) return;

    playlistBody.innerHTML = "";

    const names = Object.keys(dict);

    if (names.length === 0) {
      const empty = document.createElement("div");
      empty.className = "playlist-status";
      empty.textContent = "列表是空的。";
      playlistBody.appendChild(empty);
      return;
    }

    renderPlaylistItems(dict);
  }

  function renderPlaylistItems(dict) {
    const container = document.createElement("div");

    Object.keys(dict).forEach((name) => {
      const url = dict[name];

      const button = document.createElement("button");

      button.type = "button";
      button.className = "playlist-item";
      button.textContent = name;

      button.addEventListener("click", () => {
        switchPodcast(url);
      });

      container.appendChild(button);
    });

    playlistBody.appendChild(container);
  }

  function switchPodcast(url) {
    if (!url || typeof url !== "string") return;

    // 关键：
    // 主页 /index 点击播客后必须进入 /podcast
    window.location.href = `/podcast?url=${encodeURIComponent(url)}`;
  }

  // --- 滚动处理 ---
  /**
   * 监听滚动事件，判断用户是否手动滚动了消息区域
   * @param {Event} event - 滚动事件对象
   */
  function onUserScroll(event) {
    const element = event.target;
    const containerId = element.id; // 获取滚动容器的ID
    if (userScrolled.hasOwnProperty(containerId)) {
      // 确保是我们关心的容器
      // 判断是否滚动到接近底部 (增加 10px 容差)
      const isNearBottom =
        element.scrollHeight - element.scrollTop <= element.clientHeight + 10;
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
        mainProgress.style.width = "100%";
        progressStatus.textContent = "已完成";
        progressPercentage.textContent = "100.00%"; // 保持格式一致
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
      messageDownload: false,
    };

    if (mainProgress) mainProgress.style.width = "0%";
    if (progressStatus) progressStatus.textContent = "准备中";
    if (progressPercentage) progressPercentage.textContent = "0.00%";
    if (messageArea) {
      messageArea.innerHTML = "";
      messageArea.scrollTop = 0;
    }
    if (messageHttp) {
      messageHttp.innerHTML = "";
      messageHttp.scrollTop = 0;
    }
    if (messageDownload) {
      messageDownload.innerHTML = "";
      messageDownload.scrollTop = 0;
    }
    if (downloadLabel) downloadLabel.textContent = "";
  }

  /**
   * 创建单个消息元素的 DOM 结构
   * @param {string} message - 包含 HTML 的消息字符串
   * @returns {HTMLDivElement} - 创建的消息元素
   */
  function createMessageElement(message) {
    const div = document.createElement("div");
    // 使用 innerHTML，因为消息内容可能包含 HTML 标签 (如二维码容器)
    div.innerHTML = message;
    div.className = "message"; // 假设 'message' 是单个消息的样式类
    return div;
  }

  /**
   * 处理消息元素内部的二维码容器
   * @param {HTMLElement} element - 包含 .qrcode-container 的父元素
   */
  function processQRCodeContainers(element) {
    const qrContainers = element.querySelectorAll(".qrcode-container");
    qrContainers.forEach((container) => {
      if (container.dataset.url) {
        generateQRCodeForNode(container);
      } else {
        console.log("容器中未提供 URL，跳过二维码生成:", container);
        container.textContent = "未提供二维码 URL";
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
    const wasAtBottom =
      !userScrolled[containerId] &&
      container.scrollHeight - container.scrollTop <=
        container.clientHeight + 10;
    const newLength = newMessages.length;
    const oldLength = oldMessages.length;

    // --- 主要逻辑：比较新旧消息，更新 DOM ---
    if (newLength === oldLength && newLength > 0) {
      // --- 长度相同：检查最后几条消息是否有变化 ---
      let replaceCount = 1; // 默认只检查最后一条
      const lastMessageContent = newMessages[newLength - 1];
      // 特殊逻辑：如果最后一条消息包含特定文本，则检查最后四条
      if (
        lastMessageContent.includes("未扫描") ||
        lastMessageContent.includes("二维码超时, 请重试")
      ) {
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
      container.innerHTML = ""; // 清空
      const fragment = document.createDocumentFragment();
      newMessages.forEach((msg) => {
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
  function addProgressBar(
    i,
    percentageText,
    time,
    speed,
    part,
    status,
    idname,
    nameText,
    file,
  ) {
    const download = document.createElement("div");
    download.className = "download-container";
    // 创建 idname 文本节点（只创建一次）
    const idnameText = document.createElement("div");
    idnameText.className = "scroll-text"; // 可能也需要滚动？根据 CSS 定义
    idnameText.innerHTML = "  " + idname; // 前导空格？
    // 创建文件信息部分
    const fileInfo = document.createElement("div");
    fileInfo.className = "scroll"; // 类名可能与滚动有关
    const filesuffix = document.createElement("div");
    filesuffix.className = "scroll-suffix";
    filesuffix.innerHTML = file;
    // 创建滚动文本区域
    const scroll = document.createElement("div");
    scroll.className = "scroll-container";
    const namebar = document.createElement("div");
    namebar.className = "scroll-content";
    const filename = document.createElement("div");
    filename.className = "scroll-text";
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
      const contentWidth = filename.scrollWidth; // 单份文本宽度
      const containerWidth = scroll.clientWidth;
      if (contentWidth > containerWidth) {
        // 需要滚动，添加第二份文本实现无缝滚动
        const filename1 = document.createElement("div");
        filename1.className = "scroll-text";
        filename1.innerHTML = nameText;
        namebar.appendChild(filename1);
        // 重新计算宽度，这次是双倍宽度中的单份宽度用于计算时间
        const singleContentWidth = namebar.scrollWidth / 2;
        const scrollSpeed = 30; // 滚动速度 (像素/秒)
        const duration = singleContentWidth / scrollSpeed;
        namebar.style.animationDuration = duration + "s";
        // 延迟添加滚动类
        setTimeout(() => {
          namebar.classList.add("scrolling");
        }, 1500); // 1.5秒延迟
      } else {
        // 不需要滚动，确保移除动画类和样式
        namebar.classList.remove("scrolling");
        namebar.style.animationDuration = "";
      }
    }, 0); // 使用 setTimeout 0ms 延迟，等待浏览器渲染后测量
    // 进度条部分
    const pbBar = document.createElement("div");
    pbBar.className = "pb-bar";
    const pbProgress = document.createElement("div");
    pbProgress.className = "pb-progress pb-animated"; // 假设有动画效果
    pbProgress.style.width = `${percentageText * 100}%`;
    pbProgress.id = "pbProgress" + (i + 1); // ID 基于索引
    const pbStatusText = document.createElement("div");
    pbStatusText.className = "pb-status-text";
    pbStatusText.innerHTML = status;
    pbStatusText.id = "pbStatusText" + (i + 1);
    const pbPercentageText = document.createElement("div");
    pbPercentageText.className = "pb-percentage-text";
    pbPercentageText.innerHTML = `${(percentageText * 100).toFixed(2)}%`;
    pbPercentageText.id = "pbPercentageText" + (i + 1);
    pbBar.appendChild(pbProgress);
    pbBar.appendChild(pbStatusText);
    pbBar.appendChild(pbPercentageText);
    download.appendChild(pbBar);
    // 速度、分片、时间部分
    const speedContainer = document.createElement("div"); // 使用 div 而非 table 可能更灵活
    speedContainer.className = "scroll";
    const speedText = document.createElement("div");
    speedText.className = "speed-text";
    speedText.innerHTML = speed;
    speedText.id = "speedText" + (i + 1);
    const partText = document.createElement("div");
    partText.className = "speed-text";
    partText.innerHTML = part;
    partText.id = "partText" + (i + 1);
    const timeText = document.createElement("div");
    timeText.className = "time-text";
    timeText.innerHTML = time;
    timeText.id = "timeText" + (i + 1);
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
    // 在改动DOM前记录是否处于底部, 供末尾的自动滚动使用
    const wasAtBottom =
      !userScrolled[containerId] &&
      container.scrollHeight - container.scrollTop <=
        container.clientHeight + 10;
    const newlength = newMessages.length;
    const oldlength = oldMessages.length;

    // 如果没有下载任务，清空区域并显示提示
    if (newlength === 0) {
      if (downloadLabel) downloadLabel.textContent = "暂无下载任务";
      container.innerHTML = "";
      userScrolled[containerId] = false;
      return;
    }

    if (downloadLabel) downloadLabel.textContent = "下载进度：";

    // 如果任务数量减少（如任务完成被移除），清空重绘
    if (container.children.length > newlength) {
      container.innerHTML = "";
    }

    // 遍历所有下载任务，更新已有节点或追加新节点
    for (let i = 0; i < newlength; i++) {
      const messageContent = newMessages[i];
      const [
        percentageText,
        time,
        speed,
        part,
        status,
        idname,
        nameText,
        file,
      ] = messageContent;
      const barIndex = i + 1;

      // 依据 ID 查找对应的进度条元素
      const progressElement = container.querySelector("#pbProgress" + barIndex);

      if (progressElement) {
        // 1. 已存在 DOM 节点：直接更新文本与进度条宽度
        const parent = progressElement.closest(".download-container");
        if (parent) {
          const statusElement = parent.querySelector(
            "#pbStatusText" + barIndex,
          );
          const percentageElement = parent.querySelector(
            "#pbPercentageText" + barIndex,
          );
          const speedElement = parent.querySelector("#speedText" + barIndex);
          const partElement = parent.querySelector("#partText" + barIndex);
          const timeElement = parent.querySelector("#timeText" + barIndex);

          progressElement.style.width = `${percentageText * 100}%`;
          if (statusElement) statusElement.innerHTML = status;
          if (percentageElement)
            percentageElement.innerHTML = `${(percentageText * 100).toFixed(2)}%`;
          if (speedElement) speedElement.innerHTML = speed;
          if (partElement) partElement.innerHTML = part;
          if (timeElement) timeElement.innerHTML = time;
        }
      } else {
        // 2. 节点不存在：调用 addProgressBar 创建新的 DOM 节点并追加
        const downloadElement = addProgressBar(
          i,
          percentageText,
          time,
          speed,
          part,
          status,
          idname,
          nameText,
          file,
        );
        container.appendChild(downloadElement);
      }
    }

    // 处理自动滚动
    if (newlength > oldlength && !userScrolled[containerId]) {
      // 如果是新增了进度条且用户没滚动
      container.scrollTop = 0; // 滚动到顶部
    } else if (wasAtBottom && !userScrolled[containerId]) {
      // 如果是更新现有条目且之前在底部
      container.scrollTop = container.scrollHeight; // 保持在底部
    }
  }

  // --- 短轮询 (Short Polling) 处理 ---
  let pollingTimer = null; // 用于存储 setInterval 句柄
  let isFetching = false; // 请求锁：防止上一次请求未完成时重复发请求
  let failedCount = 0; // 连续失败计数器

  /**
   * 处理从服务器获取到的 JSON 消息数据
   * @param {Object} data - 解析后的 JSON 对象
   */
  function handleStreamData(data) {
    // 确保 lastMessage 和 data 结构完整，提供默认值防止报错
    lastMessage = lastMessage || {
      schedule: [],
      podflow: [],
      http: [],
      download: [],
    };
    data.schedule = data.schedule || [];
    data.podflow = data.podflow || [];
    data.http = data.http || [];
    data.download = data.download || [];

    // 1. 更新主进度条
    if (
      JSON.stringify(data.schedule) !== JSON.stringify(lastMessage.schedule)
    ) {
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
    if (
      JSON.stringify(data.download) !== JSON.stringify(lastMessage.download)
    ) {
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

    fetch("/stream")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP 错误！状态码: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        // 请求成功：只有之前弹出了警告时，才恢复为“已连接”
        if (failedCount >= 3) {
          reconnectAttempts = 0;
          updateConnectionStatus("connected");
        }
        failedCount = 0; // 重置连续失败计数
        handleStreamData(data);
      })
      .catch((error) => {
        console.warn("获取轮询数据单次失败 (可能偶发延迟):", error);
        failedCount++;

        // 2. 只有【连续失败 3 次】以上才判定为真正的网络中断并弹窗警告
        if (failedCount >= 3) {
          reconnectAttempts++;
          if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
            updateConnectionStatus(
              "reconnecting",
              `⚠️ 网络请求失败，正在重试 (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`,
            );
          } else {
            updateConnectionStatus("disconnected");
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
    updateConnectionStatus("connected");
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
    updateConnectionStatus(""); // 隐藏状态指示器
  }

  // --- 事件监听器绑定 ---
  // 滚动事件 (确保所有相关容器都监听)
  if (messageArea) messageArea.addEventListener("scroll", onUserScroll);
  if (messageHttp) messageHttp.addEventListener("scroll", onUserScroll);
  if (messageDownload) messageDownload.addEventListener("scroll", onUserScroll); // 添加 messageDownload 的监听

  // --- Channel ID 结果 → 跳转「修改运行配置」对应频道并自动新建频道 ---
  // 仅当最近一次「提交」成功解析出频道信息时，对应按钮才可点击
  let channelIdResult = null;

  // 解析 getid 返回：首行为网站名（youtube / bilibili），随后为 "频道名": "频道ID"
  // 失败（如 "Network Error"）或格式不符时返回 null
  function parseChannelIdResponse(text) {
    if (typeof text !== "string") return null;
    const lines = text
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    if (lines.length < 2) return null;
    const website = lines[0].toLowerCase();
    if (website !== "youtube" && website !== "bilibili") return null;
    const match = lines
      .slice(1)
      .join("\n")
      .match(/"([\s\S]*?)"\s*:\s*"([\s\S]*?)"/);
    if (!match) return null;
    const name = match[1].trim();
    const id = match[2].trim();
    if (!name || !id) return null;
    return { website, name, id };
  }

  // 更新按钮可用状态：仅当解析出有效结果时才可点击，并按网站自动切换按钮文案
  function setChannelIdResult(result) {
    channelIdResult = result;
    if (!addChannelBtn) return;
    addChannelBtn.disabled = !result;
    if (!result) {
      addChannelBtn.textContent = "➕ 添加到频道";
    } else {
      const label = result.website === "youtube" ? "YouTube" : "Bilibili";
      addChannelBtn.textContent = `➕ 添加到 ${label} 频道`;
    }
  }

  // 点击按钮：按解析结果自动判断网站，跳转到「修改运行配置」对应频道页并自动新建频道
  if (addChannelBtn) {
    addChannelBtn.addEventListener("click", async function () {
      if (addChannelBtn.disabled) return;
      const result = channelIdResult;
      if (!result) return; // 未提交成功则不可用
      const configPage = window.podflowConfig;
      if (
        !configPage ||
        typeof configPage.addChannelFromResult !== "function"
      ) {
        alert("配置页面尚未就绪，无法自动新建频道");
        return;
      }
      addChannelBtn.disabled = true;
      try {
        const res = await configPage.addChannelFromResult(
          result.website,
          result.name,
          result.id,
        );
        showPage("pageConfig"); // 跳转到「修改运行配置」对应频道页
        if (!res || !res.ok) {
          alert(`自动新建频道失败：${(res && res.message) || "未知错误"}`);
        }
      } catch (error) {
        console.error("自动新建频道失败:", error);
        alert(`自动新建频道失败：${error.message || error}`);
      } finally {
        setChannelIdResult(channelIdResult); // 恢复按钮可用状态
      }
    });
  }

  // Channel ID 表单异步提交
  if (inputForm) {
    inputForm.addEventListener("submit", function (event) {
      event.preventDefault(); // 阻止表单默认提交行为
      const content = inputOutput.value.trim(); // 获取并去除首尾空格
      if (!content) {
        alert("请输入内容！");
        return;
      }
      // 重新提交：先禁用「添加到频道」按钮，直到本次提交成功
      setChannelIdResult(null);
      // 可以添加一个加载状态提示
      console.log("正在提交内容获取 Channel ID...");
      fetch("getid", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json", // 明确希望接收 JSON
        },
        body: JSON.stringify({ content: content }), // 发送 JSON 数据
      })
        .then((response) => {
          if (!response.ok) {
            // 如果服务器返回错误状态码，尝试读取错误信息
            return response
              .json()
              .catch(() => {
                // 如果无法解析 JSON 错误体，抛出通用错误
                throw new Error(
                  `网络响应错误: ${response.status} ${response.statusText}`,
                );
              })
              .then((errorData) => {
                // 如果解析成功，抛出包含服务器信息的错误
                throw new Error(
                  errorData.error || `请求失败: ${response.status}`,
                );
              });
          }
          return response.json(); // 解析成功的 JSON 响应
        })
        .then((data) => {
          if (data && data.response) {
            inputOutput.value = data.response; // 更新输入框内容
            // 仅当解析出有效频道信息（非 Network Error 等）时才允许点击添加按钮
            const parsed = parseChannelIdResponse(data.response);
            setChannelIdResult(parsed);
            if (parsed) {
              console.log("成功获取 Channel ID:", parsed);
            } else {
              alert(
                "未能获取到有效的频道 ID（可能链接无效或网络错误），无法添加到频道！",
              );
            }
          } else {
            setChannelIdResult(null);
            console.warn("服务器响应格式不正确:", data);
            alert("服务器返回数据格式错误！");
          }
        })
        .catch((error) => {
          setChannelIdResult(null);
          console.error("获取 Channel ID 请求失败:", error);
          alert(`请求失败：${error.message || "请检查网络或联系管理员"}`);
        });
    });
  }

  // --- 播客列表 ---
  if (playlistToggleBtn) {
    playlistToggleBtn.addEventListener("click", openPlaylistDrawer);
  }

  if (playlistCloseBtn) {
    playlistCloseBtn.addEventListener("click", closePlaylistDrawer);
  }

  if (playlistOverlay) {
    playlistOverlay.addEventListener("click", closePlaylistDrawer);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && playlistOpen) {
      closePlaylistDrawer();
    }
  });

  // 手动编辑输入框后，之前提交成功的结果失效，需重新提交
  if (inputOutput) {
    inputOutput.addEventListener("input", function () {
      setChannelIdResult(null);
    });
  }

  // 粘贴按钮
  if (pasteBtn) {
    pasteBtn.addEventListener("click", function () {
      if (navigator.clipboard && navigator.clipboard.readText) {
        navigator.clipboard
          .readText()
          .then((text) => {
            inputOutput.value = text;
            setChannelIdResult(null); // 内容已变，旧结果失效
            inputOutput.focus(); // 粘贴后聚焦
          })
          .catch((err) => {
            console.warn("通过 navigator.clipboard 读取剪贴板失败:", err);
            alert("无法自动读取剪贴板，请手动粘贴 (Ctrl+V)！");
            inputOutput.focus(); // 提示后聚焦，方便手动粘贴
          });
      } else {
        // 备选方案 (可能在非 HTTPS 或旧浏览器中需要)
        try {
          inputOutput.focus();
          // execCommand 已不推荐使用，但作为后备
          if (!document.execCommand("paste")) {
            throw new Error("execCommand paste failed");
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
    copyBtn.addEventListener("click", function () {
      const textToCopy = inputOutput.value;
      if (!textToCopy) return; // 没有内容则不复制

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard
          .writeText(textToCopy)
          .then(() => {
            // 可以给用户一个成功的视觉反馈，例如按钮变色或提示
            console.log("内容已复制到剪贴板");
            // alert("已复制！"); // 或者使用更友好的提示方式
          })
          .catch((err) => {
            console.warn("通过 navigator.clipboard 写入剪贴板失败:", err);
            alert("自动复制失败，请手动选择文本后按 Ctrl+C 复制！");
            inputOutput.select(); // 选中内容方便手动复制
          });
      } else {
        // 备选方案
        try {
          inputOutput.select(); // 选中输入框中的文本
          if (!document.execCommand("copy")) {
            // 执行复制命令
            throw new Error("execCommand copy failed");
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
    clearBtn.addEventListener("click", function () {
      inputOutput.value = "";
      setChannelIdResult(null); // 内容已清空，旧结果失效
      inputOutput.focus(); // 清空后聚焦
    });
  }

  // 菜单项点击事件 (使用事件委托)
  if (menu) {
    menu.addEventListener("click", function (event) {
      // 确保点击的是 LI 元素且具有 data-page 属性
      const target = event.target.closest("li[data-page]");
      if (target) {
        const pageId = target.dataset.page;
        showPage(pageId); // 调用页面切换函数
      }
    });
  }

  // --- 隐藏测试页面：连续点击三次版本号打开 (需命令行 --debug-variable 启用) ---
  const VERSION_CLICK_WINDOW = 600; // 两次点击之间的最大间隔 (ms)
  let versionClickCount = 0;
  let versionClickTimer = null;

  // 判断一段文本更适合哪种语法高亮（python / json / plain）
  function detectCodeLanguage(text) {
    const trimmed = (text || "").trim();
    if (!trimmed) return "plain";
    if (
      (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
      (trimmed.startsWith("[") && trimmed.endsWith("]"))
    ) {
      return "json";
    }
    return "python";
  }

  // 使用 Prism 对代码进行高亮，返回 HTML 字符串
  function highlightCode(text, lang) {
    if (!window.Prism)
      return (text || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    const grammar = Prism.languages[lang] || Prism.languages.python;
    const language = Prism.languages[lang] ? lang : "python";
    try {
      return Prism.highlight(text || "", grammar, language);
    } catch (e) {
      return (text || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }
  }

  // 缩进层级配色(indent-rainbow): 给每行行首空白按缩进深度着色
  function applyIndentColors(html) {
    const INDENT_UNIT = 4; // 一个缩进层级 = 4 个空格(制表符按 4 计算)
    const LEVEL_COUNT = 8;
    return (html || "").replace(
      /(^|\n)([ \t]+)/g,
      function (match, lineBreak, whitespace) {
        let width = 0;
        for (const ch of whitespace) {
          width += ch === "\t" ? INDENT_UNIT : 1;
        }
        const level = Math.min(
          Math.floor(width / INDENT_UNIT),
          LEVEL_COUNT - 1,
        );
        return (
          lineBreak +
          '<span class="indent-rainbow-' +
          level +
          '">' +
          whitespace +
          "</span>"
        );
      },
    );
  }

  // 高亮 + 缩进配色, 用于输出框和历史记录展示
  function renderCode(text, lang) {
    return applyIndentColors(highlightCode(text, lang));
  }

  // 输入框随内容行数自动增高, 最高不超过输出框的高度
  function autoGrowDebugInput() {
    if (!debugVariableInput) return;
    const outputPre = debugVariableOutput
      ? debugVariableOutput.closest("pre")
      : null;
    let maxHeight = 120;
    if (outputPre) {
      const h = outputPre.getBoundingClientRect().height;
      if (h > 0) maxHeight = h;
    }
    debugVariableInput.style.height = "auto";
    const border =
      debugVariableInput.offsetHeight - debugVariableInput.clientHeight;
    const needed = debugVariableInput.scrollHeight + border;
    debugVariableInput.style.height = Math.min(needed, maxHeight) + "px";
  }

  // ---- 输入框(contenteditable)辅助: 文本提取 / 光标定位 ----
  const DEBUG_INPUT_ZWSP = "\u200b"; // 行尾哨兵字符: 保证框末尾不会是裸换行, 退格/删除行为才稳定

  // 提取编辑框纯文本, 兜底把 <br>/块级元素按换行处理, 并剔除哨兵字符
  function getDebugInputText() {
    if (!debugVariableInput) return "";
    let result;
    if (!debugVariableInput.querySelector("br, div, p")) {
      result = debugVariableInput.textContent || "";
    } else {
      result = "";
      const walk = function (node) {
        node.childNodes.forEach(function (child) {
          if (child.nodeType === Node.TEXT_NODE) {
            result += child.data;
          } else if (child.tagName === "BR") {
            result += "\n";
          } else if (child.nodeType === Node.ELEMENT_NODE) {
            if (child.tagName === "DIV" || child.tagName === "P")
              result += "\n";
            walk(child);
          }
        });
      };
      walk(debugVariableInput);
    }
    return result.split(DEBUG_INPUT_ZWSP).join("");
  }

  // 生成输入框内部 HTML: 彩色代码 + 缩进配色 + 行尾哨兵字符
  function buildDebugInputHTML(text) {
    return renderCode(text || "", "python") + DEBUG_INPUT_ZWSP;
  }

  // 输入框为空时显示占位提示
  function refreshDebugInputEmptyState(text) {
    if (!debugVariableInput) return;
    debugVariableInput.classList.toggle(
      "debug-input-empty",
      (text || "").length === 0,
    );
  }

  // 光标前的字符数(<br> 记 1 个字符), 光标不在框内时返回 null
  function getCaretCharOffset(el) {
    const sel = window.getSelection();
    if (!sel.rangeCount) return null;
    const range = sel.getRangeAt(0);
    if (!el.contains(range.startContainer)) return null;
    const pre = document.createRange();
    pre.selectNodeContents(el);
    try {
      pre.setEnd(range.startContainer, range.startOffset);
    } catch (error) {
      return null;
    }
    let count = pre.toString().length;
    el.querySelectorAll("br").forEach(function (br) {
      try {
        if (pre.comparePoint(br, 0) === 0) count++;
      } catch (error) {
        /* 忽略越界 */
      }
    });
    return count;
  }

  // 把光标移到第 chars 个字符处
  function setCaretCharOffset(el, chars) {
    if (chars == null || !el) return;
    const sel = window.getSelection();
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let node;
    let remaining = chars;
    while ((node = walker.nextNode())) {
      if (remaining <= node.data.length) {
        const range = document.createRange();
        range.setStart(node, remaining);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
        keepCaretVisible(el);
        return;
      }
      remaining -= node.data.length;
    }
    const range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
    sel.removeAllRanges();
    sel.addRange(range);
    keepCaretVisible(el);
  }

  // 在光标处插入纯文本(只产生文本节点, 不产生 <br>/样式标签)
  function insertPlainTextAtCaret(text) {
    const sel = window.getSelection();
    if (!sel.rangeCount) return;
    const range = sel.getRangeAt(0);
    if (
      !debugVariableInput ||
      !debugVariableInput.contains(range.startContainer)
    ) {
      // 光标不在输入框内时, 追加到输入框末尾
      const fallback = document.createRange();
      fallback.selectNodeContents(debugVariableInput);
      fallback.collapse(false);
      sel.removeAllRanges();
      sel.addRange(fallback);
      insertPlainTextAtCaret(text);
      return;
    }
    range.deleteContents();
    range.insertNode(document.createTextNode(text));
    range.collapse(false);
    sel.removeAllRanges();
    sel.addRange(range);
  }

  // 输入框可滚动时, 保证光标滚动到可见区域
  function keepCaretVisible(el) {
    try {
      const sel = window.getSelection();
      if (!sel.rangeCount) return;
      const rect = sel.getRangeAt(0).getBoundingClientRect();
      if (!rect || (rect.top === 0 && rect.bottom === 0)) return;
      const box = el.getBoundingClientRect();
      if (rect.top < box.top) {
        el.scrollTop -= box.top - rect.top + 4;
      } else if (rect.bottom > box.bottom) {
        el.scrollTop += rect.bottom - box.bottom + 4;
      }
    } catch (error) {
      /* 忽略 */
    }
  }

  let debugInputRendering = false; // 自身渲染期间置真, 防止观察器循环触发
  let debugInputObserver = null; // 兜底观察器, 由初始化代码创建

  // 恢复兜底观察器(下一轮宏任务, 确保本轮所有同步 DOM 变更完成后)
  function resumeDebugInputObserver() {
    if (!debugInputObserver) return;
    setTimeout(function () {
      if (debugInputObserver && debugVariableInput) {
        debugInputObserver.observe(debugVariableInput, {
          childList: true,
          subtree: true,
          characterData: true,
        });
      }
    }, 0);
  }

  // 重新渲染输入框的彩色代码(保留光标位置), 随后自动增高
  function updateDebugInputRender(caretOverride) {
    if (!debugVariableInput) return;
    const caret =
      caretOverride !== undefined
        ? caretOverride
        : getCaretCharOffset(debugVariableInput);
    const text = getDebugInputText();
    // 暂停观察, 避免自身渲染触发循环
    if (debugInputObserver) debugInputObserver.disconnect();
    debugInputRendering = true;
    try {
      debugVariableInput.innerHTML = buildDebugInputHTML(text);
    } finally {
      queueMicrotask(function () {
        debugInputRendering = false;
      });
    }
    refreshDebugInputEmptyState(text);
    if (caret != null) {
      // 哨兵字符始终在末尾, 光标最多落在最后可见字符之后
      setCaretCharOffset(debugVariableInput, Math.min(caret, text.length));
    }
    autoGrowDebugInput();
    resumeDebugInputObserver();
    // 部分移动端布局时机不同, 下一帧再校准一次高度
    requestAnimationFrame(function () {
      if (debugVariableInput) autoGrowDebugInput();
    });
  }

  // 直接设置输入框内容(历史回填/清空时使用)
  function setDebugInputValue(text) {
    if (!debugVariableInput) return;
    const clean = (text || "").split(DEBUG_INPUT_ZWSP).join("");
    if (debugInputObserver) debugInputObserver.disconnect();
    debugInputRendering = true;
    try {
      debugVariableInput.innerHTML = buildDebugInputHTML(clean);
    } finally {
      queueMicrotask(function () {
        debugInputRendering = false;
      });
    }
    refreshDebugInputEmptyState(clean);
    autoGrowDebugInput();
    resumeDebugInputObserver();
  }

  // 回车自动沿用上一行缩进; Ctrl/Cmd + Enter 快捷查询
  function handleDebugInputKeydown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      queryDebugVariable();
      return;
    }
    // 输入法组合中不处理, 避免打断中文输入
    if (event.isComposing || event.keyCode === 229) return;
    if (event.key !== "Enter" || event.shiftKey || event.altKey) return;
    if (!debugVariableInput) return;
    event.preventDefault();
    const text = getDebugInputText();
    const caret = getCaretCharOffset(debugVariableInput) || 0;
    const lineStart = text.lastIndexOf("\n", caret - 1) + 1;
    const currentLine = text.slice(lineStart, caret);
    const indent = (currentLine.match(/^[ \t]*/) || [""])[0];
    insertPlainTextAtCaret("\n" + indent);
    updateDebugInputRender(caret + 1 + indent.length);
  }

  async function initDebugVariable() {
    if (!versionInfo) return;
    // 先查询后端开关状态, 未启用时保持三连击无效
    try {
      const response = await fetch("/debug-variable", { cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      if (!data || data.enabled !== true) return;
    } catch (error) {
      return;
    }
    function onVersionInfoTap() {
      versionClickCount++;
      if (versionClickTimer) clearTimeout(versionClickTimer);
      // 达到三次则打开隐藏页面, 并重置计数
      if (versionClickCount >= 3) {
        versionClickCount = 0;
        versionClickTimer = null;
        showPage("pageDebugVariable");
        if (debugVariableInput) debugVariableInput.focus();
        loadDebugHistory();
        return;
      }
      // 超时未继续点击则重新计数
      versionClickTimer = setTimeout(() => {
        versionClickCount = 0;
        versionClickTimer = null;
      }, VERSION_CLICK_WINDOW);
    }
    // iOS Safari 在 touchend 上 preventDefault(防双击缩放)会抑制随后的 click 事件,
    // 导致快速连点只有第一次生效, 因此优先使用不受影响的 pointerup。
    let lastPointerUpTime = 0; // 最后一次 pointerup 时间, 用于与 click 去重
    if (window.PointerEvent) {
      versionInfo.addEventListener("pointerup", function () {
        lastPointerUpTime = Date.now();
        onVersionInfoTap();
      });
    }
    // 兼容不支持 PointerEvent 的环境(旧浏览器/辅助技术), 同一物理点击只计一次
    versionInfo.addEventListener("click", function () {
      if (Date.now() - lastPointerUpTime < 300) return;
      onVersionInfoTap();
    });
  }
  initDebugVariable();

  async function loadDebugHistory() {
    if (!debugVariableHistory) return;
    try {
      const response = await fetch("/debug-history", { cache: "no-store" });
      if (!response.ok) {
        debugVariableHistory.innerHTML =
          '<div class="debug-history-status">加载历史失败：' +
          response.status +
          "</div>";
        return;
      }
      const data = await response.json();
      const items = Array.isArray(data.items) ? data.items : [];
      if (items.length === 0) {
        debugVariableHistory.innerHTML =
          '<div class="debug-history-status">暂无历史记录</div>';
        return;
      }
      debugVariableHistory.innerHTML = "";
      // ✕ 用 SVG 而非文字字形: 墨迹在不同字体的 em 盒中不居中(同自定义媒体页操作按钮)
      const CLOSE_ICON =
        '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="m3 3 6 6M9 3l-6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" fill="none"/></svg>';
      items.reverse().forEach(function (item) {
        const historyItem = document.createElement("div");
        historyItem.className = "debug-history-item";

        const header = document.createElement("div");
        header.className = "debug-history-header";

        const time = document.createElement("span");
        time.className = "debug-history-time";
        time.textContent =
          item.datetime ||
          (item.timestamp
            ? new Date(item.timestamp * 1000).toLocaleString()
            : "");
        header.appendChild(time);

        const closeBtn = document.createElement("button");
        closeBtn.className = "debug-history-close";
        closeBtn.type = "button";
        closeBtn.title = "删除此历史记录";
        closeBtn.innerHTML = CLOSE_ICON;
        // 图形仅为装饰, 语义交给 aria-label 保证可访问性
        closeBtn.setAttribute("aria-label", "删除此历史记录");
        closeBtn.addEventListener("click", async function (e) {
          e.stopPropagation();
          try {
            await fetch("/debug-history", {
              method: "DELETE",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: item.id }),
            });
            await loadDebugHistory();
          } catch (error) {
            console.warn("删除调试历史记录失败:", error);
          }
        });
        header.appendChild(closeBtn);
        historyItem.appendChild(header);

        const inputSection = document.createElement("div");
        inputSection.className = "debug-history-section";

        const inputLabel = document.createElement("div");
        inputLabel.className = "debug-history-section-label";
        inputLabel.textContent = "输入";
        inputSection.appendChild(inputLabel);

        const codeBlock = document.createElement("pre");
        codeBlock.className = "debug-history-code";
        const codeInner = document.createElement("code");
        codeInner.className = "language-python";
        codeInner.innerHTML = renderCode(item.code || "", "python");
        codeBlock.appendChild(codeInner);
        inputSection.appendChild(codeBlock);
        historyItem.appendChild(inputSection);

        const outputSection = document.createElement("div");
        outputSection.className = "debug-history-section";

        const outputLabel = document.createElement("div");
        outputLabel.className = "debug-history-section-label";
        outputLabel.textContent = "输出";
        outputSection.appendChild(outputLabel);

        const outputBlock = document.createElement("pre");
        outputBlock.className = "debug-history-output";
        const outLang = detectCodeLanguage(item.output);
        const outputInner = document.createElement("code");
        outputInner.className = "language-" + outLang;
        outputInner.innerHTML = renderCode(item.output || "", outLang);
        outputBlock.appendChild(outputInner);
        outputSection.appendChild(outputBlock);
        historyItem.appendChild(outputSection);

        historyItem.addEventListener("click", function () {
          // 先渲染输出框(输出框高度可能变化), 输入框自动增高时才能取到最新上限
          if (debugVariableOutput) {
            const outLang = detectCodeLanguage(item.output);
            debugVariableOutput.className = "language-" + outLang;
            debugVariableOutput.innerHTML = renderCode(
              item.output || "",
              outLang,
            );
          }
          if (debugVariableInput) {
            setDebugInputValue(item.code || "");
            setCaretCharOffset(debugVariableInput, (item.code || "").length);
            debugVariableInput.focus();
          }
        });

        debugVariableHistory.appendChild(historyItem);
      });
    } catch (error) {
      debugVariableHistory.innerHTML =
        '<div class="debug-history-status">加载历史失败：' +
        (error.message || error) +
        "</div>";
      console.warn("加载调试历史记录失败:", error);
    }
  }

  // --- 变量查询：向后端提交 Python 变量或代码段并展示结果 ---
  async function queryDebugVariable() {
    if (!debugVariableInput || !debugVariableOutput) return;
    const code = getDebugInputText();
    if (!code.trim()) {
      debugVariableOutput.className = "language-plain";
      debugVariableOutput.innerHTML = renderCode(
        "请输入Python变量或代码段",
        "plain",
      );
      return;
    }
    debugVariableBtn.disabled = true;
    debugVariableOutput.className = "language-plain";
    debugVariableOutput.innerHTML = renderCode("查询中…", "plain");
    let resultOutput = "";
    try {
      const response = await fetch("/debug-variable", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ code: code }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}`);
      }
      resultOutput = data.output != null ? data.output : "";
      const outLang = detectCodeLanguage(resultOutput);
      debugVariableOutput.className = "language-" + outLang;
      debugVariableOutput.innerHTML = renderCode(resultOutput, outLang);
    } catch (error) {
      resultOutput = `查询失败：${error.message}`;
      debugVariableOutput.className = "language-plain";
      debugVariableOutput.innerHTML = renderCode(resultOutput, "plain");
    } finally {
      debugVariableBtn.disabled = false;
      // 输出框高度可能变化, 同步刷新输入框的最大高度
      autoGrowDebugInput();
    }
    try {
      if (resultOutput && code.trim()) {
        const saveResp = await fetch("/debug-history", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ code: code, output: resultOutput }),
        });
        if (!saveResp.ok) {
          const errData = await saveResp.json().catch(() => ({}));
          if (saveResp.status === 404 && debugVariableHistory) {
            debugVariableHistory.innerHTML =
              '<div class="debug-history-status">历史记录未启用，请重启服务并带上 --debug-variable</div>';
          }
          console.warn(
            "保存调试历史记录失败：",
            saveResp.status,
            errData.error || "",
          );
          return;
        }
        await loadDebugHistory();
      }
    } catch (error) {
      console.warn("保存调试历史记录失败:", error);
    }
  }

  // 输入框(contenteditable): 输入时实时重新渲染彩色代码, 粘贴转纯文本, 回车自动缩进
  let debugInputComposing = false; // 输入法组合中暂停重渲染, 避免打断中文输入
  if (debugVariableInput) {
    debugVariableInput.addEventListener("input", function () {
      if (debugInputComposing) return;
      updateDebugInputRender();
    });
    debugVariableInput.addEventListener("compositionstart", function () {
      debugInputComposing = true;
    });
    debugVariableInput.addEventListener("compositionend", function () {
      debugInputComposing = false;
      updateDebugInputRender();
    });
    debugVariableInput.addEventListener("paste", function (event) {
      const clip = event.clipboardData || window.clipboardData;
      // 取不到剪贴板数据时不拦截, 交给浏览器原生粘贴, 由 input/MutationObserver 兜底
      if (!clip || typeof clip.getData !== "function") return;
      event.preventDefault();
      let text = "";
      try {
        text = clip.getData("text/plain") || "";
      } catch (error) {
        text = "";
      }
      try {
        insertPlainTextAtCaret(text);
      } catch (error) {
        /* 忽略 */
      }
      updateDebugInputRender();
    });
    debugVariableInput.addEventListener("keydown", handleDebugInputKeydown);
    // 兜底: 任何未被拦截的 DOM 变化(原生粘贴/拖放等)也触发重渲染与自动增高
    debugInputObserver = new MutationObserver(function () {
      if (debugInputRendering || debugInputComposing) return;
      updateDebugInputRender();
    });
    debugInputObserver.observe(debugVariableInput, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    setDebugInputValue("");
  }
  // 复制文本到剪贴板(优先 Clipboard API, 失败时回退 execCommand 以兼容 http 环境)
  async function copyTextToClipboard(text) {
    let ok = false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        ok = true;
      } catch (error) {
        ok = false;
      }
    }
    if (!ok) {
      const temp = document.createElement("textarea");
      temp.value = text;
      temp.style.position = "fixed";
      temp.style.opacity = "0";
      document.body.appendChild(temp);
      temp.focus();
      temp.select();
      try {
        ok = document.execCommand("copy");
      } catch (error) {
        ok = false;
      }
      document.body.removeChild(temp);
    }
    return ok;
  }

  // 按钮点击后短暂切换为 ✓ 图形作为成功反馈
  // 仅切换 .debug-box-btn-ok 类控制两个 SVG 的显隐, 不改写按钮内容,
  // 避免覆盖后丢失原有 SVG(且 textContent 快照恢复不回 SVG)
  function flashButtonOk(button) {
    if (!button) return;
    button.classList.add("debug-box-btn-ok");
    setTimeout(function () {
      button.classList.remove("debug-box-btn-ok");
    }, 900);
  }

  if (debugVariableBtn) {
    debugVariableBtn.addEventListener("click", queryDebugVariable);
  }
  // 输入框右上角: 复制 / 清除
  if (debugInputCopyBtn) {
    debugInputCopyBtn.addEventListener("click", async function () {
      const text = getDebugInputText();
      if (!debugVariableInput || !text) return;
      const ok = await copyTextToClipboard(text);
      if (ok) flashButtonOk(debugInputCopyBtn);
    });
  }
  if (debugInputClearBtn) {
    debugInputClearBtn.addEventListener("click", function () {
      if (!debugVariableInput) return;
      setDebugInputValue("");
      debugVariableInput.focus();
      setCaretCharOffset(debugVariableInput, 0);
    });
  }
  // 输出框右上角: 复制
  if (debugOutputCopyBtn) {
    debugOutputCopyBtn.addEventListener("click", async function () {
      if (!debugVariableOutput || !debugVariableOutput.textContent) return;
      const ok = await copyTextToClipboard(debugVariableOutput.textContent);
      if (ok) flashButtonOk(debugOutputCopyBtn);
    });
  }

  // 菜单切换按钮
  if (toggleMenuBtn) {
    toggleMenuBtn.addEventListener("click", toggleMenu);
  }
  if (menuBackdrop) {
    menuBackdrop.addEventListener("click", () => setMenuVisibility(true));
  }

  // --- 初始化 ---
  // 根据屏幕宽度初始化菜单状态
  if (window.innerWidth <= 600) {
    setMenuVisibility(true);
  } else {
    setMenuVisibility(menu.classList.contains("hidden"));
  }

  // 将 YouTube Cookie 设置加载函数暴露到全局，方便其他页面调用
  window.loadYoutubeCookieSetting = loadYoutubeCookieSetting;

  // 初始化时显示默认页面 (例如消息页面)
  showPage("pageMessage");
  loadYoutubeCookieSetting();
  loadFavoriteUpdateStatus();
  setInterval(renderFavoriteUpdateCountdown, 1000);
  setInterval(loadFavoriteUpdateStatus, 15000);

  if (alwaysUseYoutubeCookie) {
    alwaysUseYoutubeCookie.addEventListener("change", saveYoutubeCookieSetting);
  }
  if (immediateUpdateBtn) {
    immediateUpdateBtn.addEventListener("click", requestImmediateUpdate);
  }
  if (favoriteUpdateCountdown) {
    favoriteUpdateCountdown.style.cursor = "pointer";
    favoriteUpdateCountdown.title = "点击切换显示预计运行时间";
    favoriteUpdateCountdown.addEventListener("click", toggleExpectedRunTime);
  }
  // --- 页面可见性检测：标签页切回前台后自动恢复轮询 ---
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      // 当且仅当处于消息页面且定时器未启动时恢复
      if (
        !pollingTimer &&
        pages.pageMessage &&
        pages.pageMessage.style.display !== "none"
      ) {
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
