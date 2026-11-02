// /templates/js/custom_media.js
(function () {
  const API_URL = "/custom-media";
  // 可选项兜底数据(仅后端未随列表下发desc时使用), 与 config_desc.channel.youtube 保持一致;
  // 正常情况下候选数据以后端下发的 config_desc["channel"]["youtube"] 为准(见 loadList)
  const FALLBACK_DESC = {
    media: {
      default: "m4a",
      type: "select",
      options: [
        { value: "m4a", label: "m4a 音频" },
        { value: "mp4", label: "mp4 视频" },
      ],
      desc: "下载媒体类型",
    },
    quality: {
      default: "1080",
      type: "select",
      when_show: { key: "media", value: "mp4" },
      options: [
        { value: "144", label: "144p 极低画质(极省流量)" },
        { value: "180", label: "180p 超低画质" },
        { value: "216", label: "216p 极低分档" },
        { value: "240", label: "240p 流畅画质" },
        { value: "360", label: "360p 标清(SD)" },
        { value: "480", label: "480p 清晰(标清)" },
        { value: "720", label: "720p 高清(HD)" },
        { value: "1080", label: "1080p 全高清(FHD)" },
        { value: "1440", label: "1440p 超高清2K(QHD)" },
        { value: "2160", label: "2160p 超高清4K(UHD)" },
        { value: "4320", label: "4320p 极清8K(FUHD)" },
      ],
      desc: "媒体分辨率(仅在media为视频时有效)",
    },
    audio_track_language: {
      default: "zh",
      type: "select",
      options: [{ value: "zh", label: "zh 中文" }],
      desc: "音频轨道语言(默认为中文)",
    },
  };
  // 后端随列表下发的字段定义(config_desc.channel.youtube 的三个下拉), 供构建下拉使用
  const DESC_KEYS = ["media", "quality", "audio_track_language"];
  // 媒体状态名称, 与后端 custom_media_status 保持一致(状态由后台下载流程更新)
  const STATUS_LABELS = {
    preparing: "准备中",
    completed: "已完成",
    failed: "失败",
  };
  // 后台新增的状态不在上表内, 直接显示其原始值
  const DEFAULT_STATUS = "preparing";
  // 媒体格式名称(兼容旧数据中的audio/video取值), 用于列表显示
  const TYPE_LABELS = {
    m4a: "音频",
    mp4: "视频",
    audio: "音频",
    video: "视频",
  };
  // 已添加媒体列表的自动刷新间隔(仅在本页显示且标签页在前台时才会请求)
  const AUTO_REFRESH_MS = 60000;

  const $ = {
    page: document.getElementById("pageCustomMedia"),
    form: document.getElementById("customMediaForm"),
    url: document.getElementById("customMediaUrl"),
    urlClear: document.getElementById("customMediaUrlClear"),
    type: document.getElementById("customMediaType"),
    quality: document.getElementById("customMediaQuality"),
    qualityItem: document.getElementById("customMediaQualityItem"),
    language: document.getElementById("customMediaLanguage"),
    downloadBtn: document.getElementById("customMediaDownloadBtn"),
    refreshBtn: document.getElementById("customMediaRefreshBtn"),
    list: document.getElementById("customMediaList"),
    status: document.getElementById("customMediaStatus"),
    busyHint: document.getElementById("customMediaBusyHint"),
  };

  // 页面状态: rev为后端列表文件的版本号, 提交时带回以防用旧内容覆盖后台的写入
  // busy为后台忙碌标记, 为true时禁用本页所有操作按钮; desc为后端下发的字段定义
  const state = { rev: null, busy: false, desc: null };
  // 三个下拉的构建状态: ""未构建 / "fallback"兜底数据 / "config"后端真实数据(config_desc)
  // 后端真实数据可覆盖更早的兜底构建, 构建后不再重复(列表每分钟自动刷新)
  let descSource = "";
  // 冲突错误文案(后端列表已被改动, 网页的本次提交被拒绝)
  const CONFLICT_MESSAGE =
    "列表已在后台更新, 本次操作已取消, 请确认最新列表后重试";

  // 应用后端返回的版本号及忙碌标记
  function applyServerState(data) {
    if (!data) return;
    // 后端未返回rev时保持原值, 避免提交空版本号导致误判冲突
    if (typeof data.rev === "string") state.rev = data.rev;
    if (typeof data.busy === "boolean") setBusy(data.busy);
  }

  // 后台忙碌时禁用本页所有写操作的按钮及输入框, 并显示提示
  // 注: 刷新按钮只读, 不写文件, 故保持可用, 避免页面被卡在忙碌状态而无从恢复
  function setBusy(busy) {
    state.busy = busy === true;
    if ($.downloadBtn) $.downloadBtn.disabled = state.busy;
    if ($.url) $.url.disabled = state.busy;
    if ($.urlClear) $.urlClear.disabled = state.busy;
    setSelectDisabled($.type, state.busy);
    setSelectDisabled($.quality, state.busy);
    setSelectDisabled($.language, state.busy);
    // 列表内的排序及删除按钮
    // 仅在忙碌时统一禁用; 解除忙碌时不改动, 由renderList按首尾位置重新计算
    if ($.list && state.busy) {
      $.list.querySelectorAll("button[data-action]").forEach((btn) => {
        btn.disabled = true;
      });
    }
    if ($.busyHint) {
      $.busyHint.hidden = !state.busy;
      $.busyHint.textContent = state.busy
        ? "⏳ 后台正在处理自定义媒体, 所有操作按钮已暂时禁用(🔄 刷新仍可使用)"
        : "";
    }
  }

  function setStatus(text, color) {
    if (!$.status) return;
    $.status.textContent = text;
    $.status.style.color = color || "green";
  }

  // 清空操作提示信息
  function clearStatus() {
    if (!$.status) return;
    $.status.textContent = "";
    $.status.style.color = "";
  }

  // 版本号冲突时的统一处理: 采用后端回传的最新列表及版本号, 避免用户重试时再次冲突
  async function handleConflict(err) {
    if (!err || !err.conflict) return false;
    console.warn("自定义媒体版本冲突, 已放弃本次写入并重载列表");
    // 409响应已附带最新列表与版本号, 直接采用
    applyServerState(err.data);
    if (err.data && Array.isArray(err.data.list)) renderList(err.data.list);
    else await loadList();
    // 重载后忙碌状态可能已变化, 需重新应用按钮禁用
    if (state.busy) setBusy(true);
    setStatus(CONFLICT_MESSAGE, "orange");
    return true;
  }

  // 本页是否处于可刷新状态(本页已显示, 且浏览器标签页在前台)
  function isPageActive() {
    if (!$.page || $.page.style.display === "none") return false;
    return document.visibilityState === "visible";
  }

  // 每分钟自动刷新已添加的媒体, 页面未显示或标签页在后台时跳过
  async function autoRefresh() {
    if (!isPageActive()) return;
    await loadList();
  }

  // 仅媒体格式为 when_show 声明的取值(如 mp4)时才显示画质下拉, 与配置页 when_show 行为一致
  function toggleQuality() {
    if (!$.qualityItem || !$.type) return;
    const rule = state.desc && state.desc.quality && state.desc.quality.when_show;
    const condition =
      rule && rule.key === "media" ? rule : FALLBACK_DESC.quality.when_show;
    $.qualityItem.hidden = $.type.value !== condition.value;
  }

  // 禁用下拉: 兼容原生 select 与自定义下拉容器(div.custom-select 提供 setDisabled)
  function setSelectDisabled(el, disabled) {
    if (!el) return;
    if (typeof el.setDisabled === "function") el.setDisabled(disabled);
    else el.disabled = disabled;
  }

  // 媒体格式/画质/音频轨道语言三个下拉统一使用全局自定义下拉组件
  // (custom_select.js, 与修改运行配置页一致):
  // 用组件容器替换 HTML 中的原生 select(保留作无 JS 时的兜底), 值经容器的 .value 读取。
  function buildSelect(selectEl, options, defaultValue, onPick) {
    if (!selectEl || typeof CustomSelect === "undefined") return;
    const wrapper = CustomSelect.create({
      id: selectEl.id,
      options: options,
      value: selectEl.value || defaultValue,
      eqStr: (a, b) => String(a) === String(b),
      onPick: onPick,
    });
    wrapper.classList.add("custom-media-select");
    selectEl.replaceWith(wrapper);
    return wrapper;
  }

  // 清洗后端下发的字段定义(config_desc.channel.youtube 的三个下拉):
  // 候选缺失/为空时回退到兜底数据, 保证下拉始终可构建
  function getDescEntry(desc, key) {
    const entry = desc && desc[key];
    if (entry && Array.isArray(entry.options) && entry.options.length) {
      return entry;
    }
    return FALLBACK_DESC[key];
  }

  // 按字段定义构建三个下拉(候选与默认值源自 config_desc.channel.youtube,
  // 候选中英文双语 label 的灰显规则与修改运行配置页一致, 见 custom_select.js),
  // 列表每分钟自动刷新, 构建一次后不重复; 后端真实数据可覆盖更早的兜底构建
  function applyDesc(desc) {
    if (descSource === "config") return;
    const valid = !!(desc && DESC_KEYS.every((key) => getDescEntry(desc, key) === desc[key]));
    if (descSource === "fallback" && !valid) return;
    descSource = valid ? "config" : "fallback";
    state.desc = DESC_KEYS.reduce((acc, key) => {
      acc[key] = getDescEntry(desc, key);
      return acc;
    }, {});
    // 生成媒体格式下拉(m4a音频/mp4视频, 取自 config_desc 的 media; 选中后联动画质显隐)
    $.type =
      buildSelect(
        $.type,
        state.desc.media.options,
        state.desc.media.default,
        toggleQuality,
      ) || $.type;
    // 生成画质下拉(144p - 4320p, 取自 config_desc 的 quality)
    $.quality =
      buildSelect(
        $.quality,
        state.desc.quality.options,
        state.desc.quality.default,
      ) || $.quality;
    // 生成音频轨道语言下拉(取自 config_desc 的 audio_track_language)
    $.language =
      buildSelect(
        $.language,
        state.desc.audio_track_language.options,
        state.desc.audio_track_language.default,
      ) || $.language;
    toggleQuality();
  }

  // 获取状态名称, 兼容后台自定义的状态及旧数据缺少status的情况
  function getStatusLabel(status) {
    if (!status) return STATUS_LABELS[DEFAULT_STATUS];
    return STATUS_LABELS[status] || status;
  }

  // 状态对应的css类名, 避免后台写入特殊字符时生成非法类名
  function getStatusClass(status) {
    return `status-${String(status || DEFAULT_STATUS).replace(/[^\w-]/g, "-")}`;
  }

  // 按钮图形用 SVG 而非文字字形: ✕/↑/↓ 的墨迹在不同字体的 em 盒中不居中,
  // 改用固定尺寸的 SVG 以 currentColor 着色保证始终居中(同 config.js 步进按钮)
  const ACTION_ICONS = {
    up: '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="M6 2.5v7M2.8 5.7 6 2.5l3.2 3.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>',
    down: '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="M6 2.5v7M2.8 6.3 6 9.5l3.2-3.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>',
    delete:
      '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="m3 3 6 6M9 3l-6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" fill="none"/></svg>',
  };

  // 构建排序及删除按钮
  function buildActionBtn(className, title, action, index) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `custom-media-btn ${className}`;
    btn.innerHTML = ACTION_ICONS[action];
    btn.title = title;
    // 图形仅为装饰, 语义交给 aria-label 保证可访问性
    btn.setAttribute("aria-label", title);
    btn.dataset.action = action;
    btn.dataset.index = index;
    return btn;
  }

  // 显示已添加的自定义媒体
  function renderList(list) {
    if (!$.list) return;
    $.list.innerHTML = "";
    if (!list || !list.length) {
      const empty = document.createElement("div");
      empty.className = "custom-media-empty";
      empty.textContent = "暂无自定义媒体";
      $.list.appendChild(empty);
      return;
    }
    list.forEach((item, index) => {
      const typeLabel = TYPE_LABELS[item.type] || item.type;
      // 视频显示画质, 音频显示音频轨道语言, 均缺失时显示 -
      const qualityText =
        (item.type === "mp4" || item.type === "video") && item.quality
          ? `${item.quality}p`
          : (item.type === "m4a" || item.type === "audio") &&
              item.audio_track_language
            ? item.audio_track_language
            : "-";
      const status = item.status || DEFAULT_STATUS;
      const statusClass = getStatusClass(status);
      const row = document.createElement("div");
      row.className = `custom-media-item ${statusClass}`;

      const num = document.createElement("span");
      num.className = "custom-media-index";
      num.textContent = `${index + 1}.`;

      const info = document.createElement("span");
      info.className = "custom-media-info";

      const type = document.createElement("span");
      type.className = "custom-media-type";
      type.textContent = `${typeLabel} ${qualityText}`;

      const statusText = document.createElement("span");
      statusText.className = `custom-media-status-text ${statusClass}`;
      statusText.textContent = getStatusLabel(status);

      // 抓取到的媒体标题, 独占一行显示, 过长时省略并可用悬浮查看全名
      const title = document.createElement("span");
      title.className = "custom-media-title";
      title.textContent = item.title || "";
      if (item.title) title.title = item.title;

      const url = document.createElement("span");
      url.className = "custom-media-url";
      url.textContent = item.url || "";

      // 媒体信息抓取失败的原因, 独占一行以便刷新页面后仍能看到
      const error = document.createElement("span");
      error.className = "custom-media-error";
      error.textContent =
        item.status === "failed" && item.error ? item.error : "";

      info.appendChild(type);
      info.appendChild(statusText);
      // lists 内有多个dict时说明该链接包含多个分集, 显示分集总数供用户确认
      const parts = Array.isArray(item.lists) ? item.lists.length : 0;
      if (parts > 1) {
        const partsText = document.createElement("span");
        partsText.className = "custom-media-parts";
        partsText.textContent = `共 ${parts} 集`;
        partsText.title = `该媒体包含 ${parts} 个分集`;
        info.appendChild(partsText);
      }
      // 未抓取到标题时不生成空行, 免得多出一行空白
      if (item.title) info.appendChild(title);
      info.appendChild(url);
      if (error.textContent) info.appendChild(error);

      // 排序按钮, 首尾位置禁用对应方向
      const upBtn = buildActionBtn(
        "custom-media-up-btn",
        "上移",
        "up",
        index,
      );
      const downBtn = buildActionBtn(
        "custom-media-down-btn",
        "下移",
        "down",
        index,
      );
      const deleteBtn = buildActionBtn(
        "custom-media-delete-btn",
        "删除",
        "delete",
        index,
      );
      if (index === 0) upBtn.disabled = true;
      if (index === list.length - 1) downBtn.disabled = true;

      row.appendChild(num);
      row.appendChild(info);
      row.appendChild(upBtn);
      row.appendChild(downBtn);
      row.appendChild(deleteBtn);
      $.list.appendChild(row);
    });
  }

  // 读取已添加的自定义媒体
  async function loadList() {
    if (!$.list) return;
    try {
      const res = await fetch(API_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      applyServerState(data);
      // 按后端下发的字段定义(config_desc)构建三个下拉, 仅首次或由兜底升级时生效
      applyDesc(data.desc);
      renderList(data.list || []);
      // 忙碌状态下renderList重新生成的按钮需再次禁用
      if (state.busy) setBusy(true);
    } catch (err) {
      console.error("读取自定义媒体列表失败:", err);
      $.list.innerHTML = "";
      const error = document.createElement("div");
      error.className = "custom-media-empty";
      error.textContent = `列表读取失败: ${err.message}`;
      $.list.appendChild(error);
    }
  }

  // 请求自定义媒体接口并返回数据, 冲突(409)时在错误对象上标记conflict与回传数据
  async function postMedia(path, body) {
    const res = await fetch(`${API_URL}/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.assign({ rev: state.rev }, body)),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.error || `HTTP ${res.status}`);
      err.conflict = res.status === 409;
      err.data = data;
      throw err;
    }
    return data;
  }

  // 上移或下移自定义媒体
  async function moveMedia(index, step) {
    try {
      const data = await postMedia("reorder", {
        old_index: index,
        new_index: index + step,
      });
      setStatus(`排序成功, 当前共 ${data.count} 个自定义媒体`, "green");
      await loadList();
    } catch (err) {
      // 版本冲突属预期情况(后台已更新列表), 不按错误处理
      if (await handleConflict(err)) return;
      console.error("自定义媒体排序失败:", err);
      setStatus(`排序失败: ${err.message}`, "red");
    }
  }

  // 删除自定义媒体
  async function removeMedia(index) {
    if (!window.confirm("确定删除该自定义媒体吗?")) return;
    try {
      const data = await postMedia("remove", { index: index });
      setStatus(
        `「${data.data.url}」已删除, 当前共 ${data.count} 个自定义媒体`,
        "green",
      );
      await loadList();
    } catch (err) {
      // 版本冲突属预期情况(后台已更新列表), 不按错误处理
      if (await handleConflict(err)) return;
      console.error("自定义媒体删除失败:", err);
      setStatus(`删除失败: ${err.message}`, "red");
    }
  }

  // 处理列表内的排序及删除按钮
  function listClick(event) {
    const btn = event.target.closest("button[data-action]");
    if (!btn || btn.disabled) return;
    const index = Number(btn.dataset.index);
    if (btn.dataset.action === "delete") {
      removeMedia(index);
    } else {
      moveMedia(index, btn.dataset.action === "up" ? -1 : 1);
    }
  }

  // 提交自定义媒体
  async function submitMedia(event) {
    if (event) event.preventDefault();
    const url = ($.url ? $.url.value : "").trim();
    const type = $.type ? $.type.value : "";
    // 仅媒体格式为mp4(画质行可见)时才提交画质, 与后端校验口径一致
    const quality =
      $.qualityItem && !$.qualityItem.hidden && $.quality ? $.quality.value : "";
    const language = $.language ? $.language.value : "";
    if (!url) {
      setStatus("请填写媒体链接", "red");
      return;
    }
    // 后台忙碌时不提交, 与按钮禁用状态保持一致
    if (state.busy) {
      setStatus("后台正在处理自定义媒体, 请稍后再试", "orange");
      return;
    }
    setStatus("正在添加...", "orange");
    $.downloadBtn.disabled = true;
    if ($.url) $.url.disabled = true;
    if ($.urlClear) $.urlClear.disabled = true;
    setSelectDisabled($.type, true);
    setSelectDisabled($.quality, true);
    setSelectDisabled($.language, true);
    // 抓取媒体信息耗时数秒至数十秒, 期间一并禁用列表操作, 避免并发改动列表
    if ($.list) {
      $.list.querySelectorAll("button[data-action]").forEach((btn) => {
        btn.disabled = true;
      });
    }
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url,
          type: type,
          quality: quality,
          audio_track_language: language,
          rev: state.rev,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const err = new Error(data.error || `HTTP ${res.status}`);
        err.conflict = res.status === 409;
        err.data = data;
        throw err;
      }
      applyServerState(data);
      if (data.fail_reason) {
        // 条目已加入列表但状态为失败, 失败原因显示在提示区供用户排查
        // 保留链接不清空, 配好cookie后可直接再次点击下载以重新获取
        setStatus(
          `${data.message}, 但媒体信息获取失败: ${data.fail_reason}`,
          "red",
        );
      } else {
        // 重复媒体被忽略时列表未发生变化, 以橙色提示
        const color = data.added ? "green" : "orange";
        setStatus(`${data.message}, 当前共 ${data.count} 个自定义媒体`, color);
        // 添加成功后清空链接, 便于连续添加
        if ($.url) $.url.value = "";
      }
      await loadList();
    } catch (err) {
      // 版本冲突属预期情况(后台已更新列表), 不按错误处理
      if (await handleConflict(err)) return;
      console.error("添加自定义媒体失败:", err);
      setStatus(`添加失败: ${err.message}`, "red");
      // 请求期间列表按钮已被禁用, 重新读取列表以恢复首尾禁用等状态
      await loadList();
    } finally {
      // 结束时按忙碌标记决定是否恢复可用, 避免后台处理中误恢复按钮
      setBusy(state.busy);
    }
  }

  // 点击输入框右端的✕清空链接, 并把焦点交回输入框便于直接粘贴
  function clearUrl(event) {
    if (event) event.preventDefault();
    // 忙碌或提交期间输入框被禁用, 此时一并拒绝清空
    if (!$.url || $.url.disabled) return;
    $.url.value = "";
    $.url.focus();
  }

  function init() {
    if (!$.page || !$.form) {
      console.warn("添加自定义媒体页面元素未找到");
      return;
    }
    // 读取列表的同时按后端下发的字段定义(config_desc)构建三个下拉
    loadList();
    // 后端未下发desc时(请求失败或版本过旧), 稍后用兜底数据构建, 保证下拉始终可用
    setTimeout(() => applyDesc(null), 3000);
    if ($.form) $.form.addEventListener("submit", submitMedia);
    if ($.urlClear) $.urlClear.addEventListener("click", clearUrl);
    if ($.refreshBtn) $.refreshBtn.addEventListener("click", loadList);
    if ($.list) $.list.addEventListener("click", listClick);
    renderList([]);
    // 每分钟自动刷新列表, 切换到其他页面后自动跳过请求
    setInterval(autoRefresh, AUTO_REFRESH_MS);

    // 对外暴露页面切换钩子
    window.podflowCustomMedia = {
      // 切换回本页时清空上次的操作提示, 再重新读取列表
      onShow: () => {
        clearStatus();
        loadList();
      },
      reload: loadList,
    };
  }

  document.addEventListener("DOMContentLoaded", init);
})();
