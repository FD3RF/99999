import requests
import json
import time
import sys
import os
from datetime import datetime

print("=" * 80)
print("ETHUSDT 量化系统 - 完整诊断")
print("=" * 80)
print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 结果收集
issues = []
warnings = []
success = []

# 1. 网络测试
print("\n[1/8] 网络连接测试")
print("-" * 80)

test_urls = [
    ("CoinEx", "https://api.coinex.com/v1/common/market/tickers?limit=1"),
    ("KuCoin", "https://api.kucoin.com/api/v1/timestamp"),
    ("Gate.io", "https://api.gateio.ws/api/v4/spot/time"),
    ("Binance", "https://api.binance.com/api/v3/ping"),
    ("Ollama AI", "http://localhost:11434/api/version"),
]

net_ok = 0
for name, url in test_urls:
    try:
        start = time.time()
        resp = requests.get(url, timeout=5)
        latency = (time.time() - start) * 1000
        if resp.status_code == 200:
            print(f"  [OK] {name:20} {latency:>6.0f}ms")
            success.append(f"{name} 正常")
            net_ok += 1
        else:
            print(f"  [FAIL] {name:20} HTTP {resp.status_code}")
            issues.append(f"{name} HTTP错误")
    except Exception as e:
        print(f"  [ERROR] {name:20} {str(e)[:30]}")
        issues.append(f"{name} 连接失败")

print(f"\n网络状态: {net_ok}/{len(test_urls)}")

# 2. CoinEx API 测试
print("\n[2/8] CoinEx API 测试")
print("-" * 80)

try:
    resp = requests.get(
        "https://api.coinex.com/v1/market/kline",
        params={"market": "ETHUSDT", "type": "5min", "limit": 10},
        timeout=10
    )
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get('code') == 0:
            kline = data.get('data', {}).get('data', [])
            if kline:
                latest = kline[0]
                print(f"  [OK] K线数据正常")
                print(f"       最新价格: ${float(latest[4]):.2f}")
                success.append("CoinEx K线正常")
            else:
                print(f"  [WARN] K线数据为空")
                warnings.append("K线数据为空")
        else:
            print(f"  [FAIL] API错误: {data.get('message')}")
            issues.append("CoinEx API错误")
    else:
        print(f"  [FAIL] HTTP {resp.status_code}")
        issues.append("CoinEx HTTP错误")
except Exception as e:
    print(f"  [ERROR] {str(e)[:50]}")
    issues.append(f"CoinEx异常: {str(e)[:30]}")

# 3. AI 服务测试
print("\n[3/8] AI 服务测试")
print("-" * 80)

try:
    # 检查服务
    resp = requests.get("http://localhost:11434/api/version", timeout=3)
    if resp.status_code == 200:
        version = resp.json().get('version', 'unknown')
        print(f"  [OK] Ollama v{version}")
        
        # 检查模型
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            deepseek = [m for m in models if 'deepseek' in m.get('name', '').lower()]
            
            if deepseek:
                print(f"  [OK] 找到 {len(deepseek)} 个DeepSeek模型:")
                for m in deepseek[:2]:
                    print(f"       - {m.get('name')}")
                success.append(f"{len(deepseek)}个AI模型可用")
                
                # 测试生成
                start = time.time()
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "deepseek-r1:1.5b",
                        "prompt": "回复OK",
                        "stream": False,
                        "options": {"num_predict": 5}
                    },
                    timeout=15
                )
                elapsed = time.time() - start
                
                if resp.status_code == 200:
                    print(f"  [OK] AI生成测试: {elapsed:.1f}秒")
                    success.append(f"AI响应{elapsed:.1f}秒")
                else:
                    print(f"  [WARN] AI生成测试失败")
                    warnings.append("AI生成测试失败")
            else:
                print(f"  [FAIL] 未找到DeepSeek模型")
                issues.append("缺少DeepSeek模型")
        else:
            print(f"  [WARN] 无法获取模型列表")
            warnings.append("模型列表获取失败")
    else:
        print(f"  [FAIL] Ollama服务未响应")
        issues.append("Ollama未运行")
        
except requests.exceptions.ConnectionError:
    print(f"  [FAIL] 无法连接Ollama")
    issues.append("Ollama服务未启动")
except Exception as e:
    print(f"  [ERROR] {str(e)[:50]}")
    issues.append(f"AI异常: {str(e)[:30]}")

# 4. 文件检查
print("\n[4/8] 文件检查")
print("-" * 80)

files = {
    "app_coinex.py": "CoinEx版",
    "app_fixed.py": "快速版",
    "requirements.txt": "依赖配置",
    ".streamlit/secrets.toml": "API密钥",
}

for fname, desc in files.items():
    if os.path.exists(fname):
        size = os.path.getsize(fname)
        print(f"  [OK] {fname:25} ({size} bytes)")
        success.append(f"{fname}存在")
    else:
        print(f"  [MISS] {fname:25}")
        issues.append(f"缺少{fname}")

# 5. API Key 检查
print("\n[5/8] API Key 检查")
print("-" * 80)

try:
    with open(".streamlit/secrets.toml", "r") as f:
        content = f.read()
        if "COINEX_ACCESS_ID" in content and "ck_" in content:
            print(f"  [OK] CoinEx API Key 已配置")
            success.append("API Key已配置")
        else:
            print(f"  [WARN] API Key 可能未正确配置")
            warnings.append("API Key待验证")
except:
    print(f"  [FAIL] 无法读取配置文件")
    issues.append("配置文件读取失败")

# 6. 进程检查
print("\n[6/8] 进程检查")
print("-" * 80)

import subprocess
try:
    result = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if ":8501" in result.stdout:
        print(f"  [OK] Streamlit 正在运行 (端口8501)")
        success.append("Streamlit运行中")
    else:
        print(f"  [INFO] Streamlit 未运行")
        print(f"       启动: streamlit run app_coinex.py")
except Exception as e:
    print(f"  [INFO] 无法检查进程状态")

# 7. 数据流测试
print("\n[7/8] 数据流测试")
print("-" * 80)

try:
    resp = requests.get(
        "https://api.coinex.com/v1/market/depth",
        params={"market": "ETHUSDT", "limit": 20, "merge": 0},
        timeout=10
    )
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get('code') == 0:
            depth = data.get('data', {})
            bids = depth.get('bids', [])
            asks = depth.get('asks', [])
            
            if bids and asks:
                bid_price = float(bids[0][0])
                ask_price = float(asks[0][0])
                spread = ask_price - bid_price
                
                print(f"  [OK] 订单簿正常")
                print(f"       买一: {bid_price:.2f} | 卖一: {ask_price:.2f}")
                print(f"       价差: {spread:.2f}")
                success.append("订单簿数据正常")
            else:
                print(f"  [WARN] 订单簿不完整")
        else:
            print(f"  [FAIL] API错误")
except Exception as e:
    print(f"  [ERROR] {str(e)[:50]}")
    issues.append("数据流测试失败")

# 8. 依赖包检查
print("\n[8/8] 依赖包检查")
print("-" * 80)

packages = ["streamlit", "pandas", "requests", "plotly"]
pkg_ok = 0

for pkg in packages:
    try:
        __import__(pkg)
        print(f"  [OK] {pkg:15} 已安装")
        pkg_ok += 1
    except ImportError:
        print(f"  [MISS] {pkg:15} 未安装")
        issues.append(f"缺少{pkg}")

print(f"\n依赖状态: {pkg_ok}/{len(packages)}")

# 总结
print("\n" + "=" * 80)
print("诊断总结")
print("=" * 80)

print(f"\n成功: {len(success)}")
for item in success[:5]:
    print(f"  ✅ {item}")

if warnings:
    print(f"\n警告: {len(warnings)}")
    for item in warnings[:3]:
        print(f"  ⚠️ {item}")

if issues:
    print(f"\n问题: {len(issues)}")
    for i, item in enumerate(issues, 1):
        print(f"  {i}. {item}")

print("\n" + "=" * 80)
if len(issues) == 0:
    print("✅ 系统状态: 完全健康")
    print("\n启动应用: streamlit run app_coinex.py")
elif len(issues) <= 2:
    print("⚠️ 系统状态: 基本可用")
    print("\n建议解决上述问题后运行")
else:
    print("❌ 系统状态: 需要修复")
    print("\n请先解决上述问题")
print("=" * 80)
