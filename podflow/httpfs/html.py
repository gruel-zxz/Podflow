# podflow/httpfs/html.py
# coding: utf-8


html_index = '''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>输入输出示例</title>
    <style>
        /* 基本样式 */
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 20px;
            background-color: #f8f9fa;
        }

        h2 {
            color: #333;
        }

        /* 响应式输入框 */
        textarea { 
            width: 90%; 
            max-width: 600px; 
            height: 250px; /* 增加默认高度 */
            font-size: 16px; 
            padding: 10px; 
            border: 1px solid #ccc; 
            border-radius: 8px; 
            resize: vertical; /* 允许手动调整高度 */
            overflow-y: auto; /* 始终显示垂直滚动条（如需自动出现滚动条，可用 `overflow-y: auto;`） */
        }

        /* 按钮样式 */
        .button-container {
            margin-top: 10px;
        }

        button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 12px 18px;
            font-size: 16px;
            border-radius: 6px;
            cursor: pointer;
            transition: 0.3s;
            box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.2);
            margin: 5px;
        }

        button:hover {
            background-color: #0056b3;
        }

        /* 手机端优化 */
        @media (max-width: 600px) {
            textarea {
                font-size: 18px;
                height: 180px;
            }

            button {
                width: 90%;
                font-size: 18px;
                padding: 14px;
            }
        }

        /* 提示信息 */
        .hint {
            font-size: 14px;
            color: #666;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <h2>获取Channel-ID</h2>
    <form id="inputForm" method="post">
        <label for="inputOutput">请输入：</label><br>
        <textarea name="inputOutput" id="inputOutput">{{ processed_input }}</textarea><br>
        <div class="button-container">
            <button type="button" onclick="pasteFromClipboard()">📋 粘贴</button>
            <button type="submit">✅ 提交</button>
            <button type="button" onclick="copyText()">📄 拷贝</button>
            <button type="button" onclick="clearInput()">🗑️ 清空</button>
        </div>
        <p class="hint">📌 如果粘贴按钮无效，请长按输入框手动粘贴。</p>
    </form>
    <script>
        function pasteFromClipboard() {
            let inputOutput = document.getElementById('inputOutput');

            if (navigator.clipboard && navigator.clipboard.readText) {
                navigator.clipboard.readText().then(text => {
                    inputOutput.value = text;
                    inputOutput.focus(); // 聚焦输入框
                    //alert("✅ 已成功粘贴！");
                }).catch(err => {
                    console.warn("❌ 剪贴板读取失败:", err);
                    alert("❌ 无法读取剪贴板，请手动粘贴！");
                });
            } else {
                // 兼容旧版浏览器
                try {
                    inputOutput.focus();
                    document.execCommand('paste'); // 仅部分浏览器支持
                    //alert("✅ 尝试使用旧版粘贴方法！");
                } catch (err) {
                    console.warn("❌ execCommand 粘贴失败:", err);
                    alert("❌ 您的浏览器不支持自动粘贴，请手动操作！");
                }
            }
        }
        function copyText() {
            let inputOutput = document.getElementById('inputOutput');
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(inputOutput.value).then(() => {
                    //alert("✅ 已拷贝到剪贴板！");
                }).catch(err => {
                    console.warn("拷贝失败:", err);
                    alert("❌ 无法拷贝，请手动选择文本后按 Ctrl+C 复制！");
                });
            } else {
                // 兼容旧版浏览器
                try {
                    inputOutput.select();
                    document.execCommand('copy');
                    //alert("✅ 已拷贝到剪贴板！");
                } catch (err) {
                    console.warn("execCommand 复制失败:", err);
                    alert("❌ 您的浏览器不支持拷贝，请手动操作！");
                }
            }
        }
        function clearInput() {
            document.getElementById('inputOutput').value = '';
        }
    </script>
</body>
</html>'''