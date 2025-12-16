# 手机号归属地查询API - 云端部署适配版
import os
import csv
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

# ---------------------- 核心配置 ----------------------
app = Flask(__name__)
CORS(app, resources=r'/*')  # 允许所有跨域请求

# ✅ 动态获取项目根目录，city 文件夹需与 api.py 同级
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_ROOT = os.path.join(BASE_DIR, "city")

SEG_MAP = {}          # {七位号段: (城市, 运营商)}
SEG_PREFIX_MAP = {}   # {三位前缀: (城市, 运营商)}

# ---------------------- 号段数据加载 ----------------------
def load_seg_data():
    """从 city/ 目录加载所有省份的运营商号段数据（支持 .csv，制表符或逗号分隔）"""
    print("=" * 60)
    print("🚀 开始加载手机号段数据...")
    print(f"📁 数据根目录: {LOCAL_ROOT}")

    if not os.path.exists(LOCAL_ROOT):
        print("❌ 错误: city/ 目录不存在！请确保它与 api.py 在同一文件夹。")
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
                # 自动检测分隔符（优先 \t，其次 ,）
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

                    # 遍历每一行
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

# ---------------------- API 接口 ----------------------

@app.route("/api/phone/location", methods=["GET", "POST"])
def phone_location():
    """查询手机号归属地"""
    phone = (
        request.args.get("phone", "").strip()
        or request.form.get("phone", "").strip()
    )

    if not re.match(r"^1[3-9]\d{9}$", phone):
        return jsonify({
            "code": 400,
            "msg": "请输入11位有效手机号（13/14/15/17/18/19开头）",
            "data": None
        })

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
        })

    return jsonify({
        "code": 200,
        "msg": "查询成功",
        "data": result
    })

@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查接口（用于验证服务是否正常运行）"""
    return jsonify({
        "status": "ok",
        "service": "phone-location-api",
        "data_loaded": len(SEG_MAP) > 0,
        "seg_7_count": len(SEG_MAP),
        "seg_3_count": len(SEG_PREFIX_MAP)
    })

# ---------------------- 启动入口 ----------------------
if __name__ == "__main__":
    load_seg_data()  # 启动时加载数据
    
    # 从环境变量读取端口（Render / 云平台会设置 PORT）
    port = int(os.environ.get("PORT", 5001))
    
    # host='0.0.0.0' 允许外部访问，debug=False 适合生产环境
    app.run(host="0.0.0.0", port=port, debug=False)
