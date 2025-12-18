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
    """根路径：显示美化后的欢迎页面"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>手机号归属地查询 API</title>
        <style>
            /* 全局样式重置 */
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            }
            
            /* 页面背景 */
            body {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
                padding: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            /* 主容器 */
            .container {
                background: #ffffff;
                border-radius: 16px;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
                padding: 40px;
                max-width: 800px;
                width: 100%;
                border: 1px solid rgba(255, 255, 255, 0.8);
            }
            
            /* 标题样式 */
            .header {
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #e8f4f8;
                padding-bottom: 20px;
            }
            
            .header h1 {
                color: #2d3748;
                font-size: 2.2rem;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
            }
            
            .header h1 svg {
                width: 32px;
                height: 32px;
                fill: #4299e1;
            }
            
            .header p {
                color: #718096;
                font-size: 1.1rem;
            }
            
            /* 接口说明区域 */
            .api-section {
                margin: 25px 0;
            }
            
            .api-section h3 {
                color: #2d3748;
                font-size: 1.4rem;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .api-section h3 svg {
                width: 20px;
                height: 20px;
                fill: #38b2ac;
            }
            
            .api-list {
                list-style: none;
                margin: 20px 0;
            }
            
            .api-list li {
                background: #f7fafc;
                border-left: 4px solid #4299e1;
                padding: 15px 20px;
                margin-bottom: 12px;
                border-radius: 8px;
                transition: all 0.3s ease;
            }
            
            .api-list li:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            }
            
            .api-list li strong {
                color: #2d3748;
                font-size: 1.05rem;
                display: block;
                margin-bottom: 8px;
            }
            
            /* 代码样式 */
            code {
                background: #e8f4f8;
                color: #2b6cb0;
                padding: 4px 8px;
                border-radius: 6px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 0.95rem;
                word-break: break-all;
            }
            
            /* 示例链接 */
            .demo-link {
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e8f4f8;
            }
            
            .demo-link a {
                background: #4299e1;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                text-decoration: none;
                font-size: 1.1rem;
                transition: all 0.3s ease;
                display: inline-block;
            }
            
            .demo-link a:hover {
                background: #3182ce;
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(66, 153, 225, 0.3);
            }
            
            .demo-link p {
                color: #718096;
                margin-top: 10px;
                font-size: 0.95rem;
            }
            
            /* 响应式适配 */
            @media (max-width: 768px) {
                .container {
                    padding: 25px 20px;
                }
                
                .header h1 {
                    font-size: 1.8rem;
                }
                
                .api-section h3 {
                    font-size: 1.2rem;
                }
                
                .demo-link a {
                    padding: 10px 20px;
                    font-size: 1rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>
                    <svg viewBox="0 0 24 24">
                        <path d="M20 22h-2v-2c1.65-1.87 3-4.41 3-7 0-5.52-4.48-10-10-10S2 6.48 2 12c0 2.59 1.35 5.13 3 7v2H2v2h2v2h2v-2h8v2h2v-2h2v2h2v-2zm-10-9c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z"/>
                    </svg>
                    手机号归属地查询 API
                </h1>
                <p>✅ 服务已正常运行，接口可正常调用</p>
            </div>

            <div class="api-section">
                <h3>
                    <svg viewBox="0 0 24 24">
                        <path d="M11 9h2V6h3V4h-3V1h-2v3H8v2h3v3zm-4 9c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zm10 0c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2zm-9.83-3.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.86-7.01L19.42 4h-.01l-1.1 2-2.76 5H8.53l-.13-.27L6.16 6l-.95-2-.94-2H1v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.13 0-.25-.11-.25-.25z"/>
                    </svg>
                    接口说明
                </h3>
                <ul class="api-list">
                    <li>
                        <strong>查询接口</strong>
                        <code>GET /api/phone/location?phone=13800138000</code>
                    </li>
                    <li>
                        <strong>健康检查</strong>
                        <code>GET /api/health</code>
                    </li>
                </ul>
            </div>

            <div class="demo-link">
                <a href="/api/phone/location?phone=13800138000">📱 点击测试手机号查询</a>
                <p>💡 示例手机号：13800138000（可自行替换为其他11位手机号）</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/api/health")
def health_check():
    """健康检查接口"""
    return json_response({
        "status": "ok",
        "service": "phone-location-api",
        "data_loaded": len(SEG_MAP) > 0,
        "seg_7_count": len(SEG_MAP),
        "seg_3_count": len(SEG_PREFIX_MAP),
        "message": "服务正常运行中"
    })

@app.route("/api/phone/location", methods=["GET", "POST"])
def phone_location():
    """手机号归属地查询接口"""
    phone = (
        request.args.get("phone", "").strip()
        or request.form.get("phone", "").strip()
    )

    if not re.match(r"^1[3-9]\d{9}$", phone):
        return json_response({
            "code": 400,
            "msg": "请输入11位有效手机号（13/14/15/17/18/19开头）",
            "data": None
        }, 400)

    seg_7 = phone[:7]
    seg_3 = phone[:3]

    if seg_7 in SEG_MAP:
        city, operator = SEG_MAP[seg_7]
        result = {
            "phone": phone,
            "seg": seg_7,
            "seg_type": "7位号段",
            "city": city,
            "operator": operator
        }
    elif seg_3 in SEG_PREFIX_MAP:
        city, operator = SEG_PREFIX_MAP[seg_3]
        result = {
            "phone": phone,
            "seg": seg_3,
            "seg_type": "3位前缀",
            "city": city,
            "operator": operator
        }
    else:
        return json_response({
            "code": 404,
            "msg": "未查询到该号段归属地",
            "data": None
        }, 404)

    return json_response({
        "code": 200,
        "msg": "查询成功",
        "data": result
    })
