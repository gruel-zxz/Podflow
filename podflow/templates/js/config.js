// /templates/js/config.js
// ====================== 1. 全局通用配置常量（新增参数仅修改此处） ======================
const CONFIG_CONST = {
    // 后端接口地址
    API: {
        GET_CONFIG: '/getconfig',
        SAVE_CONFIG: '/saveconfig'
    },
    // 支持的媒体渠道列表，新增渠道只需要在这里追加
    CHANNEL_LIST: [
        { key: 'channelid_youtube', label: 'YouTube 频道' },
        { key: 'channelid_bilibili', label: 'Bilibili 频道' }
        // 示例新增抖音：{ key: 'channelid_douyin', label: '抖音频道' }
    ],
    // 媒体格式下拉选项
    MEDIA_FORMAT_OPTIONS: ['m4a', 'mp4', 'webm'],
    // 标题修改模式下拉选项
    TITLE_MODE_OPTIONS: [
        { value: 'add-left', label: '左侧追加' },
        { value: 'add-right', label: '右侧追加' },
        { value: 'replace', label: '完全替换' }
    ],
    // 字段类型映射，统一渲染规则
    FIELD_TYPE_MAP: {
        BOOLEAN: 'boolean',
        NUMBER: 'number',
        STRING: 'string',
        URL: 'url',
        SELECT_MEDIA: 'select_media',
        SELECT_TITLE_MODE: 'select_title_mode'
    },
    // 统一文案配置
    TEXT: {
        LOADING: '正在加载配置...',
        LOAD_FAIL: '加载配置失败',
        SAVING: '正在保存配置...',
        SAVE_SUCCESS: '配置保存成功！1.5秒后自动刷新',
        SAVE_FAIL: '保存失败',
        EMPTY_CHANNEL: '暂无频道，点击上方「添加」创建',
        EMPTY_RULE: '无标题修改规则，点击「添加规则」新建',
        DELETE_CHANNEL_TEMP: '确定删除新建未保存频道？',
        DELETE_CHANNEL_CONFIRM: (name) => `确定删除频道「${name}」吗？`,
        DELETE_RULE_CONFIRM: (idx) => `确定删除规则 ${idx + 1}？`,
        EMPTY_CHANNEL_ID_WARN: '频道ID不能为空，已跳过该频道保存'
    },
    // 临时key前缀
    TEMP_KEY_PREFIX: 'new_channel_'
};

// ====================== 2. 通用工具函数层 ======================
const ConfigUtils = {
    // 生成唯一临时标识
    genTempKey(prefix = CONFIG_CONST.TEMP_KEY_PREFIX) {
        return `${prefix}${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    },

    // 路径拆分工具
    splitPath(path) {
        return path.split('.');
    },

    // 递归清理临时字段 _tempKey
    cleanTempKey(obj) {
        if (Array.isArray(obj)) {
            return obj.map(item => this.cleanTempKey(item));
        }
        if (typeof obj === 'object' && obj !== null) {
            const result = {};
            for (const k in obj) {
                if (k !== '_tempKey') result[k] = this.cleanTempKey(obj[k]);
            }
            return result;
        }
        return obj;
    },

    // 根据路径读取对象深层值
    getDeepValue(obj, path) {
        const parts = this.splitPath(path);
        let res = obj;
        for (const p of parts) {
            if (!res) return undefined;
            // 匹配数组路径 title_change[0]
            const arrMatch = p.match(/^(.+)\[(\d+)\]$/);
            if (arrMatch) {
                res = res[arrMatch[1]]?.[Number(arrMatch[2])];
            } else {
                res = res[p];
            }
        }
        return res;
    },

    // 根据路径设置对象深层值，自动创建空对象/数组
    setDeepValue(obj, path, value) {
        const parts = this.splitPath(path);
        let target = obj;
        for (let i = 0; i < parts.length; i++) {
            const curr = parts[i];
            const arrMatch = curr.match(/^(.+)\[(\d+)\]$/);
            if (arrMatch) {
                const [, arrKey, idx] = arrMatch;
                if (!target[arrKey]) target[arrKey] = [];
                if (!target[arrKey][Number(idx)]) target[arrKey][Number(idx)] = {};
                target = target[arrKey][Number(idx)];
            } else {
                if (i === parts.length - 1) {
                    target[curr] = value;
                } else if (!target[curr]) {
                    target[curr] = {};
                }
                target = target[curr];
            }
        }
    },

    // 简单数据校验
    validateField(type, value) {
        switch (type) {
            case CONFIG_CONST.FIELD_TYPE_MAP.URL:
                if (!value) return true;
                return /^https?:\/\/.+/.test(value);
            case CONFIG_CONST.FIELD_TYPE_MAP.NUMBER:
                return !isNaN(Number(value));
            default:
                return true;
        }
    }
};

// ====================== 3. DOM 公共渲染工具 ======================
const DomHelper = {
    expandedPaths: new Set(),

    // 创建通用按钮
    createBtn(text, cls, clickFn) {
        const btn = document.createElement('button');
        btn.textContent = text;
        btn.classList.add('config-button', cls);
        btn.type = 'button';
        btn.addEventListener('click', clickFn);
        return btn;
    },

    // 创建折叠面板容器
    createCollapsibleSection(path, titleText, kind = 'object') {
        const section = document.createElement('div');
        section.className = 'collapsible-section';
        section.dataset.path = path;
        section.dataset.kind = kind;

        const header = document.createElement('div');
        header.className = 'collapsible-header';
        header.tabIndex = 0;
        header.setAttribute('role', 'button');
        header.setAttribute('aria-controls', `config-section-${path}`);

        const content = document.createElement('div');
        content.id = `config-section-${path}`;
        const isExpanded = this.expandedPaths.has(path);
        content.className = `collapsible-content${isExpanded ? '' : ' hidden'}`;
        header.classList.toggle('expanded', isExpanded);
        header.setAttribute('aria-expanded', String(isExpanded));
        header.innerHTML = `<span class="section-title">${titleText}</span><span class="toggle-icon" aria-hidden="true">›</span>`;

        const toggle = (e) => {
            if (e.target.tagName === 'BUTTON') return;
            const isHide = content.classList.toggle('hidden');
            header.classList.toggle('expanded', !isHide);
            header.setAttribute('aria-expanded', String(!isHide));
            if (isHide) this.expandedPaths.delete(path);
            else this.expandedPaths.add(path);
        };
        header.addEventListener('click', toggle);
        header.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggle(e);
            }
        });

        section.append(header, content);
        return { section, header, content };
    },

    captureExpandedState(container) {
        container.querySelectorAll('.collapsible-section[data-path]').forEach(section => {
            const header = section.querySelector(':scope > .collapsible-header');
            if (header?.getAttribute('aria-expanded') === 'true') this.expandedPaths.add(section.dataset.path);
        });
    },

    // 滚动到指定元素
    scrollToEl(el) {
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    // 创建提示文本
    createTip(text, isItalic = true, color = '#777') {
        const p = document.createElement('p');
        p.textContent = text;
        p.style.color = color;
        if (isItalic) p.style.fontStyle = 'italic';
        p.style.marginLeft = '10px';
        return p;
    }
};

// ====================== 4. 主逻辑入口 ======================
document.addEventListener('DOMContentLoaded', () => {
    // DOM 元素缓存
    const $ = {
        container: document.getElementById('configContainer'),
        refreshBtn: document.getElementById('refreshConfigBtn'),
        saveBtn: document.getElementById('saveConfigBtn'),
        status: document.getElementById('configStatus'),
        page: document.getElementById('pageConfig')
    };

    let currentConfig = null;

    function rerenderConfig() {
        DomHelper.captureExpandedState($.container);
        renderConfig(currentConfig, $.container);
    }

    // 构建通用输入组件（消除大量if硬编码）
    function buildInputItem(key, value, path) {
        const wrap = document.createElement('div');
        wrap.className = 'config-item';
        const label = document.createElement('label');
        label.htmlFor = `config-${path}`;
        label.textContent = `${key}:`;
        wrap.appendChild(label);

        const inputId = `config-${path}`;
        let input;
        let fieldType = CONFIG_CONST.FIELD_TYPE_MAP.STRING;

        // 布尔复选框
        if (typeof value === 'boolean') {
            fieldType = CONFIG_CONST.FIELD_TYPE_MAP.BOOLEAN;
            input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = value;
            label.style.display = 'inline-block';
            input.style.marginLeft = '10px';
            wrap.appendChild(input);
        }
        // 数字输入框
        else if (typeof value === 'number') {
            fieldType = CONFIG_CONST.FIELD_TYPE_MAP.NUMBER;
            input = document.createElement('input');
            input.type = 'number';
            input.value = value;
            input.step = Number.isInteger(value) ? '1' : 'any';
            wrap.appendChild(document.createElement('br'));
            wrap.appendChild(input);
        }
        // 媒体格式下拉
        else if (path.includes('media')) {
            fieldType = CONFIG_CONST.FIELD_TYPE_MAP.SELECT_MEDIA;
            input = document.createElement('select');
            CONFIG_CONST.MEDIA_FORMAT_OPTIONS.forEach(opt => {
                const optEl = document.createElement('option');
                optEl.value = opt;
                optEl.textContent = opt;
                if (opt === value) optEl.selected = true;
                input.appendChild(optEl);
            });
            wrap.appendChild(document.createElement('br'));
            wrap.appendChild(input);
        }
        // 标题模式下拉
        else if (path.includes('.title_change[') && key === 'mode') {
            fieldType = CONFIG_CONST.FIELD_TYPE_MAP.SELECT_TITLE_MODE;
            input = document.createElement('select');
            CONFIG_CONST.TITLE_MODE_OPTIONS.forEach(opt => {
                const optEl = document.createElement('option');
                optEl.value = opt.value;
                optEl.textContent = opt.label;
                if (opt.value === value) optEl.selected = true;
                input.appendChild(optEl);
            });
            wrap.appendChild(document.createElement('br'));
            wrap.appendChild(input);
        }
        // URL输入框
        else if (['link', 'icon', 'url'].includes(key)) {
            fieldType = CONFIG_CONST.FIELD_TYPE_MAP.URL;
            input = document.createElement('input');
            input.type = 'url';
            input.value = value;
            wrap.appendChild(document.createElement('br'));
            wrap.appendChild(input);
        }
        // 普通文本
        else {
            input = document.createElement('input');
            input.type = 'text';
            input.value = value;
            wrap.appendChild(document.createElement('br'));
            wrap.appendChild(input);
        }

        // 统一绑定属性
        input.id = inputId;
        input.dataset.path = path;
        input.dataset.type = fieldType;
        // 统一样式类
        if (input.tagName === 'INPUT') input.classList.add('config-input-text');
        if (input.tagName === 'SELECT') input.classList.add('config-input-select');

        return wrap;
    }

    // 递归渲染配置（渠道循环化，移除硬编码）
    function renderConfig(data, parentEl, pathPrefix = '') {
        parentEl.innerHTML = '';
        Object.entries(data).forEach(([key, val]) => {
            const fullPath = pathPrefix ? `${pathPrefix}.${key}` : key;
            // 标题规则数组由频道卡片中的专用折叠面板渲染，避免重复生成一个文本输入框。
            if (key === 'title_change' && Array.isArray(val)) return;
            // 匹配媒体总节点 media
            if (key === 'media' && typeof val === 'object' && !Array.isArray(val)) {
                const { section, header, content } = DomHelper.createCollapsibleSection(fullPath, '媒体配置 media', 'media');
                // 循环渲染所有渠道，新增渠道仅修改常量
                CONFIG_CONST.CHANNEL_LIST.forEach(channelConf => {
                    const chanKey = channelConf.key;
                    const chanPath = `${fullPath}.${chanKey}`;
                    const { section: chanWrap, header: chanHeader, content: chanContent } = DomHelper.createCollapsibleSection(chanPath, channelConf.label, 'channel-group');
                    // 添加频道新增按钮
                    const addBtn = DomHelper.createBtn('添加', 'add-button', (e) => {
                        e.stopPropagation();
                        addNewChannel(chanPath);
                    });
                    chanHeader.appendChild(addBtn);
                    // 渲染现有频道列表
                    const channelMap = val[chanKey] || {};
                    const chanKeys = Object.keys(channelMap);
                    if (chanKeys.length === 0) {
                        chanContent.appendChild(DomHelper.createTip(CONFIG_CONST.TEXT.EMPTY_CHANNEL));
                    } else {
                        chanKeys.forEach(realChanId => {
                            const chanData = channelMap[realChanId];
                            const domKey = chanData._tempKey || realChanId;
                            const itemPath = `${chanPath}.${domKey}`;
                            const { section: itemWrap, header: itemHeader, content: itemContent } = DomHelper.createCollapsibleSection(itemPath, chanData.id || domKey, 'channel-item');
                            itemWrap.classList.add('channel-item');
                            // 删除按钮
                            const delBtn = DomHelper.createBtn('删除', 'delete-button', (e) => {
                                e.stopPropagation();
                                removeChannel(chanPath, realChanId);
                            });
                            itemHeader.appendChild(delBtn);
                            // 渲染频道基础配置
                            const renderData = { ...chanData };
                            delete renderData._tempKey;
                            renderConfig(renderData, itemContent, itemPath);
                            // 渲染标题修改规则数组
                            const rulePathPrefix = `${itemPath}.title_change`;
                            const { section: ruleList, header: ruleHeader, content: ruleContent } = DomHelper.createCollapsibleSection(rulePathPrefix, '标题修改规则', 'rule-list');
                            ruleList.classList.add('title-change-list');
                            // 添加规则按钮
                            const addRuleBtn = DomHelper.createBtn('添加规则', 'add-button', (e) => {
                                e.stopPropagation();
                                addTitleRule(`${itemPath}.title_change`);
                            });
                            ruleHeader.appendChild(addRuleBtn);
                            const ruleArr = renderData.title_change || [];
                            if (ruleArr.length === 0) {
                                ruleContent.appendChild(DomHelper.createTip(CONFIG_CONST.TEXT.EMPTY_RULE));
                            } else {
                                ruleArr.forEach((rule, idx) => {
                                    const rulePath = `${itemPath}.title_change[${idx}]`;
                                    const { section: ruleWrap, header: ruleHeader, content: ruleItemContent } = DomHelper.createCollapsibleSection(rulePath, `规则 ${idx + 1}`, 'rule');
                                    ruleWrap.classList.add('title-change-item');
                                    // 删除规则按钮
                                    const delRuleBtn = DomHelper.createBtn('删除', 'delete-button', (e) => {
                                        e.stopPropagation();
                                        removeTitleRule(`${itemPath}.title_change`, idx);
                                    });
                                    ruleHeader.appendChild(delRuleBtn);
                                    renderConfig(rule, ruleItemContent, rulePath);
                                    ruleContent.appendChild(ruleWrap);
                                });
                            }
                            itemContent.appendChild(ruleList);
                            chanContent.appendChild(itemWrap);
                        });
                    }
                    chanWrap.appendChild(chanContent);
                    content.appendChild(chanWrap);
                });
                section.appendChild(content);
                parentEl.appendChild(section);
            }
            // 普通嵌套对象
            else if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
                const { section: subWrap, content: subContent } = DomHelper.createCollapsibleSection(fullPath, key, 'object');
                renderConfig(val, subContent, fullPath);
                parentEl.appendChild(subWrap);
            }
            // 基础字段渲染
            else {
                const inputWrap = buildInputItem(key, val, fullPath);
                parentEl.appendChild(inputWrap);
            }
        });
    }

    // 新增频道
    function addNewChannel(chanPath) {
        if (!currentConfig) return;
        const target = ConfigUtils.getDeepValue(currentConfig, chanPath);
        const tempKey = ConfigUtils.genTempKey();
        target[tempKey] = {
            _tempKey: tempKey,
            id: '',
            name: '',
            media: CONFIG_CONST.MEDIA_FORMAT_OPTIONS[0],
            link: '',
            icon: '',
            description: '',
            title_change: []
        };
        DomHelper.expandedPaths.add('media');
        DomHelper.expandedPaths.add(chanPath);
        DomHelper.expandedPaths.add(`${chanPath}.${tempKey}`);
        rerenderConfig();
        const newEl = $.container.querySelector(`.channel-item[data-path="${chanPath}.${tempKey}"]`);
        if (newEl) {
            DomHelper.scrollToEl(newEl);
        }
    }

    // 删除频道
    function removeChannel(chanPath, realKey) {
        if (!currentConfig) return;
        const target = ConfigUtils.getDeepValue(currentConfig, chanPath);
        if (!target?.[realKey]) return;
        const isTemp = realKey.startsWith(CONFIG_CONST.TEMP_KEY_PREFIX);
        const confirmText = isTemp
            ? CONFIG_CONST.TEXT.DELETE_CHANNEL_TEMP
            : CONFIG_CONST.TEXT.DELETE_CHANNEL_CONFIRM(target[realKey].id || realKey);
        if (isTemp || confirm(confirmText)) {
            delete target[realKey];
            rerenderConfig();
        }
    }

    // 新增标题规则
    function addTitleRule(rulePath) {
        if (!currentConfig) return;
        const arr = ConfigUtils.getDeepValue(currentConfig, rulePath);
        if (!Array.isArray(arr)) return;
        arr.push({
            pattern: '',
            mode: CONFIG_CONST.TITLE_MODE_OPTIONS[2].value,
            value: ''
        });
        const channelPath = rulePath.replace('.title_change', '');
        DomHelper.expandedPaths.add('media');
        DomHelper.expandedPaths.add(channelPath);
        DomHelper.expandedPaths.add(rulePath);
        DomHelper.expandedPaths.add(`${rulePath}[${arr.length - 1}]`);
        rerenderConfig();
        const channelEl = $.container.querySelector(`.channel-item[data-path="${channelPath}"]`);
        if (channelEl) {
            const rules = channelEl.querySelectorAll('.title-change-item');
            DomHelper.scrollToEl(rules[rules.length - 1]);
        }
    }

    // 删除标题规则
    function removeTitleRule(rulePath, idx) {
        if (!currentConfig) return;
        const arr = ConfigUtils.getDeepValue(currentConfig, rulePath);
        if (!Array.isArray(arr) || idx < 0 || idx >= arr.length) return;
        if (confirm(CONFIG_CONST.TEXT.DELETE_RULE_CONFIRM(idx))) {
            arr.splice(idx, 1);
            rerenderConfig();
        }
    }

    // 收集表单数据并生成最终配置
    function collectConfig() {
        const result = {};
        // 遍历所有顶级折叠块
        $.container.querySelectorAll(':scope > .collapsible-section').forEach(section => {
            const rootPath = section.dataset.path;
            const rootKey = ConfigUtils.splitPath(rootPath)[0];
            if (rootKey === 'media') {
                result.media = {};
                // 遍历所有渠道分组
                CONFIG_CONST.CHANNEL_LIST.forEach(chanConf => {
                    const chanKey = chanConf.key;
                    const chanWrap = section.querySelector(`.collapsible-section[data-path="media.${chanKey}"]`);
                    if (!chanWrap) return;
                    result.media[chanKey] = {};
                    // 遍历每个频道项
                    chanWrap.querySelectorAll('.channel-item').forEach(item => {
                        const itemPath = item.dataset.path;
                        const idInput = item.querySelector(`[data-path="${itemPath}.id"]`);
                        const channelId = idInput?.value.trim();
                        if (!channelId) {
                            console.warn(CONFIG_CONST.TEXT.EMPTY_CHANNEL_ID_WARN, itemPath);
                            return;
                        }
                        const chanObj = {};
                        // 递归填充频道内所有字段
                        fillObjectFromDom(item.querySelector('.collapsible-content'), chanObj, itemPath);
                        result.media[chanKey][channelId] = chanObj;
                    });
                });
            } else {
                const subObj = {};
                result[rootKey] = subObj;
                fillObjectFromDom(section.querySelector(':scope > .collapsible-content'), subObj, rootPath);
            }
        });
        return ConfigUtils.cleanTempKey(result);
    }

    // 递归从DOM填充对象
    function fillObjectFromDom(parentEl, targetObj, pathPrefix) {
        // 基础输入框
        parentEl.querySelectorAll(':scope > .config-item').forEach(item => {
            const input = item.querySelector('[data-path]');
            if (!input) return;
            const path = input.dataset.path;
            if (!path.startsWith(pathPrefix)) return;
            const relativePath = path.slice(pathPrefix.length + 1);
            const type = input.dataset.type;
            let val;
            if (type === CONFIG_CONST.FIELD_TYPE_MAP.BOOLEAN) val = input.checked;
            else if (type === CONFIG_CONST.FIELD_TYPE_MAP.NUMBER) val = Number(input.value);
            else val = input.value;
            // 字段校验
            if (!ConfigUtils.validateField(type, val)) {
                console.warn(`字段格式非法 ${path}`, val);
            }
            ConfigUtils.setDeepValue(targetObj, relativePath, val);
        });
        // 标题规则数组
        parentEl.querySelectorAll(':scope > .title-change-list').forEach(list => {
            const arrPath = list.dataset.path;
            const arrKey = ConfigUtils.splitPath(arrPath).pop();
            const arr = [];
            list.querySelectorAll(':scope > .collapsible-content > .title-change-item').forEach(ruleItem => {
                const ruleObj = {};
                fillObjectFromDom(ruleItem.querySelector(':scope > .collapsible-content'), ruleObj, ruleItem.dataset.path);
                arr.push(ruleObj);
            });
            ConfigUtils.setDeepValue(targetObj, arrKey, arr);
        });
        // 嵌套子对象
        parentEl.querySelectorAll(':scope > .collapsible-section[data-kind="object"]').forEach(sub => {
            const subPath = sub.dataset.path;
            const subKey = ConfigUtils.splitPath(subPath).pop();
            const subObj = {};
            fillObjectFromDom(sub.querySelector(':scope > .collapsible-content'), subObj, subPath);
            ConfigUtils.setDeepValue(targetObj, subKey, subObj);
        });
    }

    // 加载配置
    async function loadConfig() {
        $.container.innerHTML = DomHelper.createTip(CONFIG_CONST.TEXT.LOADING, false, '#333').outerHTML;
        $.status.textContent = '';
        $.saveBtn.disabled = true;
        $.refreshBtn.disabled = true;
        try {
            const res = await fetch(CONFIG_CONST.API.GET_CONFIG);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            currentConfig = await res.json();
            // 统一给所有频道注入临时key、初始化title_change数组
            if (currentConfig.media) {
                CONFIG_CONST.CHANNEL_LIST.forEach(chanConf => {
                    const chanMap = currentConfig.media[chanConf.key];
                    if (!chanMap) return;
                    Object.values(chanMap).forEach(chanItem => {
                        if (!chanItem._tempKey) chanItem._tempKey = ConfigUtils.genTempKey();
                        if (!Array.isArray(chanItem.title_change)) chanItem.title_change = [];
                    });
                });
            }
            renderConfig(currentConfig, $.container);
            $.saveBtn.disabled = false;
        } catch (err) {
            console.error(CONFIG_CONST.TEXT.LOAD_FAIL, err);
            $.container.innerHTML = DomHelper.createTip(`${CONFIG_CONST.TEXT.LOAD_FAIL}: ${err.message}`, false, 'red').outerHTML;
            currentConfig = null;
        } finally {
            $.refreshBtn.disabled = false;
        }
    }

    // 保存配置
    async function saveConfig() {
        const finalData = collectConfig();
        console.log('最终提交配置', JSON.stringify(finalData, null, 2));
        $.status.textContent = CONFIG_CONST.TEXT.SAVING;
        $.status.style.color = 'orange';
        $.saveBtn.disabled = true;
        $.refreshBtn.disabled = true;
        try {
            const res = await fetch(CONFIG_CONST.API.SAVE_CONFIG, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(finalData)
            });
            if (!res.ok) {
                let msg = `HTTP ${res.status}`;
                try {
                    const errJson = await res.json();
                    msg = errJson.detail || errJson.message || JSON.stringify(errJson);
                } catch { msg = await res.text() || msg; }
                throw new Error(msg);
            }
            $.status.textContent = CONFIG_CONST.TEXT.SAVE_SUCCESS;
            $.status.style.color = 'green';
            setTimeout(loadConfig, 1500);
        } catch (err) {
            console.error(CONFIG_CONST.TEXT.SAVE_FAIL, err);
            $.status.textContent = `${CONFIG_CONST.TEXT.SAVE_FAIL}: ${err.message}`;
            $.status.style.color = 'red';
            $.saveBtn.disabled = false;
            $.refreshBtn.disabled = false;
        }
    }

    // 绑定按钮事件
    $.refreshBtn.addEventListener('click', loadConfig);
    $.saveBtn.addEventListener('click', saveConfig);

    // 对外暴露页面切换钩子
    window.podflowConfig = {
        onShow: () => {
            if (!currentConfig) return loadConfig();
            // 修复临时key与数组
            if (currentConfig.media) {
                CONFIG_CONST.CHANNEL_LIST.forEach(chanConf => {
                    const chanMap = currentConfig.media[chanConf.key];
                    if (!chanMap) return;
                    Object.values(chanMap).forEach(item => {
                        if (!item._tempKey) item._tempKey = ConfigUtils.genTempKey();
                        if (!Array.isArray(item.title_change)) item.title_change = [];
                    });
                });
            }
            renderConfig(currentConfig, $.container);
        },
        // 对外暴露工具，方便后续扩展
        utils: ConfigUtils,
        const: CONFIG_CONST
    };
});
