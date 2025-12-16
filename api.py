# 手机号归属地查询API（最终适配版，支持制表符分隔CSV）
import os
import csv
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

# ---------------------- 核心配置 ----------------------
app = Flask(__name__)
CORS(app, resources=r'/*')  # 强制允许所有跨域
LOCAL_ROOT = r"d:\crm1209\apifile\city"
SEG_MAP = {}  # {七位号段: (城市, 运营商)}
SEG_PREFIX_MAP = {}  # {三位号段: (城市, 运营商)} - 兼容旧查询方式

# ---------------------- 适配TSV/CSV的号段加载逻辑 ----------------------
def load_seg_data():
    """读取制表符/逗号分隔的CSV，适配表头：省份	运营商	133 号段	153 号段..."""
    print("="*60)
    #print("开始加载号段数据（适配制表符分隔格式）...")
    #print(f"号段根目录：{LOCAL_ROOT}")
    
    # 1. 校验根目录
    if not os.path.exists(LOCAL_ROOT):
        print(f"❌ 根目录不存在：{LOCAL_ROOT}")
        return
    
    # 2. 遍历城市文件夹
    city_folders = [f for f in os.listdir(LOCAL_ROOT) if os.path.isdir(os.path.join(LOCAL_ROOT, f))]
    #print(f"✅ 找到城市文件夹：{city_folders}")
    
    total_seg = 0
    for city in city_folders:
        city_path = os.path.join(LOCAL_ROOT, city)
        csv_files = [f for f in os.listdir(city_path) if f.endswith(".csv")]
        #print(f"\n📂 处理城市：{city}，CSV文件：{csv_files}")
        
        for csv_file in csv_files:
            file_path = os.path.join(city_path, csv_file)
           # print(f"\n🔍 读取文件：{file_path}")
            
            # 3. 读取TSV/CSV（优先制表符分隔，兼容逗号）
            try:
                # 尝试制表符分隔（你的格式）
                with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    # 先读取第一行表头，确认分隔符
                    first_line = f.readline().strip()
                    delimiter = "\t" if "\t" in first_line else ","
                    f.seek(0)  # 回到文件开头
                    
                    # 读取CSV/TSV
                    reader = csv.DictReader(f, delimiter=delimiter)
                    headers = reader.fieldnames
                    #print(f"✅ 分隔符：{delimiter}，表头：{headers}")
                    
                    # 4. 提取运营商（从文件名/表头第二列）
                    operator = ""
                    # 方式1：从文件名提取
                    if "移动" in csv_file:
                        operator = "移动"
                    elif "电信" in csv_file:
                        operator = "电信"
                    elif "联通" in csv_file:
                        operator = "联通"
                    # 方式2：从表头第二列（运营商列）提取
                    elif len(headers) >= 2 and headers[1] == "运营商":
                        # 读取第一行数据的运营商列
                        first_row = next(reader)
                        operator = first_row.get("运营商", "").strip()
                        f.seek(0)  # 重置读取位置
                        # 重新创建reader对象
                        reader = csv.DictReader(f, delimiter=delimiter)
                    
                    if not operator:
                        print(f"⚠️ 未提取到运营商，跳过该文件")
                        continue
                    #print(f"✅ 提取运营商：{operator}")
                    
                    # 5. 遍历数据行
                    for row in reader:
                        # 6. 遍历每个号段列（跳过“省份”“运营商”列）
                        for col in headers:
                            if col in ["省份", "运营商"]:
                                continue  # 跳过非号段列
                            
                            # 获取单元格值（具体号段）
                            seg_value = row.get(col, "").strip()
                            if not seg_value:
                                continue  # 跳过空值
                            
                            # 检查是否为有效的七位手机号段
                            if seg_value.isdigit() and len(seg_value) == 7:
                                # 直接检查第一位是否为1，第二位是否为3-9
                                if seg_value[0] == '1' and seg_value[1] in '3456789':
                                    # 存储完整的7位号段
                                    SEG_MAP[seg_value] = (city, operator)
                                    
                                    # 同时存储3位前缀以保持兼容性
                                    seg_prefix = seg_value[:3]
                                    SEG_PREFIX_MAP[seg_prefix] = (city, operator)
                                    
                                    total_seg += 1
                                    #print(f"   ✅ 号段：{seg_value} → {city}-{operator}")
                            
            except Exception as e:
                print(f"❌ 读取失败：{str(e)}")
    
    print("="*60)
    print(f"加载完成！")
    print(f"七位号段数：{len(SEG_MAP)}")
    print(f"三位前缀数：{len(SEG_PREFIX_MAP)}")
    print("="*60)

# ---------------------- API接口 ----------------------
@app.route("/api/phone/location", methods=["GET", "POST"])
def phone_location():
    phone = request.args.get("phone", "").strip() or request.form.get("phone", "").strip()
    print(f"\n查询手机号：{phone}")
    
    # 校验手机号
    if not re.match(r"^1[3-9]\d{9}$", phone):
        return jsonify({"code":400, "msg":"请输入11位手机号（13/14/15/17/18/19开头）", "data":None})
    
    # 匹配号段（优先7位，再3位）
    seg_7 = phone[:7]  # 提取7位号段
    seg_3 = phone[:3]  # 提取3位前缀
    
    if seg_7 in SEG_MAP:
        city, operator = SEG_MAP[seg_7]
        return jsonify({
            "code":200,
            "msg":"查询成功",
            "data":{"phone":phone, "seg":seg_7, "seg_type":"7位号段", "city":city, "operator":operator}
        })
    elif seg_3 in SEG_PREFIX_MAP:
        city, operator = SEG_PREFIX_MAP[seg_3]
        return jsonify({
            "code":200,
            "msg":"查询成功",
            "data":{"phone":phone, "seg":seg_3, "seg_type":"3位前缀", "city":city, "operator":operator}
        })
    else:
        return jsonify({"code":404, "msg":"未查询到该号段归属地", "data":None})

# ---------------------- 测试接口 ----------------------
@app.route("/api/test", methods=["GET"])
def test():
    return jsonify({
        "code":200,
        "msg":"API正常",
        "data":{
            "seg_7_count":len(SEG_MAP),
            "seg_3_count":len(SEG_PREFIX_MAP),
            "seg_map_sample":dict(list(SEG_MAP.items())[:10]),  # 只显示前10个
            "root_path":LOCAL_ROOT,
            "path_exists":os.path.exists(LOCAL_ROOT)
        }
    })

# ---------------------- 启动 ----------------------
if __name__ == "__main__":
    load_seg_data()
    # 端口改为5001（避免5000被占用）
    app.run(host="0.0.0.0", port=5001, debug=False)