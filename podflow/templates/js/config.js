// /templates/js/config.js
// ==========================================================================
// 「修改运行配置」页面
// 1. 顶部三个并排选项：主配置 / YouTube 频道 / Bilibili 频道。
//    - 主配置：config_desc.main 中的全部配置（即 default_config 除两个频道列表外）
//    - 后两个选项：对应 channelid 字典，字典 key 即频道名称（可修改），
//      每个选项后有 ✕ 用于删除，第一个为空选项用于新增频道。
// 2. 所有修改只暂存于本地 state，由底部「保存配置」统一 POST 至 /saveconfig。
// 3. 「撤销」按钮位于保存左侧，每修改一次记一步，可逐步退回。
// 4. 字段的显示与校验（顺序、默认值、可选项、说明、类型、约束条件）唯一来源是
//    podflow/__init__.py 的 config_desc 字典（后端随 /getconfig 下发）：
//    添加/删除配置项时只需在 __init__.py 中同步维护 default_config 与 config_desc；
//    前端只渲染 config_desc 中定义的字段，配置里多余 key 不显示、不校验、不删改。
// 5. 规则类列表字段（如 title_change）通过其条目的 rules 声明元素字段定义所在的作用域
//    （顶层键名，如 title_change_rule）；作用域内以 "_" 开头的键为元数据（_meta），不渲染为字段。
// 6. 自动纠正同样来自 config_desc：trim_to 截取 / min_field 取不小于 / force 条件强制 /
//    null 按默认值补齐；mode_in 为 {key, values, msg}，依赖字段名(key)与候选值、提示完全来自
//    config_desc（不再默认依赖 mode）；select 选项比较统一按字符串，回写还原选项原始类型。
// 7. 嵌套配置对象（type=object）通过条目 schema 声明子字段定义所在的作用域（顶层键名，
//    同规则作用域），渲染/校验/纠正均按该作用域递归；未声明时沿用当前作用域。
//    保存前的自动纠正属于状态变更，会记录为一步可撤销的历史（撤销可回到纠正前的值）。
// 8. required 约束在递归校验（walk）中统一处理（主配置 / 频道 / 嵌套对象 / 规则字段），
//    并结合适用条件判断：websites 不适用于当前网站、when 条件未满足、mode_in 依赖字段取值
//    不在候选内时均不检查；key 缺失或值为空字符串 / null（未声明 allow_empty）都视为未填写；
//    字段的实时校验与保存前校验共用同一判断与提示（requiredMissing + requiredMsg），
//    页面即时提示与保存时阻止的原因一致；修改依赖字段后按编辑分组同步刷新其它受影响字段
//    （mode_in / err_if / when）的校验状态；数字输入为空时存 null（不产生 NaN，保证 JSON
//    快照与撤销历史一致）；无默认值的 int 为 null 时保持 null（不转成 ''），由校验按
//    「需为整数」或 required「未填写」提示。
// 9. 异常防御：无效正则 pattern / 非法 schema 引用 / 非数组 options 与 _meta 元数据
//    均跳过对应约束不中断校验渲染，并由 lintDesc 给出「配置描述无效」提示级警告（不静默跳过）；
//    rules 引用无效时该规则列表实际按只读处理（不渲染「添加规则」按钮、不渲染字段行、无删除入口），
//    使提示与实际行为一致；规则列表中 null、字符串等无效元素渲染为错误提示（可删除）并阻止保存
//    （后台会忽略该元素, 继续保存将丢失规则数据）；异常频道容器（字符串/数组）保留原值、锁定编辑
//    并阻止保存，绝不覆盖为 {}；频道重命名用 defineProperty 写入自有属性，__proto__ 等特殊键不丢
//    数据（选中/删除判断均用 hasOwnProperty）。
// 10. 保存响应采用明确协议（classifySaveResponse）：空响应体→成功；读取失败 / 非 JSON /
//     JSON null 等非对象→失败（绝不判成功）；完整配置→采用：要求频道容器均为字典、提交配置里
//     每个 config_desc.main 字段都在响应中存在、且提交的每个频道名称及其应有配置字段都在响应中
//     完整存在（部分回显 / 缺字段 / 只回部分频道的响应一律不算完整，避免误判成功）；
//     业务错误信封（error/err/success:false/status∈{error,fail...}）→失败并显示后台错误；
//     部分配置或无法识别结构→失败提示、不采用返回值、不重置本地配置与撤销历史。/getconfig
//     响应中的 config_desc / default_config 为协议元数据，加载与采用时均予以剥离，不会混入待保存配置。
// 11. select 候选值统一经 normalizeOptions 规整（仅接受数组；过滤 null / 缺 value 的无效对象，
//     避免崩溃或产生 undefined 候选）；候选声明有效性问题（options 缺失 / 非数组 / 空 / 全部无效）
//     由 selectOptionsIssue 统一判定，lintDesc 与字段校验共用同一提示：任何值（含空值）都无法校验，
//     必须明确提示而不是静默放过；按错误性质区分——描述缺陷→提示级（warn，不阻塞），
//     值不在有效候选内→错误级（error，阻止保存）。
// 12. 统一的保存态 state.saving：保存入口先检查 state.saving 防止重复调用造成并发保存请求；
//     保存期间禁用所有配置编辑、频道管理、撤销与重复提交，避免新修改被正在进行的旧请求覆盖；
//     失败时本地修改与撤销历史完整保留。
// 13. 显示/同步关系同样数据驱动：when_show = { key, value } 声明显示条件（仅当 owner[key] === value
//     时显示该字段，条件不满足时隐藏且与 when 一样视为字段未生效、跳过校验；依赖它的字段变更后
//     整页重渲染以应用显示/隐藏）；sync_key: true 声明该字段（如 title）是频道名称（字典 key）的来源
//     ——修改该字段（title）即把频道名称(key)同步为字段值；频道名称(key) 平时隐藏，仅当同步目标与
//     其它频道已有 key 重复（无法自动重命名）时显示冲突频道的 key 输入框供手动修改；
//     单独修改频道名称(key)不会反向同步该字段。新建频道该字段为空时以生成的 key 为初值。
// ==========================================================================
"use strict";

// ====================== 1. 配置常量 ======================
const CONFIG_CONST = {
  // 后端接口
  API: {
    GET_CONFIG: "/getconfig",
    SAVE_CONFIG: "/saveconfig",
  },
  // 三个并排选项
  MAIN_TAB: "main",
  CHANNEL_TABS: [
    {
      key: "channelid_youtube",
      label: "YouTube 频道",
      short: "YouTube",
      website: "youtube",
    },
    {
      key: "channelid_bilibili",
      label: "Bilibili 频道",
      short: "Bilibili",
      website: "bilibili",
    },
  ],

  TEXT: {
    LOADING: "正在加载配置...",
    LOAD_FAIL: "加载配置失败",
    SAVING: "正在保存配置...",
    SAVE_SUCCESS: "配置保存成功！",
    SAVE_FAIL: "保存失败",
    SAVE_BLOCKED: "存在不满足约束的配置，已阻止保存",
    SAVE_RESPONSE_INCOMPLETE:
      "保存响应未返回完整配置，无法确认保存结果（本地修改保留，未采用返回内容）",
    SAVE_RESPONSE_NONJSON:
      "保存响应不是有效 JSON，无法确认保存结果（本地修改保留）：",
    SAVE_RESPONSE_READ_FAIL:
      "保存响应读取失败，无法确认保存结果（本地修改保留）：",
    SAVE_RESPONSE_INVALID:
      "保存响应格式无效（需为完整配置对象），无法确认保存结果（本地修改保留）",
    EMPTY_CHANNEL: "暂无频道，点击上方选择「＋ 新建频道」添加",
    EMPTY_RULE: (label) => `暂无${label}，点击「添加规则」新建`,
    NEW_CHANNEL_PLACEHOLDER: "＋ 新建频道…",
    NEW_CHANNEL_NAME: (short) => `新${short}频道`,
    DELETE_CHANNEL_CONFIRM: (name) => `确定删除频道「${name}」吗？`,
    DELETE_RULE_CONFIRM: (idx) => `确定删除规则 ${idx + 1}？`,
    UNDO: "已退回上一步（还可撤销 {n} 步）",
    EDIT: "已修改（还可撤销 {n} 步）",
    ADD_CHANNEL: (name) => `已新增频道「${name}」，请填写频道 ID`,
    ADD_CHANNEL_WITH_ID: (name) =>
      `已新增频道「${name}」，已自动填入频道 ID，请确认后点击「保存配置」生效`,
    ADD_CHANNEL_NO_TEMPLATE: (label) =>
      `无法创建频道：缺少「${label}」的有效配置模板（config_desc 未定义该网站字段）`,
    RENAME_EMPTY: "频道名称不能为空",
    RENAME_DUPLICATE: (name) => `频道名称「${name}」已存在`,
  },
};

// ====================== 2. 工具函数 ======================
const ConfigUtils = {
  clone(obj) {
    return JSON.parse(JSON.stringify(obj));
  },

  isPlainObject(obj) {
    return obj !== null && typeof obj === "object" && !Array.isArray(obj);
  },

  isValidRegex(pattern) {
    try {
      new RegExp(pattern);
      return true;
    } catch (e) {
      return false;
    }
  },

  // 统一解包后端可能存在的 { response: ... } 结构
  unwrap(raw) {
    if (ConfigUtils.isPlainObject(raw) && "response" in raw)
      return raw.response;
    return raw;
  },
};

// 保存响应错误信封识别：HTTP 200 但响应体携带业务错误标记时，提取错误信息。
// 识别的标记（与后台约定的响应协议, 不涉及具体业务）：
//   error / err 非空、success === false、status|result|state ∈ {error, fail, failed}
// 注意：完整配置本身不会走此判断（裸回显配置优先按完整配置采用）。
function extractRespError(raw) {
  if (!ConfigUtils.isPlainObject(raw)) return null;
  if (raw.error) {
    return typeof raw.error === "string"
      ? raw.error
      : raw.error.message || JSON.stringify(raw.error);
  }
  if (typeof raw.err === "string" && raw.err) return raw.err;
  if (raw.success === false)
    return raw.message || raw.detail || "后台返回 success=false";
  const statusLike = ["status", "result", "state"]
    .map((k) => raw[k])
    .filter((v) => typeof v === "string")
    .map((v) => v.toLowerCase());
  if (statusLike.some((s) => s === "error" || s === "fail" || s === "failed")) {
    return raw.message || raw.detail || `后台返回状态：${statusLike.join("/")}`;
  }
  return null;
}

// 规整 select 候选值：仅接受数组；元素可为字符串或 { value, label }。
// 异常保护：options 非数组 → []；null/undefined、缺少 value 的无效对象 → 过滤掉，
// 避免生成 undefined 候选（导致 JSON 克隆崩溃或候选比较失真）。
function normalizeOptions(raw) {
  if (!Array.isArray(raw)) return [];
  const out = [];
  raw.forEach((o) => {
    if (o === null || o === undefined) return;
    if (typeof o === "object") {
      if (Object.prototype.hasOwnProperty.call(o, "value")) {
        out.push({
          value: o.value,
          label: o.label !== undefined ? String(o.label) : String(o.value),
        });
      }
    } else {
      out.push({ value: o, label: String(o) });
    }
  });
  return out;
}

// 判断字符串是否含中日韩字符、拆分双语 label 的 hasCjk / splitBilingualLabel
// 已移至共用组件文件 custom_select.js（CustomSelect.hasCjk 等），此处不再重复定义。

// select 条目的候选声明是否存在问题（缺失 / 非数组 / 空数组 / 全部无效）。
// 返回 null 表示候选声明有效；否则返回问题描述（lintDesc 与 entry 共用同一判断，保证提示一致）。
function selectOptionsIssue(entry) {
  if (!entry || entry.type !== "select") return null;
  if (
    !Object.prototype.hasOwnProperty.call(entry, "options") ||
    entry.options === undefined ||
    entry.options === null
  ) {
    return "options 缺失";
  }
  if (!Array.isArray(entry.options)) return "options 需为列表";
  if (normalizeOptions(entry.options).length === 0)
    return "options 为空或全部无效";
  return null;
}

// rules 引用是否为有效作用域：rules 为字符串且指向 config_desc 中的字典作用域
function rulesScopeValid(ruleScope) {
  return (
    typeof ruleScope === "string" &&
    ruleScope !== "" &&
    ConfigUtils.isPlainObject(schema.configDesc[ruleScope])
  );
}

// sync_key：字段值为空（未填 / 空串 / null）判断。该字段（如 title）是频道名称（字典 key）的来源。
function isEmptyKeyValue(v) {
  return v === undefined || v === "" || v === null;
}

// 返回 channel.<website> 作用域中声明了 sync_key 的字段名（如 title），无则返回 null。
// 该字段（title）是频道名称（字典 key）的来源：修改它即同步 key；新建频道该字段为空时以 key 为初值。
function keySyncField(website) {
  const defs = schema.configDesc.channel[website];
  if (!ConfigUtils.isPlainObject(defs)) return null;
  const keys = Object.keys(defs);
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    if (k.startsWith("_")) continue;
    const e = defs[k];
    if (e && typeof e === "object" && e.sync_key === true) return k;
  }
  return null;
}

// when_show 显示条件（{ key, value }）：仅当 owner[key] === value 时显示该字段。
// 结构非法（非对象 / 缺 key）视为未声明（不隐藏），由 lintDesc 提示；
// 条件不满足 → 隐藏且不校验（与 when 一样视为字段未生效）。
function whenShowHidden(entry, owner) {
  if (!entry || !ConfigUtils.isPlainObject(entry.when_show)) return false;
  const ws = entry.when_show;
  if (ws.key === undefined || ws.key === null) return false;
  return owner[ws.key] !== ws.value;
}

// 某作用域内是否有字段的 when_show 依赖目标 key：
// 依赖字段（如 media / BackwardUpdate）变更后需整页重渲染以应用显示/隐藏。
function scopeWhenShowDepends(scope, website, key) {
  const order = scopeFieldOrder(scope, website);
  return order.some((sk) => {
    const e = descEntry(scope, sk, website);
    return !!(
      e &&
      ConfigUtils.isPlainObject(e.when_show) &&
      e.when_show.key === key
    );
  });
}

// 实时应用某作用域内所有 force 强制规则（按字段定义顺序, 与保存时 normalize 的 force 一致）:
// 让编辑时的强制改值与保存时一致(所见即所得)。如关闭 InmainRSS 时立即把 DisplayRSSaddress
// 置为 True, 使其隐藏但值生效, 进而让依赖它的 QRcode 恢复显示。
function applyScopeForces(owner, scope, website) {
  if (!ConfigUtils.isPlainObject(owner)) return;
  scopeFieldOrder(scope, website).forEach((key) => {
    const e = descEntry(scope, key, website);
    if (!e || typeof e !== "object") return;
    const f = e.force;
    if (
      f &&
      typeof f === "object" &&
      f.when_key !== undefined &&
      Object.prototype.hasOwnProperty.call(f, "set") &&
      owner[f.when_key] === f.when_value
    ) {
      owner[key] = ConfigUtils.clone(f.set);
    }
  });
}

// 保存时移除被 when_show 隐藏的字段（隐藏的配置不提交到后台）：
// 对作用域内每个声明 when_show 的字段, 若条件不满足则从提交对象中删除该键。
// 条件对「未删除前」的对象求值（先判定全部、再统一删除），保证依赖链按生效值判断:
// 如 QRcode 依赖 DisplayRSSaddress, 而 DisplayRSSaddress 自身可能被 InmainRSS 隐藏,
// 此时 DisplayRSSaddress 已被 force 置为 True, QRcode 不应随之隐藏。
// 注意：仅作用于提交副本（finalData），不改动本地 state.config（值仍保留/由 force 纠正），
// 且后台 correct_config / correct_channelid 会对缺失字段按默认值兜底，不影响运行。
function stripHiddenInScope(obj, scope, website) {
  if (!ConfigUtils.isPlainObject(obj)) return;
  const toDelete = [];
  scopeFieldOrder(scope, website).forEach((key) => {
    const e = descEntry(scope, key, website);
    if (e && whenShowHidden(e, obj)) toDelete.push(key);
  });
  toDelete.forEach((key) => {
    delete obj[key];
  });
}

// 移除主配置与所有频道中被隐藏的字段（作用于提交副本）
function stripHiddenFields(cfg) {
  if (!ConfigUtils.isPlainObject(cfg)) return;
  stripHiddenInScope(cfg.main, "main", undefined);
  CONFIG_CONST.CHANNEL_TABS.forEach((tab) => {
    const map = cfg[tab.key];
    if (!ConfigUtils.isPlainObject(map)) return;
    Object.values(map).forEach((ch) =>
      stripHiddenInScope(ch, "channel", tab.website),
    );
  });
}

// required 结构是否被 returned 完整覆盖：递归检查普通对象的键；
// 数组要求仍为数组；基本类型只要键存在（由调用方检查）即视为完整。
function coverageOk(required, returned) {
  if (Array.isArray(required)) return Array.isArray(returned);
  if (ConfigUtils.isPlainObject(required)) {
    if (!ConfigUtils.isPlainObject(returned)) return false;
    return Object.keys(required).every(
      (k) =>
        Object.prototype.hasOwnProperty.call(returned, k) &&
        coverageOk(required[k], returned[k]),
    );
  }
  return true;
}

// 保存响应是否为「完整配置」的明确协议（不只看是否出现任意一个主配置字段）：
//   1) 解包后的值为字典；
//   2) 两个频道容器均为字典；
//   3) 提交配置中每个 config_desc.main 字段都必须在响应中存在；
//   4) 提交的每个频道名称及其应有配置字段（键结构）都必须在响应中完整存在
//      （部分回显 / 缺字段 / 只回部分频道的响应一律不算完整配置，避免被误判为保存成功）。
function isCompleteConfigResponse(saved, submitted) {
  if (
    !ConfigUtils.isPlainObject(saved) ||
    !ConfigUtils.isPlainObject(submitted)
  )
    return false;
  if (
    !CONFIG_CONST.CHANNEL_TABS.every((t) =>
      ConfigUtils.isPlainObject(saved[t.key]),
    )
  )
    return false;
  const submittedMain = schema.mainOrder.filter((k) =>
    Object.prototype.hasOwnProperty.call(submitted, k),
  );
  if (!submittedMain.length) return false;
  if (
    !submittedMain.every((k) => Object.prototype.hasOwnProperty.call(saved, k))
  )
    return false;
  // 频道完整性：提交的频道名及其配置字段必须在返回配置中完整存在
  return CONFIG_CONST.CHANNEL_TABS.every((tab) => {
    const subMap = submitted[tab.key];
    if (subMap === undefined || subMap === null) return true; // 未提交该容器，允许
    if (!ConfigUtils.isPlainObject(subMap)) return false; // 异常容器：无法确认完整
    const savedMap = saved[tab.key];
    return Object.keys(subMap).every(
      (chKey) =>
        Object.prototype.hasOwnProperty.call(savedMap, chKey) &&
        coverageOk(subMap[chKey], savedMap[chKey]),
    );
  });
}

// 保存响应分类（返回 { kind, message?, data? }）：
//   'ok'    — 空响应体：视为成功（兼容不回显内容的后台）
//   'adopt' — 完整配置：data 为解包后的配置对象
//   'error' — 失败：message 为原因（读取失败 / 非 JSON / 非对象 / 业务错误 / 非完整配置）
// 明确不把「读取失败」与「JSON null / 标量」当作成功。
function classifySaveResponse(rawText, submitted, readError) {
  if (readError) {
    return {
      kind: "error",
      message:
        CONFIG_CONST.TEXT.SAVE_RESPONSE_READ_FAIL + (readError.message || ""),
    };
  }
  if (
    rawText === null ||
    rawText === undefined ||
    String(rawText).trim() === ""
  ) {
    return { kind: "ok" };
  }
  const text = String(rawText);
  let body;
  try {
    body = JSON.parse(text);
  } catch (e) {
    return {
      kind: "error",
      message:
        CONFIG_CONST.TEXT.SAVE_RESPONSE_NONJSON +
        text.slice(0, 120) +
        (text.length > 120 ? "…" : ""),
    };
  }
  // JSON null / 数字 / 字符串 / 布尔等非对象 → 不是有效的配置确认
  if (body === null || typeof body !== "object") {
    return { kind: "error", message: CONFIG_CONST.TEXT.SAVE_RESPONSE_INVALID };
  }
  const saved = ConfigUtils.unwrap(body);
  const complete = isCompleteConfigResponse(saved, submitted);
  // 错误信封识别：包装信封（body 与解包结果不同层）时信封层错误标记优先；
  // 裸回显的完整配置不走此判断（避免配置字段名与协议键撞名时误判）
  let businessErr = saved !== body ? extractRespError(body) : null;
  if (!businessErr && !complete) {
    businessErr =
      extractRespError(body) ||
      (saved !== body ? extractRespError(saved) : null);
  }
  if (businessErr) return { kind: "error", message: businessErr };
  if (!complete)
    return {
      kind: "error",
      message: CONFIG_CONST.TEXT.SAVE_RESPONSE_INCOMPLETE,
    };
  return { kind: "adopt", data: saved };
}

// ====================== 3. 字段结构（由后端 config_desc 下发） ======================
// 与 podflow/__init__.py 的 config_desc 保持一致：字段顺序 / 默认值 / 候选选项 / 说明
// 全部来自该字典，由 /getconfig 在页面加载时填充。
const schema = {
  defaults: {}, // 主配置各字段默认值（config_desc.main[].default）
  mainOrder: [], // 主配置字段顺序（config_desc.main 定义顺序）
  channelOrder: {}, // { youtube: [..], bilibili: [..] }
  templates: {}, // 新建频道模板（config_desc.channel[].default）
  configDesc: { main: {}, channel: {} }, // 后端 config_desc 原样（含规则作用域如 title_change_rule）
};

// 取某字段在 config_desc 中的条目（无定义时返回 undefined）
// scope: 'main' = 主配置; 'channel' = 频道字段（需 website）;
// 其余顶层作用域名（如 'title_change_rule'）= 规则列表元素字段定义。
function descEntry(scope, key, website) {
  // 异常保护：作用域定义缺失或非字典时视为无字段定义（不崩溃）
  if (scope === "main") {
    const main = schema.configDesc.main;
    return ConfigUtils.isPlainObject(main) ? main[key] : undefined;
  }
  if (scope === "channel") {
    const ch = schema.configDesc.channel[website];
    return ConfigUtils.isPlainObject(ch) ? ch[key] : undefined;
  }
  const top = schema.configDesc[scope];
  return ConfigUtils.isPlainObject(top) ? top[key] : undefined;
}

// 取某作用域的字段显示/校验顺序：
//   'main'      → 主配置顺序（config_desc.main 定义顺序）
//   'channel'   → 频道字段顺序（config_desc.channel.<website> 定义顺序, 需 website）
//   其他顶层作用域（规则作用域 title_change_rule / 嵌套对象 schema 作用域）
//   → 该作用域自身定义顺序（以 "_" 开头的键为元数据如 _meta, 不参与渲染/校验）
function scopeFieldOrder(scope, website) {
  if (scope === "main") return schema.mainOrder;
  if (scope === "channel") return schema.channelOrder[website] || [];
  // 异常保护：作用域值为字符串/数组等非字典时按空作用域处理（不生成垃圾字段键）
  const obj = schema.configDesc[scope];
  return ConfigUtils.isPlainObject(obj)
    ? Object.keys(obj).filter((k) => !k.startsWith("_"))
    : [];
}

// ====================== 4. 约束校验（条件/类型/提示全部取自 config_desc） ======================
const ConfigRules = {
  err(msg) {
    return { level: "error", msg };
  },
  warn(msg) {
    return { level: "warn", msg };
  },

  isInt(v) {
    return typeof v === "number" && Number.isInteger(v);
  },

  // 取 select 字段的候选值（由 config_desc 的 options 派生, 元素可为字符串或 {value,label}）
  // 异常保护：options 非数组 / 含 null、无效对象时由 normalizeOptions 过滤，避免崩溃或产生 undefined 候选
  options(entry) {
    if (!entry) return [];
    return normalizeOptions(entry.options).map((o) => o.value);
  },

  // 按约束自动生成提示文本（条目未提供 msg/msg_err 时使用）
  msgFor(entry, opts) {
    if (entry.msg_err) return entry.msg_err;
    if (entry.msg) return entry.msg;
    if (entry.type === "int") {
      if (entry.min !== undefined && entry.max !== undefined)
        return `需为 ${entry.min} ~ ${entry.max} 的整数`;
      if (entry.min !== undefined)
        return entry.min === 1
          ? "需为大于 0 的整数"
          : `需为大于等于 ${entry.min} 的整数`;
      if (entry.max !== undefined) return `需为不超过 ${entry.max} 的整数`;
      return "需为整数";
    }
    if (entry.type === "select") return `需为：${opts.join(" / ")}`;
    return null;
  },

  // 统一的 required 提示文本（walk 保存前校验与字段实时校验共用，保证提示一致）
  requiredMsg(key, miss) {
    return miss === "empty" ? `${key} 未填写` : `缺少 ${key} 字段`;
  },

  // required 是否被违反：先判断字段当前是否适用，再判断缺失/空值
  //   websites — 不适用于当前网站时不检查
  //   when     — 条件不满足（字段未生效）时不检查
  //   mode_in  — 与值校验一致：依赖字段取值不在候选内时（字段未生效）不检查
  //   空值     — key 存在但值为 '' 或 null（未声明 allow_empty）视为未填写
  // 返回 null（不违反）| 'missing'（字段缺失）| 'empty'（值为空）
  requiredMissing(entry, owner, key, website) {
    if (!entry || entry.required !== true) return null;
    if (entry.websites && !entry.websites.includes(website)) return null;
    // when_show 显示条件：条件不满足（字段未生效/被隐藏）时不检查 required
    if (
      entry.when_show &&
      typeof entry.when_show === "object" &&
      entry.when_show.key !== undefined &&
      entry.when_show.key !== null &&
      owner[entry.when_show.key] !== entry.when_show.value
    )
      return null;
    if (
      entry.when &&
      typeof entry.when === "object" &&
      owner[entry.when.key] !== entry.when.value
    )
      return null;
    if (entry.mode_in && typeof entry.mode_in === "object") {
      const miVals = Array.isArray(entry.mode_in)
        ? entry.mode_in
        : Array.isArray(entry.mode_in.values)
          ? entry.mode_in.values
          : [];
      const miKey = Array.isArray(entry.mode_in)
        ? undefined
        : entry.mode_in.key;
      if (!miVals.some((x) => String(x) === String(owner[miKey]))) return null;
    }
    if (!(key in owner)) return "missing";
    const v = owner[key];
    return (v === "" || v === null) && entry.allow_empty !== true
      ? "empty"
      : null;
  },

  // 数据驱动单字段校验：ctx = { scope: 'main' | 'channel' | 规则作用域名(title_change_rule 等), website }
  // owner 为所在对象（主配置字典 / 单个频道字典 / 单个规则），key 为待校验字段。
  // 校验规则全部来自 config_desc 条目（type / min / max / pattern / min_length /
  // options / when / mode_in / websites / err_if / warn / msg / regex / required）。
  entry(ctx, owner, key) {
    const entry = descEntry(ctx.scope, key, ctx.website);
    if (!entry) return null;
    const v = owner[key];

    // 显示条件（when_show）：条件不满足（字段被隐藏/未生效）时不校验该字段
    if (
      entry.when_show &&
      typeof entry.when_show === "object" &&
      entry.when_show.key !== undefined &&
      entry.when_show.key !== null &&
      owner[entry.when_show.key] !== entry.when_show.value
    )
      return null;

    // 条件化校验（when）：仅当 owner[when.key] === when.value 时才校验该字段
    if (entry.when && owner[entry.when.key] !== entry.when.value) return null;

    // 适用网站限制（websites）：不适用于当前网站时跳过
    if (entry.websites && !entry.websites.includes(ctx.website)) return null;

    // 适用模式限制（mode_in，如 rule.url）：mode_in = {key, values, msg},
    // 依赖字段名与候选值、提示完全来自 config_desc；未声明依赖字段(key)时不猜不校验
    if (entry.mode_in) {
      const mi = entry.mode_in;
      // 异常保护：values 非数组时按空候选处理（不中断校验）
      const miValues = Array.isArray(mi)
        ? mi
        : Array.isArray(mi.values)
          ? mi.values
          : [];
      const miKey = mi.key;
      const inList =
        miKey !== undefined &&
        miKey !== null &&
        miValues.some((x) => String(x) === String(owner[miKey]));
      if (!inList) {
        if (v !== "" && v !== undefined && v !== null) {
          return this.warn(
            mi.msg || `该字段仅在 ${miValues.join(" / ")} 模式下有效`,
          );
        }
        return null;
      }
    }

    const opts = this.options(entry);
    // 校验失败时的级别：条目标记 warn 则仅提示，否则报错
    const fail = (msg) => (entry.warn ? this.warn(msg) : this.err(msg));
    switch (entry.type) {
      case "int": {
        if (!this.isInt(v)) return this.err("需为整数");
        if (entry.min !== undefined && v < entry.min)
          return this.err(this.msgFor(entry));
        if (entry.max !== undefined && v > entry.max)
          return this.err(this.msgFor(entry));
        return null;
      }
      case "bool":
        if (typeof v !== "boolean")
          return this.err("需为布尔值（true / false）");
        return null;
      case "select": {
        // 无效的配置描述（options 缺失 / 非数组 / 空数组 / 全部无效）：任何值（含空值）都无法校验，
        // 必须明确提示而不是静默放过。属描述缺陷 → 提示级（warn），不阻塞保存。
        const issue = selectOptionsIssue(entry);
        if (issue) {
          return this.warn(
            entry.msg ||
              `该选项字段的候选值未定义（config_desc ${issue}），无法校验候选值`,
          );
        }
        // 候选值与当前值统一按字符串比较, 兼容数字/字符串两种选项写法
        const valid = opts.some((o) => String(o) === String(v));
        if (!valid) {
          // err_if：校验失败时, 若条件成立(i.e. media 为 mp4)则报错并优先用 msg_err, 否则仅提示用 msg
          // 异常保护：err_if 缺少 key 时视为条件不成立（避免 undefined === undefined 误判）
          const errIf =
            entry.err_if &&
            entry.err_if.key !== undefined &&
            owner[entry.err_if.key] === entry.err_if.value;
          const m = errIf
            ? entry.msg_err || this.msgFor(entry, opts)
            : entry.msg || this.msgFor(entry, opts);
          if (entry.warn || (entry.err_if && !errIf)) return this.warn(m);
          return this.err(m);
        }
        return null;
      }
      case "url":
      case "str": {
        if (typeof v !== "string") return fail("需为文本");
        // allow_empty：空值视为合法（如 title_change_rule.url 未填写时）
        if (entry.allow_empty === true && v === "") return null;
        if (entry.min_length !== undefined && v.length < entry.min_length) {
          return fail(
            this.msgFor(entry) || `长度不能少于 ${entry.min_length} 位`,
          );
        }
        // pattern 异常保护：无效正则（如 '('）时跳过该约束, 不中断校验
        if (entry.pattern && ConfigUtils.isValidRegex(entry.pattern)) {
          const re = new RegExp(entry.pattern);
          if (!re.test(v)) return fail(this.msgFor(entry) || "格式不正确");
        }
        return null;
      }
      case "regex":
        if (v && !ConfigUtils.isValidRegex(v))
          return this.warn(this.msgFor(entry) || "正则表达式无效");
        return null;
      case "array":
        if (!Array.isArray(v))
          return this.err(this.msgFor(entry) || "需为列表");
        return null;
      case "object":
        // 嵌套配置对象：值本身需为字典（其子字段由条目声明的 schema 作用域递归校验）
        if (!ConfigUtils.isPlainObject(v))
          return this.err(this.msgFor(entry) || "需为字典");
        return null;
      default:
        return null;
    }
  },

  // ---- 保存前归一化（结构性纠正，规则全部来自 config_desc, 与 correct_config/correct_channelid 一致） ----
  normalize(cfg) {
    // 主配置与频道配置共用 normalizeScope（trim_to 截取 / null 按默认值兜底 /
    // min_field 取不小于 / force 条件强制 / 嵌套对象按 schema 作用域递归）
    this.normalizeScope(cfg, "main", undefined);
    CONFIG_CONST.CHANNEL_TABS.forEach((tab) => {
      const map = cfg[tab.key];
      // 缺失/为 null 的容器无数据可丢失，补空结构；
      // 异常容器（字符串/数组等）保留原值不覆盖，由 validateAll 报错阻止保存，避免数据丢失
      if (map === undefined || map === null) {
        cfg[tab.key] = {};
        return;
      }
      if (!ConfigUtils.isPlainObject(map)) return;
      Object.values(map).forEach((ch) => {
        if (!ConfigUtils.isPlainObject(ch)) return;
        this.normalizeScope(ch, "channel", tab.website);
      });
    });
  },

  // 按 config_desc 纠正一个字典对象（频道字段 / 嵌套配置对象共用）
  normalizeScope(obj, scope, website) {
    const desc =
      scope === "main"
        ? schema.configDesc.main
        : scope === "channel"
          ? schema.configDesc.channel[website]
          : schema.configDesc[scope];
    // 配置描述异常保护：作用域缺失或非字典时不做纠正
    if (!ConfigUtils.isPlainObject(desc)) return;
    Object.keys(desc).forEach((key) => {
      const e = desc[key];
      if (!e || typeof e !== "object") return;
      if (key in obj) {
        // null 按默认值纠正（与后台 default 兜底一致）；未声明 default 时：
        //   object → {}；int → 保持 null（不转成 '',由校验按「需为整数」提示）；其余 → ''
        if (obj[key] === null) {
          if (Object.prototype.hasOwnProperty.call(e, "default")) {
            obj[key] = ConfigUtils.clone(e.default);
          } else if (e.type === "object") {
            obj[key] = {};
          } else if (e.type !== "int") {
            obj[key] = "";
          }
        }
        // 规则类列表字段（type=array 且声明了 rules 作用域，如 title_change）统一为列表
        if (
          e.type === "array" &&
          typeof e.rules === "string" &&
          !Array.isArray(obj[key])
        ) {
          obj[key] = [obj[key]];
        }
        // trim_to：截取为 pattern 匹配到的部分（如 YouTube id 保留前 24 位）；
        // 无效正则跳过截取（异常保护）
        if (
          e.trim_to === "match" &&
          e.pattern &&
          ConfigUtils.isValidRegex(e.pattern) &&
          typeof obj[key] === "string"
        ) {
          const m = obj[key].match(new RegExp(e.pattern));
          if (m) obj[key] = m[0];
        }
        // min_field：int 值不小于另一字段（如 last_size 不小于 update_size）
        if (
          e.min_field &&
          this.isInt(obj[key]) &&
          this.isInt(obj[e.min_field])
        ) {
          obj[key] = Math.max(obj[key], obj[e.min_field]);
        }
        // 嵌套配置对象：子字段按条目声明的 schema 作用域递归纠正（schema 须为作用域名）
        if (
          typeof e.schema === "string" &&
          e.schema &&
          ConfigUtils.isPlainObject(obj[key])
        ) {
          this.normalizeScope(obj[key], e.schema, website);
        }
      }
      // force：满足条件时强制为指定值（InmainRSS 为 False 时 DisplayRSSaddress 变为 True）
      // 异常保护：force 结构不完整（非对象/缺 when_key/set）时跳过，避免生成 undefined
      if (
        e.force &&
        typeof e.force === "object" &&
        e.force.when_key !== undefined &&
        Object.prototype.hasOwnProperty.call(e.force, "set") &&
        obj[e.force.when_key] === e.force.when_value
      ) {
        obj[key] = ConfigUtils.clone(e.force.set);
      }
    });
  },

  // ---- 递归校验：单字段 / 规则类列表字段 / 嵌套配置对象, 定义与规则全部来自 config_desc ----
  // prefix 为提示前缀（如 [主配置] / [YouTube]）; path 为字段路径（如 youtube / youtube.nested_test）
  walk(prefix, path, obj, scope, website, errors, warns, push) {
    const order = scopeFieldOrder(scope, website);
    const mid = path ? `${path}.` : "";
    order.forEach((key) => {
      const e = descEntry(scope, key, website);
      if (!e) return;
      // required：结合适用条件（when / websites）判断，缺失或空字符串均视为未填写
      // （主配置 / 频道 / 嵌套对象统一在递归中处理）
      const miss = this.requiredMissing(e, obj, key, website);
      if (miss) {
        const parentHint = path || (scope === "main" ? "" : scope);
        errors.push(
          `${prefix}${parentHint ? " " + parentHint : ""}：${this.requiredMsg(key, miss)}`,
        );
        return;
      }
      if (!(key in obj)) return;
      // 规则类列表字段（type=array 且声明了 rules 作用域，如 title_change）：
      // 元素字段定义与校验规则取自其声明的顶层作用域（如 title_change_rule）
      if (e.type === "array" && typeof e.rules === "string") {
        const ruleDesc = schema.configDesc[e.rules] || {};
        const fieldKeys = Object.keys(ruleDesc).filter(
          (rk) => !rk.startsWith("_"),
        );
        const rules = obj[key];
        // 规则列表应为数组；不是数组时给出明确错误，而非静默跳过
        if (!Array.isArray(rules)) {
          errors.push(`${prefix} ${mid}${key}：需为列表（规则列表字段）`);
          return;
        }
        rules.forEach((r, i) => {
          const rulePath = `${mid}${key}[${i + 1}]`;
          if (!ConfigUtils.isPlainObject(r)) {
            // 无效规则元素（null / 字符串等）必须阻止保存：后台会忽略该元素,
            // 继续保存会造成规则数据丢失
            errors.push(
              `${prefix} ${rulePath}：规则数据无效（需为对象），请删除该规则后再保存`,
            );
            return;
          }
          fieldKeys.forEach((rk) => {
            const fe = ruleDesc[rk];
            if (!fe) return;
            // 规则字段的 required 约束同样生效（结合 when / websites 适用条件与空值判断）
            const rMiss = this.requiredMissing(fe, r, rk, website);
            if (rMiss) {
              errors.push(
                `${prefix} ${rulePath}：${this.requiredMsg(rk, rMiss)}`,
              );
              return;
            }
            if (!(rk in r)) return;
            const res = this.entry({ scope: e.rules, website }, r, rk);
            if (res)
              push(
                res.level === "error" ? errors : warns,
                prefix,
                `${rulePath} ${rk}`,
                res,
              );
          });
          // 元素必备结构由作用域 _meta 声明（require / any_of / message）
          // 异常保护：require / any_of 非数组时按未声明处理, 不中断校验
          const meta = ruleDesc._meta;
          if (meta) {
            const missingReq = (
              Array.isArray(meta.require) ? meta.require : []
            ).filter((rk) => !(rk in r));
            const missingAny = (
              Array.isArray(meta.any_of) ? meta.any_of : []
            ).filter(
              (group) => !(Array.isArray(group) && group.some((rk) => rk in r)),
            );
            if (missingReq.length || missingAny.length) {
              warns.push(
                `${prefix} ${rulePath}：${meta.message || "规则字段不完整，可能被后台忽略"}`,
              );
            }
          }
        });
        return;
      }
      const fieldPath = `${mid}${key}`;
      const res = this.entry({ scope, website }, obj, key);
      if (res)
        push(res.level === "error" ? errors : warns, prefix, fieldPath, res);
      // 嵌套配置对象：子字段按条目声明的 schema 作用域递归校验（schema 须为作用域名）
      if (
        ConfigUtils.isPlainObject(obj[key]) &&
        typeof e.schema === "string" &&
        e.schema
      ) {
        this.walk(
          prefix,
          fieldPath,
          obj[key],
          e.schema,
          website,
          errors,
          warns,
          push,
        );
      }
    });
  },

  // ---- 配置描述体检：无效的 schema / rules / options / pattern / mode_in 声明给出提示级警告
  // （不阻塞保存），避免对应校验被静默跳过而漏掉问题 ----
  lintDesc() {
    const out = [];
    const checkScope = (scopeName, desc) => {
      if (!ConfigUtils.isPlainObject(desc)) return;
      Object.keys(desc).forEach((key) => {
        if (key.startsWith("_")) return;
        const e = desc[key];
        if (!e || typeof e !== "object") return;
        const where = `${scopeName}.${key}`;
        if (
          e.schema !== undefined &&
          !(
            typeof e.schema === "string" &&
            ConfigUtils.isPlainObject(schema.configDesc[e.schema])
          )
        ) {
          out.push(
            `配置描述无效：${where} 的 schema「${e.schema}」未指向有效作用域，已跳过子字段校验`,
          );
        }
        if (e.rules !== undefined && !rulesScopeValid(e.rules)) {
          out.push(
            `配置描述无效：${where} 的 rules「${e.rules}」未指向有效作用域，该列表已按只读处理`,
          );
        }
        if (e.type === "select") {
          const optIssue = selectOptionsIssue(e);
          if (optIssue)
            out.push(`配置描述无效：${where} 的 ${optIssue}，无法校验候选值`);
        }
        if (e.pattern !== undefined && !ConfigUtils.isValidRegex(e.pattern)) {
          out.push(
            `配置描述无效：${where} 的 pattern 不是有效正则，已跳过格式校验`,
          );
        }
        if (
          e.mode_in !== undefined &&
          !Array.isArray(e.mode_in) &&
          !(typeof e.mode_in === "object" && Array.isArray(e.mode_in.values))
        ) {
          out.push(
            `配置描述无效：${where} 的 mode_in.values 需为列表，已跳过该约束`,
          );
        }
        if (
          e.when_show !== undefined &&
          !(
            ConfigUtils.isPlainObject(e.when_show) &&
            e.when_show.key !== undefined &&
            e.when_show.key !== null
          )
        ) {
          out.push(
            `配置描述无效：${where} 的 when_show 需为 { key, value } 对象，已跳过显示条件`,
          );
        }
        if (e.sync_key !== undefined && e.sync_key !== true) {
          out.push(`配置描述无效：${where} 的 sync_key 需为 true，已忽略`);
        }
      });
    };
    checkScope("main", schema.configDesc.main);
    if (ConfigUtils.isPlainObject(schema.configDesc.channel)) {
      checkScope("channel.youtube", schema.configDesc.channel.youtube);
      checkScope("channel.bilibili", schema.configDesc.channel.bilibili);
    }
    Object.keys(schema.configDesc).forEach((k) => {
      if (k === "main" || k === "channel" || k.startsWith("_")) return;
      checkScope(k, schema.configDesc[k]);
    });
    return out;
  },

  // ---- 全量校验，返回 { errors, warns }（只校验 config_desc 中定义的字段） ----
  validateAll(cfg) {
    const errors = [];
    const warns = [];
    const push = (list, prefix, key, res) =>
      list.push(`${prefix} ${key}：${res.msg}`);
    // 配置描述体检（提示级）：schema/rules/options/pattern/mode_in 声明无效时明确提示
    this.lintDesc().forEach((w) => warns.push(w));

    // 主配置：仅校验 config_desc.main 中定义且存在于配置中的字段
    this.walk("[主配置]", "", cfg, "main", undefined, errors, warns, push);

    // 频道配置
    CONFIG_CONST.CHANNEL_TABS.forEach((tab) => {
      const map = cfg[tab.key];
      // 容器缺省（undefined / null）允许（normalize 会补空结构, 后台按空处理）
      if (map === undefined || map === null) return;
      if (!ConfigUtils.isPlainObject(map)) {
        // 异常容器（字符串/数组等）：明确报错阻止保存，绝不覆盖为 {}，避免数据丢失
        errors.push(
          `[${tab.short}] ${tab.key}：配置需为字典（已阻止保存，避免数据丢失）`,
        );
        return;
      }
      const chKeys = Object.keys(map);
      if (!chKeys.length) return;

      chKeys.forEach((chKey) => {
        const prefix = `[${tab.short}]`;
        if (!chKey.trim()) errors.push(`${prefix} 存在空的频道名称`);
        const ch = map[chKey];
        if (!ConfigUtils.isPlainObject(ch)) {
          errors.push(`${prefix} ${chKey}：配置需为字典`);
          return;
        }
        // 递归校验字段 / 规则列表 / 嵌套配置对象（required 缺失等约束统一在 walk 中处理）
        this.walk(
          prefix,
          chKey,
          ch,
          "channel",
          tab.website,
          errors,
          warns,
          push,
        );
      });
    });

    return { errors, warns };
  },
};

// ====================== 5. DOM 公共工具 ======================
let fieldSeq = 0;
const DomHelper = {
  expandedPaths: new Set(),

  createBtn(text, cls, clickFn) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = text;
    btn.classList.add("config-button", cls);
    btn.addEventListener("click", clickFn);
    return btn;
  },

  createTip(text, isItalic = true, color = "var(--secondary-text)") {
    const p = document.createElement("p");
    p.textContent = text;
    p.style.color = color;
    if (isItalic) p.style.fontStyle = "italic";
    p.style.marginLeft = "10px";
    return p;
  },

  createCollapsibleSection(path, titleText) {
    const section = document.createElement("div");
    section.className = "collapsible-section";
    section.dataset.path = path;

    const header = document.createElement("div");
    header.className = "collapsible-header";
    header.tabIndex = 0;
    header.setAttribute("role", "button");

    const content = document.createElement("div");
    const isExpanded = this.expandedPaths.has(path);
    content.className = `collapsible-content${isExpanded ? "" : " hidden"}`;
    header.classList.toggle("expanded", isExpanded);
    header.setAttribute("aria-expanded", String(isExpanded));
    header.innerHTML = `<span class="section-title"></span>`;
    header.querySelector(".section-title").textContent = titleText;

    const toggle = (e) => {
      if (e.target.closest("button")) return;
      const isHide = content.classList.toggle("hidden");
      header.classList.toggle("expanded", !isHide);
      header.setAttribute("aria-expanded", String(!isHide));
      if (isHide) this.expandedPaths.delete(path);
      else this.expandedPaths.add(path);
    };
    header.addEventListener("click", toggle);
    header.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle(e);
      }
    });

    section.append(header, content);
    return { section, header, content };
  },
};

// ====================== 6. 主逻辑 ======================
document.addEventListener("DOMContentLoaded", () => {
  const $ = {
    container: document.getElementById("configContainer"),
    tabs: Array.from(document.querySelectorAll("#configTabs .config-tab")),
    refreshBtn: document.getElementById("refreshConfigBtn"),
    undoBtn: document.getElementById("undoConfigBtn"),
    saveBtn: document.getElementById("saveConfigBtn"),
    status: document.getElementById("configStatus"),
  };

  // 页面状态：config = 暂存中的配置；history = 撤销快照（每修改一次记一步）
  const state = {
    config: null,
    tab: CONFIG_CONST.MAIN_TAB,
    selected: {}, // 各 channelid 选项当前选中的 key
    history: [],
    historyIndex: -1,
    keyConflicts: {}, // { [tabKey]: Set<channelKey> } 频道名称(key)与其它频道重复的冲突标记
    saving: false, // 保存进行中：禁止编辑 / 频道管理 / 撤销 / 重复提交
  };
  const MAX_HISTORY = 200;

  // 字段行注册表：以"编辑分组"（main / 频道 / 规则元素 / 嵌套对象）为单位记录当前渲染的行，
  // 供某个字段变更后同步刷新同组内其它受影响字段（mode_in / when / err_if 依赖）的校验状态
  const fieldGroups = {};

  // ---------- 频道名称(key) 冲突标记 ----------
  // sync_key 字段（title）修改后同步频道名称(key)时，若目标 key 与其它频道重复则无法自动重命名，
  // 此时标记冲突：渲染层据此显示该频道的 key 输入框供手动修改；手动改 key 后清除。
  function setKeyConflict(tabKey, key) {
    if (!state.keyConflicts[tabKey]) state.keyConflicts[tabKey] = new Set();
    state.keyConflicts[tabKey].add(key);
  }

  function clearKeyConflict(tabKey, key) {
    const set = state.keyConflicts[tabKey];
    if (set) set.delete(key);
  }

  function isKeyConflict(tabKey, key) {
    const set = state.keyConflicts[tabKey];
    return !!(set && set.has(key));
  }

  function clearAllKeyConflicts() {
    state.keyConflicts = {};
  }

  // 结构同步源：由后端随 /getconfig 下发 podflow/__init__.py 的 config_desc（含默认值/选项/说明）。
  // 添加/删除配置项时, 在 __init__.py 中同步维护 default_config 与 config_desc 即可自动同步前端。
  function buildSchema(configDesc) {
    if (!ConfigUtils.isPlainObject(configDesc)) return;
    schema.configDesc = {
      main: ConfigUtils.isPlainObject(configDesc.main) ? configDesc.main : {},
      channel: {
        youtube:
          ConfigUtils.isPlainObject(configDesc.channel) &&
          ConfigUtils.isPlainObject(configDesc.channel.youtube)
            ? configDesc.channel.youtube
            : {},
        bilibili:
          ConfigUtils.isPlainObject(configDesc.channel) &&
          ConfigUtils.isPlainObject(configDesc.channel.bilibili)
            ? configDesc.channel.bilibili
            : {},
      },
    };
    // 其余顶层键为规则作用域（如 title_change_rule）：规则列表元素字段定义, 原样收集
    Object.keys(configDesc).forEach((k) => {
      if (k === "main" || k === "channel") return;
      schema.configDesc[k] = ConfigUtils.isPlainObject(configDesc[k])
        ? configDesc[k]
        : {};
    });

    // 主配置：顺序 = config_desc.main 定义顺序, 默认值 = 各条目 default（无 default 的如 address 不补齐）
    schema.mainOrder = Object.keys(schema.configDesc.main);
    schema.defaults = {};
    Object.keys(schema.configDesc.main).forEach((k) => {
      const entry = schema.configDesc.main[k];
      if (!entry || !Object.prototype.hasOwnProperty.call(entry, "default"))
        return;
      schema.defaults[k] = ConfigUtils.clone(entry.default);
    });

    // 频道：字段顺序与新建频道模板（默认值）取自 config_desc.channel.<website>
    CONFIG_CONST.CHANNEL_TABS.forEach((tab) => {
      const defs = schema.configDesc.channel[tab.website] || {};
      schema.channelOrder[tab.website] = Object.keys(defs);
      schema.templates[tab.website] = {};
      Object.keys(defs).forEach((k) => {
        const entry = defs[k];
        if (!entry || !Object.prototype.hasOwnProperty.call(entry, "default"))
          return;
        schema.templates[tab.website][k] = ConfigUtils.clone(entry.default);
      });
    });
  }

  // 按作用域取字段说明（main / channel / rule，来自 config_desc 的 desc）
  function getFieldHint(key, ctx) {
    const entry = descEntry(ctx.scope, key, ctx.website);
    if (entry && entry.desc) return entry.desc;
    return "";
  }

  // 取字段作用域默认值：优先使用 config_desc 声明的 default, 未声明时按类型给类型合理的占位
  // （仅用于"新增规则"模板；新建频道/补齐字段只取声明了 default 的条目, 不凭空生成值）
  function fallbackValue(entry) {
    if (entry && Object.prototype.hasOwnProperty.call(entry, "default")) {
      return ConfigUtils.clone(entry.default);
    }
    if (!entry) return "";
    switch (entry.type) {
      case "bool":
        return false;
      case "int":
        return null; // 无默认时先空, 保存时由 normalize 按需兜底
      case "array":
        return [];
      case "object":
        return {};
      case "select": {
        const opts = ConfigRules.options(entry);
        return opts.length ? ConfigUtils.clone(opts[0]) : "";
      }
      default:
        return ""; // str / url / regex
    }
  }

  // 用 default_config 补齐缺失项：主配置缺的字段填默认值（仅 config_desc 有 default 的条目）；
  // 老频道缺的字段用示例频道补齐，保证各频道显示的顺序与数量一致（与 correct_channelid 行为一致）
  function applyDefaults(cfg) {
    schema.mainOrder.forEach((k) => {
      if (
        !(k in cfg) &&
        Object.prototype.hasOwnProperty.call(schema.defaults, k)
      ) {
        cfg[k] = ConfigUtils.clone(schema.defaults[k]);
      }
    });
    CONFIG_CONST.CHANNEL_TABS.forEach((tab) => {
      const map = cfg[tab.key];
      if (!ConfigUtils.isPlainObject(map)) return;
      const defs = schema.templates[tab.website] || {};
      Object.values(map).forEach((ch) => {
        if (!ConfigUtils.isPlainObject(ch)) return;
        Object.keys(defs).forEach((k) => {
          if (!(k in ch)) ch[k] = ConfigUtils.clone(defs[k]);
        });
      });
    });
    return cfg;
  }

  // ---------- 撤销历史 ----------
  function resetHistory() {
    state.history = state.config ? [ConfigUtils.clone(state.config)] : [];
    state.historyIndex = state.history.length - 1;
    updateActionButtons();
  }

  // 提交一次修改 = 记一步
  function commit(mutate, options = {}) {
    if (!state.config) return;
    // 保存进行中：忽略一切编辑提交，避免新修改被正在进行的旧请求覆盖
    if (state.saving) return;
    if (typeof mutate === "function") mutate(state.config);
    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push(ConfigUtils.clone(state.config));
    if (state.history.length > MAX_HISTORY) state.history.shift();
    state.historyIndex = state.history.length - 1;
    updateActionButtons();
    // 修改后实时刷新「还可撤销 N 步」; 具体场景(如新增频道)随后设置的提示会覆盖此条
    setStatus(
      CONFIG_CONST.TEXT.EDIT.replace("{n}", state.historyIndex),
      "muted",
    );
    if (options.render !== false) render();
  }

  function undo() {
    if (state.saving) return;
    if (state.historyIndex <= 0) return;
    state.historyIndex -= 1;
    state.config = ConfigUtils.clone(state.history[state.historyIndex]);
    clearAllKeyConflicts();
    updateActionButtons();
    render();
    setStatus(
      CONFIG_CONST.TEXT.UNDO.replace("{n}", state.historyIndex),
      "muted",
    );
  }

  function updateActionButtons() {
    const loaded = !!state.config;
    if ($.undoBtn)
      $.undoBtn.disabled = state.saving || !loaded || state.historyIndex <= 0;
    $.saveBtn.disabled = state.saving || !loaded;
  }

  // 保存进行中禁用页面内所有编辑/频道管理控件（开始保存时与每次渲染后都会调用）
  function applySavingLock() {
    if (!state.saving) return;
    $.container
      .querySelectorAll("input, select, textarea, button")
      .forEach((el) => {
        el.setAttribute("disabled", "disabled");
      });
  }

  function setStatus(text, tone = "muted") {
    const colors = {
      success: "var(--accent-green)",
      error: "var(--accent-red)",
      warn: "var(--accent-amber)",
      saving: "orange",
      muted: "var(--secondary-text)",
    };
    $.status.textContent = text;
    $.status.style.color = colors[tone] || colors.muted;
  }

  // 在状态栏下方显示警告明细（保存成功时若有提示则逐条列出, 便于用户定位问题字段）
  function renderWarnings(list) {
    clearWarnings();
    if (!list || !list.length) return;
    const box = document.createElement("div");
    box.id = "configWarns";
    box.className = "config-warns";
    const title = document.createElement("div");
    title.className = "config-warns-title";
    title.textContent = `${list.length} 条提示：`;
    box.appendChild(title);
    list.forEach((w) => {
      const item = document.createElement("div");
      item.className = "config-warns-item";
      item.textContent = w;
      box.appendChild(item);
    });
    const statusEl = $.status;
    statusEl.parentNode.insertBefore(box, statusEl.nextSibling);
  }

  function clearWarnings() {
    const old = document.getElementById("configWarns");
    if (old && old.parentNode) old.parentNode.removeChild(old);
  }

  // ---------- 字段规格 ----------
  function getSpec(key, value, ctx) {
    const entry = descEntry(ctx.scope, key, ctx.website);
    // 只读字段（config_desc 中 readonly: true, 如自动生成的 address）
    if (entry && entry.readonly) return { kind: "text", readOnly: true };
    if (!entry) {
      // 兜底（正常情况下渲染的字段都来自 config_desc，不会走到这里）
      if (typeof value === "boolean") return { kind: "bool" };
      if (typeof value === "number") return { kind: "int" };
      if (Array.isArray(value)) return { kind: "readonly-json" };
      return { kind: "text" };
    }
    switch (entry.type) {
      case "bool":
        return { kind: "bool" };
      case "int":
        return { kind: "int" };
      // 异常保护：options 非数组或含无效元素时由 normalizeOptions 规整（不中断渲染）
      case "select":
        return { kind: "select", options: normalizeOptions(entry.options) };
      case "url":
        return { kind: "url" };
      case "array":
        return { kind: "readonly-json", readOnly: true };
      case "object":
        return { kind: "readonly-json", readOnly: true };
      default:
        return { kind: "text" }; // str / regex
    }
  }

  // 字段实时校验：required 与保存前校验使用同一套判断与提示（requiredMissing + requiredMsg），
  // 保证页面即时提示与保存时阻止的原因一致
  function getFieldError(key, owner, ctx) {
    const entry = descEntry(ctx.scope, key, ctx.website);
    const miss = ConfigRules.requiredMissing(entry, owner, key, ctx.website);
    if (miss)
      return { level: "error", msg: ConfigRules.requiredMsg(key, miss) };
    return ConfigRules.entry(ctx, owner, key);
  }

  function refreshFieldState(wrap, key, owner, ctx) {
    const errBox = wrap.querySelector(".field-error");
    // 匹配原生 input/select 与自定义双语下拉的切换按钮，使校验高亮同样作用于自定义下拉
    const input = wrap.querySelector("input, select, .custom-select-toggle");
    if (!errBox || !input) return;
    const res = ctx.readOnly ? null : getFieldError(key, owner, ctx);
    if (!res) {
      errBox.textContent = "";
      errBox.classList.remove("show", "warn");
      input.classList.remove("field-input-error");
      return;
    }
    errBox.textContent = res.msg;
    errBox.classList.add("show");
    errBox.classList.toggle("warn", res.level !== "error");
    input.classList.toggle("field-input-error", res.level === "error");
  }

  // 同步刷新同一编辑分组内所有字段行的校验状态：
  // 某个字段变更后（如 mode / media / BackwardUpdate 被修改），依赖它的其它字段
  // （mode_in / err_if / when 约束）的错误提示立即更新，无需整页重建
  function refreshGroup(groupId) {
    const rows = fieldGroups[groupId];
    if (!rows) return;
    rows.forEach((row) =>
      refreshFieldState(row.wrap, row.key, row.owner, row.ctx),
    );
  }

  // ---------- 通用字段行 ----------
  // 自定义下拉工厂 createCustomSelect 已移至共用组件文件 custom_select.js（window.CustomSelect），
  // 供本页全部 select 字段与「添加自定义媒体」页的类型/画质下拉共用，样式见 config.css。
  function buildFieldRow(key, value, owner, ctx) {
    const wrap = document.createElement("div");
    wrap.className = "config-item";

    const spec = getSpec(key, value, ctx);
    const readOnly = !!spec.readOnly;

    // 注册到所在编辑分组，供依赖字段变更后同步刷新本行校验状态
    if (ctx.group && !readOnly) {
      fieldGroups[ctx.group] = fieldGroups[ctx.group] || [];
      fieldGroups[ctx.group].push({ wrap, key, owner, ctx });
    }

    // 标签 + 配置说明
    const labelCell = document.createElement("div");
    labelCell.className = "field-label";
    const inputId = `config-field-${++fieldSeq}`;
    const label = document.createElement("label");
    label.htmlFor = inputId;
    label.textContent = `${key}:`;
    labelCell.appendChild(label);
    const hintText = getFieldHint(key, ctx);
    if (hintText) {
      const hint = document.createElement("p");
      hint.className = "field-hint";
      hint.textContent = hintText;
      labelCell.appendChild(hint);
    }
    wrap.appendChild(labelCell);

    let input;
    let stepInt = null; // int 字段步进回调（±1），构建后由行内 +/- 按钮使用

    const onCommit = (renderAfter) => {
      if (readOnly) return;
      // 实时应用依赖本作用域的 force 强制改值（如关闭 InmainRSS 时把 DisplayRSSaddress
      // 置 True），使其与保存时 normalize 一致；随后的重渲染应用显示/隐藏
      applyScopeForces(owner, ctx.scope, ctx.website);
      // 依赖字段（when_show.key 指向本字段，如 media / BackwardUpdate）变更后，
      // 整页重渲染以应用相关字段的显示/隐藏（仅刷新校验状态无法隐藏/恢复行）
      if (scopeWhenShowDepends(ctx.scope, ctx.website, key)) {
        commit({}, { render: true });
      } else {
        commit({}, { render: !!renderAfter });
      }
      // 刷新本字段及同组其它依赖字段（mode_in / err_if / when）的校验状态
      refreshGroup(ctx.group);
    };

    if (spec.kind === "bool") {
      input = document.createElement("input");
      input.type = "checkbox";
      input.checked = value === true;
      input.addEventListener("change", () => {
        if (state.saving) return;
        owner[key] = input.checked;
        onCommit(false);
      });
    } else if (spec.kind === "select") {
      // spec.options 已是规整后的 [{value,label}]（缺失/无效候选由 normalizeOptions 过滤）。
      // 统一使用自定义下拉组件（与 category 相同的外观与交互，英文正常色、中文灰显，
      // 纯英文候选仅显示 value）；写入配置的始终是候选 value（保留原始类型）。
      const eqStr = (a, b) => String(a) === String(b);
      input = CustomSelect.create({
        id: inputId,
        options: spec.options || [],
        value,
        eqStr,
        onPick: (val) => {
          if (state.saving) return;
          owner[key] = ConfigUtils.clone(val);
          onCommit(false);
        },
      });
    } else if (spec.kind === "readonly-json") {
      input = document.createElement("input");
      input.type = "text";
      input.value = JSON.stringify(value);
      input.addEventListener("change", () => refreshGroup(ctx.group));
    } else {
      input = document.createElement("input");
      let intEntry = null;
      if (spec.kind === "int") {
        input.type = "number";
        input.step = "1";
        input.value =
          value === undefined || value === null || Number.isNaN(value)
            ? ""
            : value;
        // 条目约束（min/max）供步进按钮钳制数值
        intEntry = descEntry(ctx.scope, key, ctx.website);
      } else if (spec.kind === "url") {
        input.type = "url";
        input.placeholder = "https://";
        input.value =
          value === undefined || value === null ? "" : String(value);
      } else {
        input.type = "text";
        input.value =
          value === undefined || value === null ? "" : String(value);
      }
      // 应用输入值并走统一提交流程（change 事件与 int 步进按钮共用）
      const applyValue = () => {
        if (readOnly || state.saving) return;
        if (spec.kind === "int") {
          // 空输入存 null（而非 NaN）：JSON 快照/撤销历史里 NaN 会被序列化为 null,
          // 造成 live 值与快照不一致；存 null 后渲染保持一致, 保存时由 normalize 按默认值兜底
          owner[key] = input.value.trim() === "" ? null : Number(input.value);
        } else {
          owner[key] = input.value;
        }
        // sync_key：该字段（如 title）是频道名称(key)的来源，修改后把 key 同步为字段值。
        // 同步可能重命名 key 或产生冲突（需显示 key 输入框），必须整页重渲染以反映这些变化
        const entrySync = descEntry(ctx.scope, key, ctx.website);
        const isSyncField = !!(
          entrySync &&
          entrySync.sync_key === true &&
          ctx.tabKey &&
          ctx.ownerKey
        );
        if (isSyncField) {
          syncChannelKeyFromField(ctx.tabKey, ctx.ownerKey, owner[key]);
        }
        onCommit(isSyncField);
      };
      input.addEventListener("change", applyValue);
      if (spec.kind === "int") {
        // 按约束钳制：越界时停在 min/max 边界（无约束原样返回）
        const clampInt = (n) => {
          if (intEntry && intEntry.min !== undefined && n < intEntry.min)
            return intEntry.min;
          if (intEntry && intEntry.max !== undefined && n > intEntry.max)
            return intEntry.max;
          return n;
        };
        // 步进：每次 ±1；空/非法输入从 0 起步
        stepInt = (delta) => {
          if (readOnly || state.saving) return;
          const cur = Number(input.value);
          input.value = clampInt((Number.isFinite(cur) ? cur : 0) + delta);
          applyValue();
        };
      }
    }

    // 自定义下拉（div.custom-select）：id 与样式类已在工厂内设好（供 label 聚焦），
    // 故此处不再重复赋 id / 加样式类；其余控件按类型补齐样式类
    const isCustomSelect = input.classList.contains("custom-select");
    if (!isCustomSelect) input.id = inputId;
    input.dataset.field = key;
    if (readOnly && !isCustomSelect) input.readOnly = true;
    if (!isCustomSelect && spec.kind !== "bool")
      input.classList.add("config-input-text");

    // int 字段：输入框内右侧嵌入 +/- 步进按钮（+ 加 1 / - 减 1），
    // 样式参照变量查询页框内复制/清除按钮（index.css .debug-box-btn）。
    // 图形用 SVG 而非文字字形：不同字体的 + / - 墨迹在 em 盒中的高度不一致
    // （- 的墨迹中心比 + 低约 1px），会导致上下看起来没有居中
    if (spec.kind === "int" && stepInt) {
      const holder = document.createElement("div");
      holder.className = "int-stepper";
      holder.appendChild(input);
      const ICONS = {
        up: '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="M6 2v8M2 6h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" fill="none"/></svg>',
        down: '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="M2 6h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" fill="none"/></svg>',
      };
      [
        ["up", 1],
        ["down", -1],
      ].forEach(([action, delta]) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `int-stepper-btn int-stepper-${action}`;
        btn.innerHTML = ICONS[action];
        btn.title = delta > 0 ? "加 1" : "减 1";
        btn.setAttribute("aria-label", delta > 0 ? "加 1" : "减 1");
        btn.disabled = readOnly;
        btn.addEventListener("click", () => stepInt(delta));
        holder.appendChild(btn);
      });
      wrap.appendChild(holder);
    } else {
      wrap.appendChild(input);
    }

    const errBox = document.createElement("p");
    errBox.className = "field-error";
    wrap.appendChild(errBox);

    refreshFieldState(wrap, key, owner, { ...ctx, readOnly });
    return wrap;
  }

  // ---------- 主配置选项 ----------
  function renderMainTab(container) {
    const cfg = state.config;
    // 仅渲染 config_desc.main 中定义且存在于配置中的字段（多余 key 不显示）
    schema.mainOrder.forEach((key) => {
      if (!(key in cfg)) return;
      const fieldEntry = descEntry("main", key);
      // when_show 显示条件：条件不满足时隐藏该字段
      if (whenShowHidden(fieldEntry, cfg)) return;
      const val = cfg[key];
      if (ConfigUtils.isPlainObject(val)) {
        const { section, content } = DomHelper.createCollapsibleSection(
          key,
          key,
        );
        // 主配置字段若为嵌套对象：子字段按条目声明的 schema 作用域渲染
        renderPlainObject(val, content, {
          scope:
            (fieldEntry &&
              typeof fieldEntry.schema === "string" &&
              fieldEntry.schema) ||
            "main",
          group: "main",
        });
        container.appendChild(section);
      } else {
        container.appendChild(
          buildFieldRow(key, val, cfg, { scope: "main", group: "main" }),
        );
      }
    });
  }

  function renderPlainObject(obj, parentEl, ctx) {
    // 仅渲染当前作用域 config_desc 中定义且存在于对象中的字段（多余 key 不显示、不改动）
    const order = scopeFieldOrder(ctx.scope, ctx.website);
    order.forEach((key) => {
      if (!(key in obj)) return;
      const val = obj[key];
      const entry = descEntry(ctx.scope, key, ctx.website);
      // when_show 显示条件：条件不满足时隐藏该字段（不渲染；值保留不删改）
      if (whenShowHidden(entry, obj)) return;
      // 嵌套配置对象：子字段声明了自己的 schema 作用域（须为字符串）时按该作用域描述递归（真正数据驱动），
      // 未声明或声明无效时继续沿用当前作用域
      const childCtx =
        entry && typeof entry.schema === "string" && entry.schema
          ? {
              scope: entry.schema,
              website: ctx.website,
              group: `${ctx.group || ""}\u0000${key}`,
            }
          : ctx;
      if (ConfigUtils.isPlainObject(val)) {
        const { section, content } = DomHelper.createCollapsibleSection(
          key,
          key,
        );
        renderPlainObject(val, content, childCtx);
        parentEl.appendChild(section);
      } else {
        parentEl.appendChild(buildFieldRow(key, val, obj, ctx));
      }
    });
  }

  // ---------- 频道选择器（首项为空选项用于新增，选项后 ✕ 删除） ----------
  function closeAllPickers(except) {
    document.querySelectorAll(".channel-picker-menu").forEach((menu) => {
      if (menu !== except) menu.classList.add("hidden");
    });
  }

  function buildPicker(tabKey, keys, current) {
    const wrap = document.createElement("div");
    wrap.className = "channel-picker";

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "channel-picker-toggle";
    const currentSpan = document.createElement("span");
    currentSpan.className = "channel-picker-current";
    currentSpan.textContent = current || "（暂无频道）";
    const caret = document.createElement("span");
    caret.className = "channel-picker-caret";
    caret.setAttribute("aria-hidden", "true");
    caret.textContent = "▾";
    toggle.append(currentSpan, caret);

    const menu = document.createElement("div");
    menu.className = "channel-picker-menu hidden";

    // 第一项：空选项，用于添加新的 channelid
    const addItem = document.createElement("div");
    addItem.className = "channel-picker-item add";
    addItem.setAttribute("data-action", "add");
    const addName = document.createElement("span");
    addName.className = "item-name placeholder";
    addName.textContent = CONFIG_CONST.TEXT.NEW_CHANNEL_PLACEHOLDER;
    addItem.appendChild(addName);
    addItem.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.add("hidden");
      addChannel(tabKey);
    });
    menu.appendChild(addItem);

    keys.forEach((k) => {
      const item = document.createElement("div");
      item.className = "channel-picker-item";
      if (k === current) item.classList.add("active");
      const name = document.createElement("span");
      name.className = "item-name";
      name.textContent = k;
      const del = document.createElement("button");
      del.type = "button";
      del.className = "channel-picker-delete";
      del.textContent = "✕";
      del.title = `删除频道 ${k}`;
      del.setAttribute("aria-label", `删除频道 ${k}`);
      item.append(name, del);
      item.addEventListener("click", (e) => {
        if (e.target === del) return;
        state.selected[tabKey] = k;
        menu.classList.add("hidden");
        render();
      });
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        menu.classList.add("hidden");
        removeChannel(tabKey, k);
      });
      menu.appendChild(item);
    });

    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      const willOpen = menu.classList.contains("hidden");
      closeAllPickers(menu);
      menu.classList.toggle("hidden", !willOpen);
    });
    // 阻止点击冒泡导致菜单立即关闭
    menu.addEventListener("click", (e) => e.stopPropagation());

    wrap.append(toggle, menu);
    return wrap;
  }

  function genChannelKey(map, tab) {
    const base = CONFIG_CONST.TEXT.NEW_CHANNEL_NAME(tab.short);
    let name = base;
    let i = 1;
    while (Object.prototype.hasOwnProperty.call(map, name)) {
      i += 1;
      name = `${base}${i}`;
    }
    return name;
  }

  // 以期望的频道名作为字典 key；重名时在名称后追加序号，避免覆盖已有频道。
  // hasOwnProperty 判断：'__proto__' 等键用 in 恒为真，会被误判为已存在。
  function genUniqueChannelKey(map, desired) {
    const base =
      (desired === undefined || desired === null
        ? ""
        : String(desired)
      ).trim() || "新频道";
    if (!Object.prototype.hasOwnProperty.call(map, base)) return base;
    let i = 2;
    while (Object.prototype.hasOwnProperty.call(map, base + i)) i += 1;
    return base + i;
  }

  // 取某网站频道配置中的「频道ID」字段名：
  // 优先使用 config_desc.channel.<website> 中名为 id 的字段，否则取第一个 required 字段；
  // 均未声明时返回 null（调用方据此拒绝自动新建，避免写错字段）。
  function channelIdField(website) {
    const defs = schema.configDesc.channel[website];
    if (!ConfigUtils.isPlainObject(defs)) return null;
    if (Object.prototype.hasOwnProperty.call(defs, "id")) return "id";
    const keys = Object.keys(defs);
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      if (k.startsWith("_")) continue;
      const e = defs[k];
      if (e && typeof e === "object" && e.required === true) return k;
    }
    return null;
  }

  function addChannel(tabKey) {
    if (state.saving) return;
    const tab = CONFIG_CONST.CHANNEL_TABS.find((t) => t.key === tabKey);
    // 没有有效模板（config_desc.channel.<website> 未定义任何带 default 的字段）时阻止创建
    const tpl = schema.templates[tab.website];
    if (!tpl || !Object.keys(tpl).length) {
      setStatus(CONFIG_CONST.TEXT.ADD_CHANNEL_NO_TEMPLATE(tab.label), "error");
      return;
    }
    let created = "";
    const syncKey = keySyncField(tab.website);
    commit((cfg) => {
      if (!ConfigUtils.isPlainObject(cfg[tabKey])) cfg[tabKey] = {};
      const map = cfg[tabKey];
      created = genChannelKey(map, tab);
      // 新频道模板 = config_desc.channel.<website> 各条目的 default（无需硬编码兜底）
      map[created] = ConfigUtils.clone(tpl);
      // sync_key：新建频道该字段为空（如 title 默认 ''）时以生成的频道名（key）为初值
      if (syncKey !== null && isEmptyKeyValue(map[created][syncKey])) {
        map[created][syncKey] = created;
      }
      state.selected[tabKey] = created;
    });
    setStatus(CONFIG_CONST.TEXT.ADD_CHANNEL(created), "muted");
  }

  // 由「获取媒体频道 ID」页调用：以获取到的频道名称与ID自动新建一个频道，
  // 并把「修改运行配置」页切到对应频道（website: 'youtube' / 'bilibili'）。
  // 返回 Promise<{ ok, name?, message?, existed? }>，供调用方提示结果。
  async function addChannelFromResult(website, name, channelId) {
    const tab = CONFIG_CONST.CHANNEL_TABS.find((t) => t.website === website);
    if (!tab) return { ok: false, message: `未知的网站类型：${website}` };
    // 配置页可能尚未打开：首次调用时按需加载（loadConfig 已含失败处理）
    if (!state.config) await loadConfig();
    if (!state.config)
      return { ok: false, message: "配置尚未加载，无法自动新建频道" };
    if (state.saving) return { ok: false, message: "配置正在保存，请稍后再试" };
    const tpl = schema.templates[tab.website];
    if (!tpl || !Object.keys(tpl).length) {
      return {
        ok: false,
        message: CONFIG_CONST.TEXT.ADD_CHANNEL_NO_TEMPLATE(tab.label),
      };
    }
    const idField = channelIdField(tab.website);
    if (!idField)
      return { ok: false, message: `配置描述缺少「${tab.label}」的频道ID字段` };
    const mapKey = tab.key;
    if (!ConfigUtils.isPlainObject(state.config[mapKey]))
      state.config[mapKey] = {};
    const map = state.config[mapKey];
    // 已存在相同频道ID的频道：直接选中该频道，避免重复添加
    const existing = Object.keys(map).find(
      (k) =>
        ConfigUtils.isPlainObject(map[k]) &&
        String(map[k][idField]) === String(channelId),
    );
    if (existing) {
      state.tab = mapKey;
      state.selected[mapKey] = existing;
      render();
      setStatus(`该频道已存在，已为你选中「${existing}」`, "muted");
      return { ok: true, name: existing, existed: true };
    }
    let created = "";
    // 先切到目标频道 tab，commit 内部重建页面时即显示该频道
    state.tab = mapKey;
    commit((cfg) => {
      if (!ConfigUtils.isPlainObject(cfg[mapKey])) cfg[mapKey] = {};
      const m = cfg[mapKey];
      created = genUniqueChannelKey(m, name);
      // 新频道模板 = config_desc.channel.<website> 各条目的 default
      const ch = ConfigUtils.clone(tpl);
      ch[idField] = channelId;
      // sync_key 字段（如 title）填频道名称，使其与频道名 key 一致
      const syncKey = keySyncField(tab.website);
      if (syncKey !== null) ch[syncKey] = created;
      // 用 defineProperty 写入自有属性（频道名可能是 __proto__ 等特殊键）
      Object.defineProperty(m, created, {
        value: ch,
        enumerable: true,
        writable: true,
        configurable: true,
      });
      state.selected[mapKey] = created;
    });
    setStatus(CONFIG_CONST.TEXT.ADD_CHANNEL_WITH_ID(created), "muted");
    return { ok: true, name: created };
  }

  function removeChannel(tabKey, key) {
    if (state.saving) return;
    if (!state.config || !ConfigUtils.isPlainObject(state.config[tabKey]))
      return;
    // hasOwnProperty 判断：'__proto__' 等键用 in 恒为真，会误入删除流程
    if (!Object.prototype.hasOwnProperty.call(state.config[tabKey], key))
      return;
    if (!confirm(CONFIG_CONST.TEXT.DELETE_CHANNEL_CONFIRM(key))) return;
    commit((cfg) => {
      delete cfg[tabKey][key];
      const rest = Object.keys(cfg[tabKey]);
      state.selected[tabKey] = rest[0] || null;
    });
    clearKeyConflict(tabKey, key);
  }

  // 频道重命名（底层）：保留原有键顺序，用 defineProperty 写入自有属性
  // （频道名可能是 __proto__ 等特殊键，直接赋值会落到原型链上导致该频道数据丢失）
  function renameChannelKey(tabKey, oldKey, newKey) {
    const rebuilt = {};
    Object.keys(state.config[tabKey]).forEach((k) => {
      Object.defineProperty(rebuilt, k === oldKey ? newKey : k, {
        value: state.config[tabKey][k],
        enumerable: true,
        writable: true,
        configurable: true,
      });
    });
    state.config[tabKey] = rebuilt;
    if (state.selected[tabKey] === oldKey) state.selected[tabKey] = newKey;
  }

  // sync_key：修改来源字段（如 title）后，把频道名称(key)同步为该字段值。
  // 目标 key 与其它频道已有 key 重复（字典 key 不能重复）时无法自动重命名，保持原 key
  // 并标记冲突，渲染层据此显示该频道的 key 输入框供手动修改。
  function syncChannelKeyFromField(tabKey, oldKey, value) {
    if (!state.config || !ConfigUtils.isPlainObject(state.config[tabKey]))
      return;
    const map = state.config[tabKey];
    if (!Object.prototype.hasOwnProperty.call(map, oldKey)) return;
    const newKey = value === undefined || value === null ? "" : String(value);
    if (newKey.trim() === "") return; // 字段为空：保持频道名称(key)不变
    if (newKey === oldKey) {
      clearKeyConflict(tabKey, oldKey);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(map, newKey)) {
      setKeyConflict(tabKey, oldKey); // 与其它频道重复：显示 key 输入框供手动修改
      return;
    }
    renameChannelKey(tabKey, oldKey, newKey);
    clearKeyConflict(tabKey, oldKey);
  }

  // 手动修改频道名称(key)：只改 key，不反向同步来源字段（如 title）
  function renameChannel(tabKey, oldKey, raw) {
    if (state.saving) return;
    const newKey = (raw || "").trim();
    const map = state.config[tabKey];
    if (!newKey) {
      setStatus(CONFIG_CONST.TEXT.RENAME_EMPTY, "error");
      render();
      return;
    }
    if (newKey === oldKey) {
      clearKeyConflict(tabKey, oldKey);
      render();
      return;
    }
    if (Object.prototype.hasOwnProperty.call(map, newKey)) {
      setStatus(CONFIG_CONST.TEXT.RENAME_DUPLICATE(newKey), "error");
      render();
      return;
    }
    setStatus("");
    // 手动改 key 视为对该频道名称的最终确认：清除冲突标记（key 已唯一）
    clearKeyConflict(tabKey, oldKey);
    clearKeyConflict(tabKey, newKey);
    commit(() => renameChannelKey(tabKey, oldKey, newKey));
  }

  // ---------- 规则类列表字段（如 title_change；规则作用域由字段条目的 rules 声明） ----------
  function buildRuleSection(tab, chKey, channel, key, ruleScope, channelGroup) {
    const entry = descEntry("channel", key, tab.website);
    const title = `${(entry && entry.label) || key} ${key}`;
    const { section, header, content } = DomHelper.createCollapsibleSection(
      `${tab.key}.${chKey}.${key}`,
      title,
    );
    section.classList.add("title-change-list");

    // rules 引用无效：该列表按只读处理 —— 实际禁用「新增 / 删除 / 编辑」，
    // 不渲染「添加规则」按钮，也不渲染任何字段行（提示与行为一致）
    if (!rulesScopeValid(ruleScope)) {
      section.classList.add("rule-readonly");
      content.appendChild(
        DomHelper.createTip(
          `配置描述无效：规则作用域「${ruleScope}」未指向有效作用域，该列表已按只读处理（不可新增 / 删除 / 编辑）`,
          false,
          "var(--accent-amber)",
        ),
      );
      const roRules = Array.isArray(channel[key]) ? channel[key] : [];
      if (!roRules.length) {
        content.appendChild(
          DomHelper.createTip(
            CONFIG_CONST.TEXT.EMPTY_RULE((entry && entry.label) || key),
          ),
        );
      } else {
        // 只读展示现有数据（复用数组字段的只读 JSON 呈现，无任何编辑入口）
        content.appendChild(
          buildFieldRow(key, channel[key], channel, {
            scope: "channel",
            website: tab.website,
            group: channelGroup,
          }),
        );
      }
      return section;
    }

    const ruleDesc = schema.configDesc[ruleScope] || {};
    // 作用域内以 "_" 开头的键为元数据（如 _meta），不渲染为字段
    const fieldKeys = Object.keys(ruleDesc).filter((k) => !k.startsWith("_"));

    const addRuleBtn = DomHelper.createBtn("＋ 添加规则", "add-button", (e) => {
      e.stopPropagation();
      commit((cfg) => {
        const ch = cfg[tab.key][chKey];
        if (!ConfigUtils.isPlainObject(ch)) return;
        if (!Array.isArray(ch[key])) ch[key] = [];
        // 新规则模板取自该规则作用域各条目的默认值；
        // 未声明 default 时按字段类型生成合理占位（bool→false / array→[] / select→首项…）
        const tpl = {};
        fieldKeys.forEach((rk) => {
          tpl[rk] = fallbackValue(ruleDesc[rk]);
        });
        ch[key].push(tpl);
      });
    });
    header.appendChild(addRuleBtn);

    const rules = Array.isArray(channel[key]) ? channel[key] : [];
    if (!rules.length) {
      content.appendChild(
        DomHelper.createTip(
          CONFIG_CONST.TEXT.EMPTY_RULE((entry && entry.label) || key),
        ),
      );
    }
    rules.forEach((rule, idx) => {
      const sub = DomHelper.createCollapsibleSection(
        `${tab.key}.${chKey}.${key}[${idx}]`,
        `规则 ${idx + 1}`,
      );
      sub.section.classList.add("title-change-item");
      const delRuleBtn = DomHelper.createBtn("删除", "delete-button", (e) => {
        e.stopPropagation();
        if (!confirm(CONFIG_CONST.TEXT.DELETE_RULE_CONFIRM(idx))) return;
        commit((cfg) => {
          const ch = cfg[tab.key][chKey];
          if (Array.isArray(ch[key])) ch[key].splice(idx, 1);
        });
      });
      sub.header.appendChild(delRuleBtn);

      // 规则元素异常保护：null / 字符串等无效元素不渲染字段行（避免崩溃），
      // 给出错误提示并保留删除入口（删除按钮已在上方注册）
      if (!ConfigUtils.isPlainObject(rule)) {
        sub.content.appendChild(
          DomHelper.createTip(
            "规则数据无效（需为对象），无法编辑，请删除该规则",
            false,
            "var(--accent-red)",
          ),
        );
        content.appendChild(sub.section);
        return;
      }

      // 规则字段按该作用域定义顺序渲染（websites 限制的字段仅对适用网站显示）
      fieldKeys.forEach((rk) => {
        const e = ruleDesc[rk];
        if (e && e.websites && !e.websites.includes(tab.website)) return;
        // when_show 显示条件：规则字段条件不满足时隐藏
        if (whenShowHidden(e, rule)) return;
        sub.content.appendChild(
          buildFieldRow(rk, rule[rk], rule, {
            scope: ruleScope,
            website: tab.website,
            group: `${channelGroup}|${key}|rule|${idx}`,
          }),
        );
      });
      content.appendChild(sub.section);
    });

    return section;
  }

  // ---------- 频道选项 ----------
  function renderChannelTab(container, tabKey) {
    const tab = CONFIG_CONST.CHANNEL_TABS.find((t) => t.key === tabKey);
    if (!tab) return;
    // 频道容器异常保护：缺失/为 null 时补空结构（无数据可丢失）；
    // 已是字符串/数组等异常值时保留原值并锁定编辑（绝不覆盖为 {}，避免数据丢失）
    if (state.config[tabKey] === undefined || state.config[tabKey] === null) {
      state.config[tabKey] = {};
    }
    const map = state.config[tabKey];
    if (!ConfigUtils.isPlainObject(map)) {
      container.appendChild(
        DomHelper.createTip(
          `频道容器 ${tabKey} 数据异常（需为字典），已锁定编辑以避免数据丢失`,
          false,
          "var(--accent-red)",
        ),
      );
      return;
    }
    const keys = Object.keys(map);

    // 校正当前选中的频道（hasOwnProperty：'__proto__' 等键用 in 恒为真）
    const selected = state.selected[tabKey];
    if (!selected || !Object.prototype.hasOwnProperty.call(map, selected))
      state.selected[tabKey] = keys[0] || null;

    container.appendChild(buildPicker(tabKey, keys, state.selected[tabKey]));

    const current = state.selected[tabKey];
    if (!current) {
      container.appendChild(
        DomHelper.createTip(CONFIG_CONST.TEXT.EMPTY_CHANNEL),
      );
      return;
    }
    const channel = map[current];

    // 频道字段的标准顺序（config_desc.channel.<website> 定义顺序），只显示其中的字段（多余 key 不显示）
    const channelOrder = schema.channelOrder[tab.website] || [];

    // 频道名称（字典 key）平时隐藏；仅当 sync_key 同步冲突（与其它频道 key 重复）时显示供手动修改
    if (isKeyConflict(tabKey, current)) {
      container.appendChild(buildRenameRow(tabKey, current));
    }

    if (!ConfigUtils.isPlainObject(channel)) {
      container.appendChild(
        DomHelper.createTip("该频道配置不是字典，无法编辑"),
      );
      return;
    }
    const chDesc = schema.configDesc.channel[tab.website] || {};
    const chGroup = `${tabKey}|${current}`;
    channelOrder.forEach((key) => {
      if (!(key in channel)) return;
      const fieldEntry = chDesc[key];
      // when_show 显示条件：条件不满足时隐藏该字段（不渲染；值保留不删改）
      if (whenShowHidden(fieldEntry, channel)) return;
      // 规则类列表字段（type=array 且声明了 rules 作用域）按规则列表渲染
      if (
        fieldEntry &&
        fieldEntry.type === "array" &&
        typeof fieldEntry.rules === "string"
      ) {
        container.appendChild(
          buildRuleSection(
            tab,
            current,
            channel,
            key,
            fieldEntry.rules,
            chGroup,
          ),
        );
        return;
      }
      const val = channel[key];
      if (ConfigUtils.isPlainObject(val)) {
        const { section, content } = DomHelper.createCollapsibleSection(
          `${tabKey}.${current}.${key}`,
          key,
        );
        // 嵌套配置对象：条目声明了 schema 作用域（须为字符串）时按其子字段定义渲染, 否则按当前频道作用域
        renderPlainObject(val, content, {
          scope:
            (fieldEntry &&
              typeof fieldEntry.schema === "string" &&
              fieldEntry.schema) ||
            "channel",
          website: tab.website,
          group: `${chGroup}|nested:${key}`,
        });
        container.appendChild(section);
      } else {
        container.appendChild(
          buildFieldRow(key, val, channel, {
            scope: "channel",
            website: tab.website,
            group: chGroup,
            ownerKey: current,
            tabKey,
          }),
        );
      }
    });
  }

  function buildRenameRow(tabKey, key) {
    const wrap = document.createElement("div");
    wrap.className = "config-item";

    const labelCell = document.createElement("div");
    labelCell.className = "field-label";
    const inputId = `config-field-${++fieldSeq}`;
    const label = document.createElement("label");
    label.htmlFor = inputId;
    label.textContent = "频道名称(key):";
    labelCell.appendChild(label);
    const hint = document.createElement("p");
    hint.className = "field-hint";
    hint.style.color = "var(--accent-red)";
    hint.textContent =
      "与其它频道名称重复，无法自动同步，请修改为唯一的频道名称(key)；单独修改此处不会同步 title";
    labelCell.appendChild(hint);
    wrap.appendChild(labelCell);

    const input = document.createElement("input");
    input.type = "text";
    input.id = inputId;
    input.value = key;
    input.classList.add("config-input-text");
    input.addEventListener("change", () =>
      renameChannel(tabKey, key, input.value),
    );
    wrap.appendChild(input);

    const errBox = document.createElement("p");
    errBox.className = "field-error";
    wrap.appendChild(errBox);
    return wrap;
  }

  // ---------- 渲染入口 ----------
  function render() {
    $.tabs.forEach((btn) => {
      const active = btn.dataset.tab === state.tab;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-selected", String(active));
    });

    const container = $.container;
    // 重建页面时清空字段行注册表（随后由各渲染入口重新登记）
    for (const g in fieldGroups) delete fieldGroups[g];
    container.innerHTML = "";
    if (!state.config) return;

    if (state.tab === CONFIG_CONST.MAIN_TAB) {
      renderMainTab(container);
    } else {
      renderChannelTab(container, state.tab);
    }
    applySavingLock();
  }

  // ---------- 加载 ----------
  async function loadConfig() {
    clearWarnings();
    $.container.innerHTML = "";
    $.container.appendChild(
      DomHelper.createTip(CONFIG_CONST.TEXT.LOADING, false),
    );
    setStatus("");
    $.saveBtn.disabled = true;
    $.undoBtn.disabled = true;
    $.refreshBtn.disabled = true;
    try {
      const res = await fetch(CONFIG_CONST.API.GET_CONFIG, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const raw = await res.json();
      const data = ConfigUtils.unwrap(raw);
      if (!ConfigUtils.isPlainObject(data)) throw new Error("返回数据格式错误");

      // 同步 config_desc（podflow/__init__.py）：字段顺序 / 默认值 / 选项 / 说明以它为准
      // 页面渲染完全依赖 config_desc, 缺失或结构不完整时直接视为加载失败
      const configDesc =
        ConfigUtils.isPlainObject(raw) &&
        ConfigUtils.isPlainObject(raw.config_desc)
          ? raw.config_desc
          : null;
      if (
        !configDesc ||
        !ConfigUtils.isPlainObject(configDesc.main) ||
        !ConfigUtils.isPlainObject(configDesc.channel)
      ) {
        throw new Error(
          "config_desc 缺失或结构不完整（需含 main 与 channel 定义）",
        );
      }

      state.config = ConfigUtils.clone(data);
      // 元数据防护：/getconfig 响应中的 config_desc / default_config 是协议元数据，
      // 不属于配置本身；后台若未用 response 包装配置（unwrap 无操作），不得混入待保存的配置 JSON
      delete state.config.config_desc;
      delete state.config.default_config;
      buildSchema(configDesc);
      applyDefaults(state.config);
      ConfigRules.normalize(state.config);
      clearAllKeyConflicts();
      state.tab = CONFIG_CONST.MAIN_TAB;
      // 频道 tab 默认选中第一个已有频道（异常容器不取键, 由渲染层显示错误提示）
      CONFIG_CONST.CHANNEL_TABS.forEach((tab) => {
        const map = state.config[tab.key];
        state.selected[tab.key] =
          (ConfigUtils.isPlainObject(map) ? Object.keys(map)[0] : null) || null;
      });
      resetHistory();
      render();
    } catch (err) {
      console.error(CONFIG_CONST.TEXT.LOAD_FAIL, err);
      $.container.innerHTML = "";
      $.container.appendChild(
        DomHelper.createTip(
          `${CONFIG_CONST.TEXT.LOAD_FAIL}: ${err.message}`,
          false,
          "var(--accent-red)",
        ),
      );
      state.config = null;
      resetHistory();
    } finally {
      $.refreshBtn.disabled = false;
    }
  }

  // ---------- 保存（统一提交暂存的最终 JSON） ----------
  async function saveConfig() {
    // 保存入口保护：防止重复调用（如连点 / 程序化调用）造成并发保存请求
    if (state.saving) return;
    if (!state.config) return;
    clearWarnings();

    // 先按后台规则归一化，再全量校验
    // 自动纠正若改变了配置，记录为一步可撤销的历史（撤销可回到纠正前的值），
    // 避免纠正悄悄作用于 state.config 而撤销历史不一致
    const beforeCorrection = JSON.stringify(state.config);
    ConfigRules.normalize(state.config);
    if (JSON.stringify(state.config) !== beforeCorrection) {
      commit(() => {}, { render: false }); // 记录纠正后的状态为一步（随后 setStatus 会覆盖其提示）
    }
    const { errors, warns } = ConfigRules.validateAll(state.config);
    render();

    if (errors.length) {
      const more = errors.length > 3 ? ` 等 ${errors.length} 项` : "";
      setStatus(
        `${CONFIG_CONST.TEXT.SAVE_BLOCKED}：${errors.slice(0, 3).join("；")}${more}`,
        "error",
      );
      return;
    }

    const finalData = ConfigUtils.clone(state.config);
    // 被 when_show 隐藏的配置不提交到后台（作用于主配置与所有频道; 仅提交副本, 本地状态保留）
    stripHiddenFields(finalData);
    console.log("最终提交配置", JSON.stringify(finalData, null, 2));
    // 进入保存态：禁用所有编辑 / 频道管理 / 撤销与重复提交（新修改不会被旧请求覆盖）
    state.saving = true;
    updateActionButtons();
    applySavingLock();
    setStatus(CONFIG_CONST.TEXT.SAVING, "saving");
    $.refreshBtn.disabled = true;

    try {
      const res = await fetch(CONFIG_CONST.API.SAVE_CONFIG, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(finalData),
      });
      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try {
          const errJson = await res.json();
          msg =
            errJson.detail ||
            errJson.message ||
            (typeof errJson.error === "string" ? errJson.error : null) ||
            JSON.stringify(errJson);
        } catch (e) {
          msg = (await res.text()) || msg;
        }
        throw new Error(msg);
      }

      // ---- 保存响应的明确协议（classifySaveResponse）----
      // 1) 响应体为空 → 成功（兼容不回显内容的后台），保留本地暂存
      // 2) 读取失败 / 非 JSON / JSON null 等非对象 → 失败（绝不判成功）
      // 3) 完整配置（频道容器均为字典 + 提交的主配置字段全部存在）→ 采用并刷新本地
      // 4) 业务错误信封（error / err / success:false / status∈{error,fail...}）→ 失败，显示后台错误
      // 5) 其余（部分配置或无法识别的结构）→ 失败提示，不采用返回值、不重置历史
      //    ——避免将部分配置或业务错误误判为保存成功
      let rawText = null;
      let readError = null;
      try {
        rawText = await res.text();
      } catch (e) {
        readError = e; // 读取失败不得当作空响应体判成功
      }
      const result = classifySaveResponse(rawText, finalData, readError);
      if (result.kind === "error") throw new Error(result.message);

      if (result.kind === "adopt") {
        state.config = ConfigUtils.clone(result.data);
        // 元数据防护：同 loadConfig，回显配置中若夹带 config_desc / default_config 不予保留
        delete state.config.config_desc;
        delete state.config.default_config;
        // 采用后台确认的配置后同样补齐默认值并做结构性纠正, 保证渲染与校验一致
        applyDefaults(state.config);
        ConfigRules.normalize(state.config);
        clearAllKeyConflicts();
        CONFIG_CONST.CHANNEL_TABS.forEach((tab) => {
          const keys = Object.keys(state.config[tab.key] || {});
          if (
            !state.selected[tab.key] ||
            !Object.prototype.hasOwnProperty.call(
              state.config[tab.key] || {},
              state.selected[tab.key],
            )
          ) {
            state.selected[tab.key] = keys[0] || null;
          }
        });
      }

      resetHistory();
      const warnNote = warns.length ? `（${warns.length} 条提示见下方）` : "";
      setStatus(`${CONFIG_CONST.TEXT.SAVE_SUCCESS}${warnNote}`, "success");
      renderWarnings(warns);
      if (warns.length) {
        console.warn("保存提示", warns);
      }
    } catch (err) {
      clearWarnings();
      console.error(CONFIG_CONST.TEXT.SAVE_FAIL, err);
      setStatus(`${CONFIG_CONST.TEXT.SAVE_FAIL}: ${err.message}`, "error");
    } finally {
      // 退出保存态并重建页面（恢复控件可用）；失败时本地修改与撤销历史均完整保留
      state.saving = false;
      render();
      $.refreshBtn.disabled = false;
      updateActionButtons();
    }
  }

  // ---------- 事件绑定 ----------
  $.tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (state.saving) return;
      state.tab = btn.dataset.tab;
      render();
    });
  });
  $.refreshBtn.addEventListener("click", loadConfig);
  $.saveBtn.addEventListener("click", saveConfig);
  if ($.undoBtn) $.undoBtn.addEventListener("click", undo);
  // 点击空白处关闭频道选择菜单
  document.addEventListener("click", () => closeAllPickers());
  // 点击空白处关闭自定义下拉的监听已随组件移至 custom_select.js（多页面共用）

  updateActionButtons();

  // 对外暴露页面切换钩子（index.js 调用）
  window.podflowConfig = {
    onShow: () => {
      if (!state.config) return loadConfig();
      render();
    },
    // 「获取媒体频道 ID」页提交成功后调用：按获取结果自动新建频道并切到对应频道页
    addChannelFromResult,
    utils: ConfigUtils,
    const: CONFIG_CONST,
  };
});
