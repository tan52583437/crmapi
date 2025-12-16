# 手机号归属地查询 API - 完整生产版（适配 Render + gunicorn）
import os
import csv
import re
from flask import Flask, request, jsonify

# ---------------------- 初始化 Flask 应用 ----------------------
app = Flask(__name__)

# 启用 CORS（允许所有来源跨域请求）
from flask_cors import CORS
CORS(app, resources=r'/*')

# ---------------------- 路径配置 ----------------------
# 自动定位 city/ 目录（与 api.py 同级）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_ROOT = os.path.join(BASE_DIR, "city")

# 全局号段映射
SEG_MAP = {}          # {七位号段: (城市, 运营商)}
SEG_PREFIX_MAP = {}   # {三位前缀: (城市, 运营商)}

# ---------------------- 数据加载函数 ----------------------
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
    """根路径：显示欢迎页面"""
    return """
    <html>
    <head>
        <title>手机号归属地查询 API</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; padding: 40px; background: #f9f9f9; }
            h1 { color: #2c3e50; }
            code { background: #eee; padding: 2px 6px; border-radius: 4px; }
            ul { line-height: 1.6; }
        </style>
    </head>
    <body>
        <h1>📞 手机号归属地查询 API</h1>
        <p>服务已正常运行！</p>
        <h3>📌 接口说明</h3>
        <ul>
            <li><strong>查询接口：</strong> 
                <code>GET /api/phone/location?phone=13800138000</code>
            </li>
            <li><strong>健康检查：</strong> 
                <code>GET /api/health</code>
            </li>
        </ul>
        <p>💡 示例：<a href="/api/phone/location?phone=13800138000">点击测试查询</a></p>
    </body>
    </html>
    """

@app.route("/api/health")
def health_check():
    """健康检查接口"""
    return jsonify({
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
        return jsonify({
            "code": 400,
            "msg": "请输入11位有效手机号（13/14/15/17/18/19开头）",
            "data": None
        }), 400

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
        return jsonify({
            "code": 404,
            "msg": "未查询到该号段归属地",
            "data": None
        }), 404

    return jsonify({
        "code": 200,
        "msg": "查询成功",
        "data": result
    })
