# 手机号归属地查询 API - 完整生产版（兼容 Python 3.12 + Flask 3.0.3）
import os
import csv
import re
import json
from flask import Flask, request, Response

# ---------------------- 初始化 Flask 应用 ----------------------
app = Flask(__name__)

# 启用 CORS（允许所有来源跨域请求）
from flask_cors import CORS
CORS(app, resources=r'/*')

# ---------------------- 自定义 JSON 响应（确保 UTF-8 中文）----------------------
def json_response(data, status=200):
    """返回 UTF-8 编码的 JSON 响应，不转义中文"""
    return Response(
        json.dumps(data, ensure_ascii=False, separators=(',', ':')),
        status=status,
        mimetype='application/json; charset=utf-8'
    )

# ---------------------- 路径配置 ----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_ROOT = os.path.join(BASE_DIR, "city")

SEG_MAP = {}          # {七位号段: (城市, 运营商)}
SEG_PREFIX_MAP = {}   # {三位前缀: (城市, 运营商)}

# ---------------------- 数据加载函数（完全保留你的逻辑）----------------------
def load_seg_data():
    """从 city/ 目录递归加载所有 CSV/TSV 号段文件"""
    print("=" * 60)
    print("🚀 开始加载手机号段数据...")
    print(f"📁 数据目录: {LOCAL_ROOT}")

    if not os.path.exists(LOCAL_ROOT):
        print("❌ 错误: city/ 目录不存在！请确保它与 api.py 在同一目录。")
        return

    city_folders = [f for f in os.listdir(LOCAL_ROOT) if os.path.isdir(os.path.join(LOCAL_ROOT, f))]
    print(f"✅ 发现 {len(city_folders)} 个城市文件夹")

    total_loaded = 0
    for city in city_folders:
        city_path = os.path.join(LOCAL_ROOT, city)
        csv_files = [f for f in os.listdir(city_path) if f.endswith(".csv")]
        
        for csv_file in csv_files:
            file_path = os.path.join(city_path, csv_file)
            try:
                # 自动检测分隔符：优先 \t，其次 ,
                with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    first_line = f.readline().strip()
                    delimiter = "\t" if "\t" in first_line else ","
                    f.seek(0)

                    reader = csv.DictReader(f, delimiter=delimiter)
                    headers = reader.fieldnames
                    if not headers:
                        continue

                    # 从文件名提取运营商
                    operator = ""
                    if "移动" in csv_file:
                        operator = "移动"
                    elif "电信" in csv_file:
                        operator = "电信"
                    elif "联通" in csv_file:
                        operator = "联通"
                    elif "广电" in csv_file:
                        operator = "广电"

                    if not operator:
                        print(f"⚠️  跳过文件（无法识别运营商）: {csv_file}")
                        continue

                    # 解析每一行的号段列
                    for row in reader:
                        for col in headers:
                            if col in ["省份", "运营商"]:
                                continue
                            seg_value = str(row.get(col, "")).strip()
                            if (
                                seg_value.isdigit()
                                and len(seg_value) == 7
                                and seg_value[0] == '1'
                                and seg_value[1] in '3456789'
                            ):
                                SEG_MAP[seg_value] = (city, operator)
                                SEG_PREFIX_MAP[seg_value[:3]] = (city, operator)
                                total_loaded += 1

            except Exception as e:
                print(f"❌ 加载失败 {file_path}: {e}")

    print(f"✅ 数据加载完成！共加载 {total_loaded} 个号段")
    print(f"   - 7位号段: {len(SEG_MAP)}")
    print(f"   - 3位前缀: {len(SEG_PREFIX_MAP)}")
    print("=" * 60)

# ---------------------- ✅ 关键：在模块顶层调用数据加载 ----------------------
load_seg_data()

# ---------------------- API 路由 ----------------------
@app.route("/")
def index():
    """根路径：显示美化后的查询页面"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>📱 手机号归属地查询</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4edf9 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 500px;
            padding: 32px;
            text-align: center;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 24px;
            font-size: 28px;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 14px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            border-color: #3498db;
        }
        button {
            background: #3498db;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 14px 24px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #2980b9;
        }
        .result {
            margin-top: 24px;
            padding: 16px;
            border-radius: 10px;
            background: #f8f9fa;
            text-align: left;
            display: none;
        }
        .result.show {
            display: block;
        }
        .result h3 {
            margin-bottom: 12px;
            color: #2c3e50;
        }
        .result p {
            margin: 6px 0;
            font-size: 15px;
            color: #555;
        }
        .error {
            color: #e74c3c;
        }
        footer {
            margin-top: 20px;
            font-size: 13px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 手机号归属地查询</h1>
        <div class="input-group">
            <input type="text" id="phoneInput" placeholder="请输入11位手机号" maxlength="11" />
            <button onclick="queryLocation()">查询</button>
        </div>
        <div class="result" id="resultBox"></div>
        <footer>Powered by Phone Location API · 支持 13/14/15/17/18/19 开头号码</footer>
    </div>

    <script>
        function queryLocation() {
            const phone = document.getElementById("phoneInput").value.trim();
            const resultBox = document.getElementById("resultBox");
            resultBox.className = "result";

            if (!/^1[3-9]\\d{9}$/.test(phone)) {
                resultBox.innerHTML = `<p class="error">❌ 请输入有效的11位手机号（13/14/15/17/18/19开头）</p>`;
                resultBox.classList.add("show");
                return;
            }

            fetch(`/api/phone/location?phone=${encodeURIComponent(phone)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.code === 200) {
                        const d = data.data;
                        resultBox.innerHTML = `
                            <h3>✅ 查询成功</h3>
                            <p><strong>手机号：</strong>${d.phone}</p>
                            <p><strong>匹配方式：</strong>${d.seg_type}（${d.seg}）</p>
                            <p><strong>归属地：</strong>${d.city}</p>
                            <p><strong>运营商：</strong>${d.operator}</p>
                        `;
                    } else {
                        resultBox.innerHTML = `<p class="error">⚠️ ${data.msg}</p>`;
                    }
                    resultBox.classList.add("show");
                })
                .catch(err => {
                    console.error(err);
                    resultBox.innerHTML = `<p class="error">❌ 网络错误，请稍后重试</p>`;
                    resultBox.classList.add("show");
                });
        }

        document.getElementById("phoneInput").addEventListener("keyup", (e) => {
            if (e.key === "Enter") queryLocation();
        });
    </script>
</body>
</html>
"""
