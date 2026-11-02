// /templates/js/custom_select.js
// 自定义下拉组件（多页面共用：修改运行配置页各 select 字段、添加自定义媒体页的类型/画质）。
// 原生 <option> 无法在同一行内让英文正常色、中文灰色显示，故改用 button + ul 自绘下拉。
// 展示与写入配置的仍是候选 value，中文仅作前端灰显。样式见 config.css 的 .custom-select 块。
(function () {
  "use strict";

  // 判断字符串是否含中日韩字符（用于识别双语候选 label，如 category 的「Arts 艺术」）。
  function hasCjk(s) {
    return /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]/.test(
      String(s || ""),
    );
  }

  // 拆分「English 中文」式 label 为 { en, cn }：从首个中日韩字符起为中文部分（前端灰显）；
  // 无中文时 cn 为空串。存入配置的仍是候选 value（英文），与此拆分无关。
  function splitBilingualLabel(label) {
    const s = String(label === undefined || label === null ? "" : label);
    const m = s.match(
      /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]/,
    );
    if (!m) return { en: s, cn: "" };
    return { en: s.slice(0, m.index).trim(), cn: s.slice(m.index).trim() };
  }

  // 创建自定义下拉。参数：
  //   id      : 触发按钮的元素 id（供 label[for] 聚焦）
  //   options : [{ value, label }] 候选（label 支持双语「English 中文」）
  //   value   : 当前值（不在候选中时按钮原样展示并标注「无效值」，与原生 select 行为一致）
  //   eqStr   : 值比较函数（调用方决定类型口径）
  //   onPick  : 选中候选后的回调（写入配置等由调用方负责）
  // 返回包裹容器 div.custom-select，并附加：
  //   .value       与当前值保持同步，可按原生 select 的习惯直接读取
  //   .setDisabled(d) 等价原生 select 的 disabled（供忙碌/保存锁使用）
  function createCustomSelect({ id, options, value, eqStr, onPick }) {
    const wrapEl = document.createElement("div");
    wrapEl.className = "custom-select";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "custom-select-toggle";
    btn.id = id;

    const menu = document.createElement("ul");
    menu.className = "custom-select-menu";

    // 把「English 中文」渲染为：英文 span（正常色）+ 中文 span（灰色）；
    // 纯中文候选（如添加自定义媒体页的「音频/视频」）整词用正常色，不灰显。
    const renderBilingual = (container, labelText) => {
      container.textContent = "";
      const { en, cn } = splitBilingualLabel(labelText);
      const enSpan = document.createElement("span");
      enSpan.className = "custom-select-en";
      enSpan.textContent = en || cn;
      container.appendChild(enSpan);
      if (en && cn) {
        const cnSpan = document.createElement("span");
        cnSpan.className = "custom-select-cn";
        cnSpan.textContent = cn;
        container.appendChild(cnSpan);
      }
    };

    // 展示按钮回显当前值；不在候选中时原样展示以便发现问题（与原生 select 行为一致）
    const setValue = (val) => {
      // 供外部按原生 select 的习惯读取 .value（如 custom_media.js 的 $.type.value）
      wrapEl.value = val;
      const opt = options.find((o) => eqStr(o.value, val));
      if (opt) {
        renderBilingual(btn, opt.label);
      } else {
        btn.textContent = `${val === undefined || val === null ? "" : String(val)}（无效值）`;
      }
    };

    const closeMenu = () => wrapEl.classList.remove("open");

    options.forEach((opt) => {
      const li = document.createElement("li");
      li.className = "custom-select-option";
      renderBilingual(li, opt.label);
      if (eqStr(value, opt.value)) li.classList.add("selected");
      li.addEventListener("click", (e) => {
        e.stopPropagation();
        if (btn.disabled) return;
        setValue(opt.value);
        menu
          .querySelectorAll(".custom-select-option.selected")
          .forEach((x) => x.classList.remove("selected"));
        li.classList.add("selected");
        closeMenu();
        if (onPick) onPick(opt.value);
      });
      menu.appendChild(li);
    });

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (btn.disabled) return;
      const willOpen = !wrapEl.classList.contains("open");
      // 打开前先关闭其它已展开的自定义下拉
      document
        .querySelectorAll(".custom-select.open")
        .forEach((el) => el.classList.remove("open"));
      if (willOpen) wrapEl.classList.add("open");
    });

    setValue(value);
    wrapEl.setDisabled = (d) => {
      btn.disabled = d === true;
    };
    wrapEl.appendChild(btn);
    wrapEl.appendChild(menu);
    return wrapEl;
  }

  // 点击空白处关闭已展开的自定义下拉（下拉内部点击已 stopPropagation，不会误关）。
  // 组件为多页面共用，监听随组件注册一次即可。
  document.addEventListener("click", (e) => {
    document.querySelectorAll(".custom-select.open").forEach((el) => {
      if (!el.contains(e.target)) el.classList.remove("open");
    });
  });

  window.CustomSelect = {
    create: createCustomSelect,
    hasCjk: hasCjk,
    splitBilingualLabel: splitBilingualLabel,
  };
})();
