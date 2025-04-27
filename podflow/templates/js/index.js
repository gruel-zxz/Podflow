(function() {
  // 缓存常用节点
  const menu = document.getElementById('menu');
  const toggleMenuBtn = document.getElementById('toggleMenu');
  const pages = {
    pageChannel: document.getElementById('pageChannel'),
    pageMessage: document.getElementById('pageMessage')
  };
  const inputForm = document.getElementById('inputForm');
  const inputOutput = document.getElementById('inputOutput');
  const pasteBtn = document.getElementById('pasteBtn');
  const copyBtn = document.getElementById('copyBtn');
  const clearBtn = document.getElementById('clearBtn');
  // 缓存进度条和文本元素
  const mainProgress = document.getElementById('mainProgress');
  const progressStatus = document.getElementById('progressStatus');
  const progressPercentage = document.getElementById('progressPercentage');
  const messageArea = document.getElementById('messageArea');
  const messageHttp = document.getElementById('messageHttp');
  const messageDownload = document.getElementById('messageDownload');

  let lastMessage = { schedule: [], podflow: [], http: [], download: [] };
  let pollingTimer = null;
  let userScrolled = false;
  let eventSource = null; // 用于存储 EventSource 实例
  
  // 生成单个二维码的函数
  function generateQRCodeForNode(container) {
    const rootStyles = getComputedStyle(document.documentElement);
    const textColor = rootStyles.getPropertyValue('--text-color').trim();
    const inputBg = rootStyles.getPropertyValue('--input-bg').trim();
    const url = container.dataset.url;
    container.innerHTML = '';
    if (url) {
      new QRCode(container, {
        text: url,
        width: 220,
        height: 220,
        colorDark: textColor,
        colorLight: inputBg,
        correctLevel: QRCode.CorrectLevel.L
      });
    } else {
      container.textContent = 'URL 未提供';
    }
  }

  // 菜单切换函数
  function toggleMenu() {
    menu.classList.toggle('hidden');
    if (menu.classList.contains('hidden')) {
      toggleMenuBtn.style.left = '0px';
      toggleMenuBtn.textContent = '❯';
    } else {
      toggleMenuBtn.style.left = 'var(--menu-width)';
      toggleMenuBtn.textContent = '❮';
    }
  }

  // 根据页面标识显示对应面板
  function showPage(pageId) {
    Object.values(pages).forEach(page => page.style.display = 'none');
    if (pages[pageId]) {
      pages[pageId].style.display = 'block';
      // 手机模式下自动隐藏菜单
      if (window.innerWidth <= 600 && typeof menu !== 'undefined' && !menu.classList.contains('hidden')) {
        if (typeof toggleMenu === 'function') {
          toggleMenu();
        }
      }
      // --- SSE 连接管理 ---
      if (pageId === 'pageMessage') {
        startMessageStream(); // <--- 启动 SSE 连接
      } else {
        stopMessageStream(); // <--- 关闭 SSE 连接
      }
    }
  }

  // 监听滚动事件，检测用户是否手动滚动
  function onUserScroll(event) {
    const element = event.target;
    // 判断是否接近底部，增加一定的容差值
    const nearBottom = element.scrollHeight - element.scrollTop <= element.clientHeight + 10;
    userScrolled = !nearBottom;
  }

  // 轮询消息更新，更新 messageArea 与 messageHttp
  function getMessages() {
    fetch('message')
      .then(response => response.json()) // 解析 JSON 数据
      .then(data => {
        // 更新进度条
        if (JSON.stringify(data.schedule) !== JSON.stringify(lastMessage.schedule)) {
          updateProgress(data.schedule);
          lastMessage.schedule = data.schedule;
        }
        // 追加新消息
        if (JSON.stringify(data.podflow) !== JSON.stringify(lastMessage.podflow)) {
          appendMessages(messageArea, data.podflow, lastMessage.podflow);
          lastMessage.podflow = data.podflow;
        }
        if (JSON.stringify(data.http) !== JSON.stringify(lastMessage.http)) {
          appendMessages(messageHttp, data.http, lastMessage.http);
          lastMessage.http = data.http;
        }
        if (JSON.stringify(data.download) !== JSON.stringify(lastMessage.download)) {
          appendBar(messageDownload, data.download, lastMessage.download);
          lastMessage.download = data.download
        }
      })
      .catch(error => console.error('获取消息失败:', error));
  }
  
  // 更新进度条并显示状态和百分比
  function updateProgress(scheduleData) {
    // 检查 schedule 数据是否存在且长度为 2
    if (scheduleData && scheduleData.length === 2) {
      const [status, progress] = scheduleData; // 直接解构数组
      if (status === "准备中" || status === "构建中") {
        mainProgress.style.width = `${progress * 100}%`;
        progressStatus.textContent = status;   // 显示状态
        progressPercentage.textContent = `${(progress * 100).toFixed(2)}%`;   // 显示百分比，保留两位小数
      } else if (status === "已完成") {
        mainProgress.style.width = '100%';
        progressStatus.textContent = '已完成';   // 显示完成状态
        progressPercentage.textContent = '100.0%';   // 显示百分比
      }
    }
  }
  
  function createMessageElement(message) {
    const div = document.createElement('div');
    div.innerHTML = message;
    div.className = 'message';
    return div;
  }
  
  function processQRCodeContainers(div) {
    const qrContainers = div.querySelectorAll('.qrcode-container');
    qrContainers.forEach(container => {
      // 判断当前容器是否有 data-url 属性，并且值不为空
      if (container.dataset.url) {
        generateQRCodeForNode(container);
      } else {
        // 如果没有 data-url 或值为空，可以执行其他操作，例如输出提示信息
        console.log('容器中未提供 URL，跳过二维码生成:', container);
        container.textContent = '未提供二维码 URL'; // 可选：在容器中显示提示
      }
    });
  }
  
  // 修改后的 appendMessages 函数：先生成消息节点内的二维码，再将节点追加或替换到消息容器中
  function appendMessages(container, newMessages, oldMessages) {
    // 判断当前是否在底部
    const wasAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 10;
    // 较为简单的情况：两数组长度相同且有内容，只比较最后四项
    if (newMessages.length === oldMessages.length && newMessages.length > 0) {
      let replaceCount;
      if (newMessages[newMessages.length - 1].includes("未扫描") || 
          newMessages[newMessages.length - 1].includes("二维码超时, 请重试")) {
        replaceCount = Math.min(4, newMessages.length);
      } else {
        replaceCount = 1;
      }
      for (let i = 0; i < replaceCount; i++) {
        // 计算从后向前的索引位置
        const index = newMessages.length - 1 - i;
        const newMessage = newMessages[index];
        const oldMessage = oldMessages[index];
        if (newMessage !== oldMessage) {
          // 先创建消息节点
          const div = createMessageElement(newMessage);
          // 在插入前先处理二维码生成
          processQRCodeContainers(div);
          // 替换到容器中 - 注意这里要找到对应位置的子元素
          const childToReplace = container.children[index];
          if (childToReplace) {
            container.replaceChild(div, childToReplace);
          }
        }
      }
    } else {
      // 当 newMessages 与 oldMessages 数量不一致时
      // 如果 oldMessages 存在数据，先替换容器中最后一项对应的消息
      if (oldMessages.length > 0) {
        const replaceIndex = oldMessages.length - 1;
        const div = createMessageElement(newMessages[replaceIndex]);
        // 先生成二维码
        processQRCodeContainers(div);
        const lastChild = container.lastElementChild;
        if (lastChild) {
          container.replaceChild(div, lastChild);
        } else {
          container.appendChild(div);
        }
      }
      // 再追加从 oldMessages.length 开始的后续消息
      newMessages.slice(oldMessages.length).forEach(msg => {
        const div = createMessageElement(msg);
        // 先生成二维码
        processQRCodeContainers(div);
        // 插入容器中
        container.appendChild(div);
      });
    }
    // 如果之前在底部且用户没有主动滚动，则自动滚动到底部
    if (wasAtBottom && !userScrolled) {
      container.scrollTop = container.scrollHeight;
    }
  }

  function appendBar(container, newMessages, oldMessages) {
    // 遍历新的消息并渲染进度条
    if (newMessages.length > 0) {
      downloadLabel.textContent = '下载进度：';
      const newlength = newMessages.length;
      const oldlength = oldMessages.length;
      if (oldlength!== 0){
        const childToReplace = container.children[0];
        const newMessage = newMessages[oldlength - 1];
        const oldMessage = oldMessages[oldlength - 1];
        if (newMessage !== oldMessage){
          const [percentageText, time, speed, status, idname, nameText, file] = newMessage;
          childToReplace.querySelector('#pbProgress' + oldlength).style.width = `${percentageText * 100}%`;
          childToReplace.querySelector('#pbStatusText' + oldlength).innerHTML = status;
          childToReplace.querySelector('#pbPercentageText' + oldlength).innerHTML = `${(percentageText * 100).toFixed(2)}%`;
          childToReplace.querySelector('#speedText' + oldlength).innerHTML = speed;
          childToReplace.querySelector('#timeText' + oldlength).innerHTML = time;
        }
      }
      if (newlength !== oldlength) {
        for (let i = oldlength; i < newlength; i++) {
          const messageContent = newMessages[i];
          const [percentageText, time, speed, status, idname, nameText, file] = messageContent;
          const download = document.createElement('div');
          download.className = 'download-container';
          // 创建 idname 文本节点（只创建一次）
          const idnameText = document.createElement('div');
          idnameText.className = 'scroll-text';
          idnameText.innerHTML = '  ' + idname;
          // 创建文件信息部分
          const fileInfo = document.createElement('div');
          fileInfo.className = 'scroll';
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
          // 延迟测量文本宽度，决定是否滚动
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
                  const speed = 30;
                  const duration = singleContentWidth / speed;
                  namebar.style.animationDuration = duration + 's';
                  // 延迟添加滚动类
                  setTimeout(() => {
                      namebar.classList.add('scrolling');
                  }, 1500);
              } else {
                  // 不需要滚动，确保移除动画类和样式
                  namebar.classList.remove('scrolling');
                  namebar.style.animationDuration = '';
              }
          }, 0);
          // 进度条部分
          const pbBar = document.createElement('div');
          pbBar.className = 'pb-bar';
          const pbProgress = document.createElement('div');
          pbProgress.className = 'pb-progress pb-animated';
          pbProgress.style.width = `${percentageText * 100}%`;
          pbProgress.id = 'pbProgress' + (i+1);
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
          // 速度部分
          const speedContainer = document.createElement('div');
          speedContainer.className = 'scroll';
          const speedText = document.createElement('div');
          speedText.className = 'speed-text';
          speedText.innerHTML = speed;
          speedText.id = 'speedText' + (i+1);
          const timeText = document.createElement('div');
          timeText.className = 'time-text';
          timeText.innerHTML = time;
          timeText.id = 'timeText' + (i+1);
          speedContainer.appendChild(speedText);
          speedContainer.appendChild(timeText);
          download.appendChild(speedContainer);
          container.insertBefore(download, container.firstChild);
        }
      }
    }
  }

  // 启动 SSE 连接
  function startMessageStream() {
    // 如果已存在连接，先关闭
    if (eventSource) {
      eventSource.close();
    }
    // 创建新的 EventSource 连接到 /stream 端点
    eventSource = new EventSource('/stream'); // <--- 连接到新的 SSE 端点
    // 监听 'message' 事件 (默认事件)
    eventSource.onmessage = function(event) {
      try {
        // event.data 是服务器发送的 JSON 字符串
        const data = JSON.parse(event.data);
        // --- 更新 UI (逻辑与原 getMessages 类似) ---
        // 确保 lastMessage 和 data 结构完整
        lastMessage = lastMessage || { schedule: {}, podflow: [], http: [], download: [] };
        data.schedule = data.schedule || {};
        data.podflow = data.podflow || [];
        data.http = data.http || [];
        data.download = data.download || [];
        // 更新进度条 (如果 updateProgress 存在)
        if (typeof updateProgress === 'function' && JSON.stringify(data.schedule) !== JSON.stringify(lastMessage.schedule)) {
          updateProgress(data.schedule);
          lastMessage.schedule = data.schedule;
        }
        // 追加新消息 (如果 appendMessages 存在)
        if (typeof appendMessages === 'function') {
          if (JSON.stringify(data.podflow) !== JSON.stringify(lastMessage.podflow)) {
            appendMessages(messageArea, data.podflow, lastMessage.podflow || []); // 传入旧消息用于比较
            lastMessage.podflow = [...data.podflow]; // 创建副本以避免引用问题
          }
          if (JSON.stringify(data.http) !== JSON.stringify(lastMessage.http)) {
            appendMessages(messageHttp, data.http, lastMessage.http || []); // 传入旧消息
            lastMessage.http = [...data.http]; // 创建副本
          }
        }
        // 更新下载栏 (如果 appendBar 存在)
        if (typeof appendBar === 'function' && JSON.stringify(data.download) !== JSON.stringify(lastMessage.download)) {
          appendBar(messageDownload, data.download, lastMessage.download || []); // 传入旧消息
          lastMessage.download = [...data.download]; // 创建副本
        }
      } catch (error) {
        console.error('处理 SSE 消息失败:', error, '原始数据:', event.data);
      }
    };
    // 监听错误事件
    eventSource.onerror = function(error) {
      console.error('EventSource 失败:', error);
      // 可以选择在这里关闭连接或尝试重连，但 EventSource 通常会自动重连
      // eventSource.close(); // 如果需要手动停止
    };
    console.log("SSE 连接已启动");
  }

  // 停止 SSE 连接
  function stopMessageStream() {
    if (eventSource) {
      eventSource.close(); // 关闭连接
      eventSource = null; // 清除引用
      console.log("SSE 连接已关闭");
    }
  }

  // 滚动事件监听器
  messageArea.addEventListener('scroll', onUserScroll);
  messageHttp.addEventListener('scroll', onUserScroll);
  messageDownload.addEventListener('scroll', onUserScroll);

  // 初始化默认页面
  showPage('pageMessage');

  // 表单异步提交（获取 Channel-ID）
  inputForm && inputForm.addEventListener('submit', function(event) {
    event.preventDefault();
    const content = inputOutput.value;
    fetch('getid', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    })
      .then(response => {
        if (!response.ok) {
          throw new Error('网络响应异常');
        }
        return response.json();
      })
      .then(data => inputOutput.value = data.response)
      .catch(error => {
        console.error('请求失败:', error);
        alert('请求失败，请稍后重试！');
      });
  });

  // 粘贴功能
  pasteBtn.addEventListener('click', function() {
    if (navigator.clipboard && navigator.clipboard.readText) {
      navigator.clipboard.readText().then(text => {
        inputOutput.value = text;
        inputOutput.focus();
      }).catch(err => {
        console.warn("剪贴板读取失败:", err);
        alert("无法读取剪贴板，请手动粘贴！");
      });
    } else {
      try {
        inputOutput.focus();
        document.execCommand('paste');
      } catch (err) {
        console.warn("execCommand 粘贴失败:", err);
        alert("您的浏览器不支持自动粘贴，请手动操作！");
      }
    }
  });

  // 复制功能
  copyBtn.addEventListener('click', function() {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(inputOutput.value).catch(err => {
        console.warn("复制失败:", err);
        alert("无法复制，请手动选择文本后按 Ctrl+C 复制！");
      });
    } else {
      try {
        inputOutput.select();
        document.execCommand('copy');
      } catch (err) {
        console.warn("execCommand 复制失败:", err);
        alert("您的浏览器不支持复制，请手动操作！");
      }
    }
  });

  // 清空输入框
  clearBtn.addEventListener('click', function() {
    inputOutput.value = '';
  });

  // 菜单项点击事件委托
  menu.addEventListener('click', function(event) {
    const target = event.target;
    if (target.tagName.toLowerCase() === 'li' && target.dataset.page) {
      showPage(target.dataset.page);
    }
  });

  // 菜单切换按钮事件绑定
  toggleMenuBtn.addEventListener('click', toggleMenu);

  // 针对手机端，初始化时隐藏菜单
  if (window.innerWidth <= 600) {
    menu.classList.add('hidden');
    toggleMenuBtn.style.left = '0px';
    toggleMenuBtn.textContent = '❯';
  }
})();