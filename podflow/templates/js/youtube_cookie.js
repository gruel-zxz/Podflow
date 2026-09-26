// /templates/js/youtube_cookie.js
(function() {
    const API_URL = '/youtube-cookie-file';

    const $ = {
        page: document.getElementById('pageYoutubeCookie'),
        editor: document.getElementById('youtubeCookieEditor'),
        refreshBtn: document.getElementById('refreshYoutubeCookieBtn'),
        saveBtn: document.getElementById('saveYoutubeCookieBtn'),
        status: document.getElementById('youtubeCookieStatus')
    };

    let hasLoaded = false;

    function setStatus(text, color) {
        if (!$.status) return;
        $.status.textContent = text;
        $.status.style.color = color || 'green';
    }

    async function loadCookieFile() {
        if (!$.editor) return;
        setStatus('正在读取 Cookie 文件...', 'orange');
        $.editor.disabled = true;
        if ($.refreshBtn) $.refreshBtn.disabled = true;
        if ($.saveBtn) $.saveBtn.disabled = true;

        try {
            const res = await fetch(API_URL);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            $.editor.value = data.content || '';
            setStatus('Cookie 文件读取成功', 'green');
        } catch (err) {
            console.error('读取 YouTube Cookie 文件失败:', err);
            setStatus(`读取失败: ${err.message}`, 'red');
        } finally {
            $.editor.disabled = false;
            if ($.refreshBtn) $.refreshBtn.disabled = false;
            if ($.saveBtn) $.saveBtn.disabled = false;
        }
    }

    async function saveCookieFile() {
        if (!$.editor) return;
        const content = $.editor.value;
        setStatus('正在保存 Cookie 文件...', 'orange');
        $.editor.disabled = true;
        if ($.refreshBtn) $.refreshBtn.disabled = true;
        if ($.saveBtn) $.saveBtn.disabled = true;

        try {
            const res = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: content })
            });
            if (!res.ok) {
                let msg = `HTTP ${res.status}`;
                try {
                    const errJson = await res.json();
                    msg = errJson.error || msg;
                } catch { /* ignore */ }
                throw new Error(msg);
            }
            setStatus('Cookie 文件保存成功', 'green');
            // 保存成功后刷新 YouTube Cookie 开关的可用状态
            if (window.loadYoutubeCookieSetting) {
                window.loadYoutubeCookieSetting();
            }
        } catch (err) {
            console.error('保存 YouTube Cookie 文件失败:', err);
            setStatus(`保存失败: ${err.message}`, 'red');
        } finally {
            $.editor.disabled = false;
            if ($.refreshBtn) $.refreshBtn.disabled = false;
            if ($.saveBtn) $.saveBtn.disabled = false;
        }
    }

    function init() {
        if (!$.page || !$.editor) {
            console.warn('YouTube Cookie 文件页面元素未找到');
            return;
        }

        if ($.refreshBtn) {
            $.refreshBtn.addEventListener('click', loadCookieFile);
        }
        if ($.saveBtn) {
            $.saveBtn.addEventListener('click', saveCookieFile);
        }

        // 对外暴露页面切换钩子
        window.podflowYoutubeCookie = {
            onShow: () => {
                if (!hasLoaded) {
                    hasLoaded = true;
                    loadCookieFile();
                }
            },
            reload: loadCookieFile
        };
    }

    document.addEventListener('DOMContentLoaded', init);
})();
