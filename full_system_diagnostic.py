import requests
import json
import time
import sys
import os
from datetime import datetime

print("=" * 80)
print("ETHUSDT 量化系统 - 完整诊断")
print("=" * 80)
print(f"诊断时间: {datetime.now().strftime('%Y-%m-% %d %H:%M:%S')}")

# 诊断结果收集
issues = []
warnings = []
success = []

def test_network():
    """测试网络连接"""
    print("\n[1/10] 网络连接测试")
    print("-" * 80)
    
    test_sites = [
        ("CoinEx API", "https://api.coinex.com/v1/common/market/tickers?limit=1"),
        ("KuCoin API", "https://api.kucoin.com/api/v1/timestamp"),
        ("Gate.io API", "https://api.gateio.ws/api/v4/spot/time"),
        ("Binance API", "https://api.binance.com/api/v3/ping"),
        ("DeepSeek API", "http://localhost:11434/api/version"),
    ]
    
    all_passed = True
    for name, url in test_sites:
        try:
            start = time.time()
            resp = requests.get(url, timeout=5)
            latency = (time.time() - start) * 1000
            
            if resp.status_code == 200:
                print(f"  [OK] {name:20} {latency:>6.0f}ms")
                success.append(f"{name} 连接正常")
            else:
                print(f"  [FAIL] {name:20} HTTP {resp.status_code}")
                issues.append(f"{name} HTTP {resp.status_code}")
                all_passed = False
        except Exception as e:
            print(f"  [ERROR] {name:20} {str(e)[:40]}")
            issues.append(f"{name} 连接失败: {str(e)[:40]}")
            all_passed = False
    
    return all_passed

def test_coinex_api():
    """测试 CoinEx API 功能"""
    print("\n[2/10] CoinEx API 功能测试")
    print("-" * 80)
    
    try:
        # 测试公共接口
        resp = requests.get(
            "https://api.coinex.com/v1/market/kline",
            params={"market": "ETHUSDT", "type": "5min", "limit": 10},
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('code') == 0:
                kline_data = data.get('data', {}).get('data', [])
                if kline_data:
                    latest = kline_data[0]
                    print(f"  [OK] K线数据获取成功")
                    print(f"       最新价格: ${float(latest[4]):.2f} USDT")
                    print(f"       数据条数: {len(kline_data)}")
                    success.append("CoinEx K线数据正常")
                    return True
                else:
                    print(f"  [WARN] K线数据为空")
                    warnings.append("CoinEx K线数据为空")
                    return False
            else:
                print(f"  [FAIL] API 返回错误: {data.get('message')}")
                issues.append(f"CoinEx API 错误: {data.get('message')}")
                return False
        else:
            print(f"  [FAIL] HTTP {resp.status_code}")
            issues.append(f"CoinEx HTTP {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"  [ERROR] {str(e)[:60]}")
        issues.append(f"CoinEx 异常: {str(e)[:60]}")
        return False

def test_ai_service():
    """测试 AI 服务"""
    print("\n[3/10] AI 服务测试")
    print("-" * 80)
    
    try:
        # 测试服务状态
        resp = requests.get("http://localhost:11434/api/version", timeout=3)
        
        if resp.status_code == 200:
            version = resp.json().get('version', 'unknown')
            print(f"  [OK] Ollama 服务运行中 (v{version})")
            
            # 测试模型列表
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get('models', [])
                deepseek_models = [m for m in models if 'deepseek' in m.get('name', '').lower()]
                
                if deepseek_models:
                    print(f"  [OK] 找到 {len(deepseek_models)} 个 DeepSeek 模型:")
                    for m in deepseek_models:
                        name = m.get('name', 'unknown')
                        size = m.get('size', 0) / (1024**3)
                        print(f"       - {name} ({size:.1f}GB)")
                    success.append(f"{len(deepseek_models)} 个 DeepSeek 模型可用")
                    
                    # 测试生成
                    print("\n  测试 AI 生成能力...")
                    start = time.time()
                    resp = requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": "deepseek-r1:1.5b",
                            "prompt": "用5个字回复",
                            "stream": False,
                            "options": {"num_predict": 10}
                        },
                        timeout=15
                    )
                    elapsed = time.time() - start
                    
                    if resp.status_code == 200:
                        print(f"  [OK] AI 生成成功 ({elapsed:.1f}秒)")
                        success.append(f"AI 响应时间: {elapsed:.1f}秒")
                        return True
                    else:
                        print(f"  [WARN] AI 生成失败: HTTP {resp.status_code}")
                        warnings.append("AI 生成测试失败")
                        return False
                else:
                    print(f"  [FAIL] 未找到 DeepSeek 模型")
                    issues.append("未安装 DeepSeek 模型")
                    return False
            else:
                print(f"  [WARN] 无法获取模型列表")
                warnings.append("无法获取 Ollama 模型列表")
                return False
        else:
            print(f"  [FAIL] Ollama 服务未响应")
            issues.append("Ollama 服务未运行")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] 无法连接到 Ollama")
        issues.append("Ollama 服务未启动")
        return False
    except Exception as e:
        print(f"  [ERROR] {str(e)[:60]}")
        issues.append(f"AI 服务错误: {str(e)[:60]}")
        return False

def check_files():
    """检查文件完整性"""
    print("\n[4/10] 文件完整性检查")
    print("-" * 80)
    
    required_files = {
        "app_coinex.py": "CoinEx 企业版应用",
        "app_fixed.py": "快速版应用",
        "requirements.txt": "依赖配置",
        ".streamlit/secrets.toml": "API 密钥配置",
    }
    
    all_exist = True
    for filename, desc in required_files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"  [OK] {filename:25} {desc:20} ({size} bytes)")
            success.append(f"{filename} 存在")
        else:
            print(f"  [MISS] {filename:25} {desc:20}")
            issues.append(f"缺少文件: {filename}")
            all_exist = False
    
    return all_exist

def check_api_keys():
    """检查 API Key 配置"""
    print("\n[5/10] API Key 配置检查")
    print("-" * 80)
    
    try:
        with open(".streamlit/secrets.toml", "r") as f:
            content = f.read()
            
            if "COINEX_ACCESS_ID" in content and "COINEX_SECRET_KEY" in content:
                # 检查是否为示例值
                if "your_" not in content.lower():
                    print(f"  [OK] CoinEx API Key 已配置")
                    # 验证格式
                    if "ck_" in content:
                        print(f"       Access ID 格式正确")
                        success.append("CoinEx API Key 配置正确")
                        return True
                    else:
                        print(f"  [WARN] Access ID 格式可能不正确")
                        warnings.append("API Key 格式待验证")
                        return True
                else:
                    print(f"  [WARN] 使用的是示例 API Key")
                    warnings.append("使用示例 API Key")
                    return False
            else:
                print(f"  [FAIL] API Key 配置不完整")
                issues.append("API Key 配置缺失")
                return False
                
    except FileNotFoundError:
        print(f"  [FAIL] secrets.toml 文件不存在")
        issues.append("secrets.toml 不存在")
        return False
    except Exception as e:
        print(f"  [ERROR] {str(e)[:60]}")
        issues.append(f"API Key 检查失败: {str(e)[:60]}")
        return False

def check_streamlit_process():
    """检查 Streamlit 进程"""
    print("\n[6/10] Streamlit 进程检查")
    print("-" * 80)
    
    import subprocess
    
    try:
        # Windows
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME", "eq python.exe"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "python.exe" in result.stdout:
            print(f"  [OK] Python 进程正在运行")
            
            # 检查端口
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if ":8501" in result.stdout:
                print(f"  [OK] Streamlit 端口 8501 正在监听")
                success.append("Streamlit 正在运行")
                return True
            else:
                print(f"  [INFO] Streamlit 端口未监听")
                print(f"       启动命令: streamlit run app_coinex.py")
                return False
        else:
            print(f"  [INFO] 未检测到 Python 进程")
            return False
            
    except Exception as e:
        print(f"  [ERROR] {str(e)[:60]}")
        return False

def check_code_syntax():
    """检查代码语法"""
    print("\n[7/10] 代码语法检查")
    print("-" * 80)
    
    files_to_check = ["app_coinex.py", "app_fixed.py"]
    all_valid = True
    
    for filename in files_to_check:
        if not os.path.exists(filename):
            continue
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 编译检查
            compile(code, filename, 'exec')
            print(f"  [OK] {filename:20} 语法正确")
            success.append(f"{filename} 语法检查通过")
            
        except SyntaxError as e:
            print(f"  [FAIL] {filename:20} 语法错误")
            print(f"       Line {e.lineno}: {e.msg}")
            issues.append(f"{filename} 第{e.lineno}行语法错误")
            all_valid = False
        except Exception as e:
            print(f"  [ERROR] {filename:20} {str(e)[:40]}")
            issues.append(f"{filename} 检查失败")
            all_valid = False
    
    return all_valid

def check_dependencies():
    """检查依赖包"""
    print("\n[8/10] Python 依赖检查")
    print("-" * 80)
    
    required_packages = [
        "streamlit", "pandas", "requests", "plotly",
        "streamlit_autorefresh", "urllib3"
    ]
    
    all_installed = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"  [OK] {package:25} 已安装")
            success.append(f"{package} 已安装")
        except ImportError:
            print(f"  [MISS] {package:25} 未安装")
            issues.append(f"缺少依赖: {package}")
            all_installed = False
    
    return all_installed

def check_memory_usage():
    """检查内存使用"""
    print("\n[9/10] 系统资源检查")
    print("-" * 80)
    
    try:
        import psutil
        
        mem = psutil.virtual_memory()
        print(f"  内存总量: {mem.total / (1024**3):.1f} GB")
        print(f"  已使用: {mem.used / (1024**3):.1f} GB ({mem.percent}%)")
        print(f"  可用: {mem.available / (1024**3):.1f} GB")
        
        if mem.percent > 90:
            print(f"  [WARN] 内存使用率过高 ({mem.percent}%)")
            warnings.append(f"内存使用率: {mem.percent}%")
        else:
            print(f"  [OK] 内存使用正常")
            success.append(f"内存使用: {mem.percent}%")
        
        # CPU
        cpu = psutil.cpu_percent(interval=1)
        print(f"  CPU 使用: {cpu}%")
        
        return True
        
    except ImportError:
        print(f"  [INFO] psutil 未安装，跳过资源检查")
        return True
    except Exception as e:
        print(f"  [ERROR] {str(e)[:60]}")
        return False

def test_data_fetch():
    """测试数据获取"""
    print("\n[10/10] 完整数据流测试")
    print("-" * 80)
    
    try:
        # 测试 CoinEx 数据流
        resp = requests.get(
            "https://api.coinex.com/v1/market/depth",
            params={"market": "ETHUSDT", "limit": 20, "merge": 0},
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('code') == 0:
                depth_data = data.get('data', {})
                bids = depth_data.get('bids', [])
                asks = depth_data.get('asks', [])
                
                if bids and asks:
                    bid_price = float(bids[0][0])
                    ask_price = float(asks[0][0])
                    spread = ask_price - bid_price
                    
                    print(f"  [OK] 订单簿数据获取成功")
                    print(f"       最高买价: {bid_price:.2f}")
                    print(f"       最低卖价: {ask_price:.2f}")
                    print(f"       买卖价差: {spread:.2f}")
                    success.append("订单簿数据正常")
                    return True
                else:
                    print(f"  [WARN] 订单簿数据不完整")
                    warnings.append("订单簿数据不完整")
                    return False
            else:
                print(f"  [FAIL] API 返回错误")
                return False
        else:
            print(f"  [FAIL] HTTP {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"  [ERROR] {str(e)[:60]}")
        issues.append(f"数据流测试失败: {str(e)[:60]}")
        return False

# 运行所有测试
print("\n开始完整系统诊断...\n")

results = {
    "网络连接": test_network(),
    "CoinEx API": test_coinex_api(),
    "AI 服务": test_ai_service(),
    "文件完整": check_files(),
    "API Key": check_api_keys(),
    "Streamlit": check_streamlit_process(),
    "代码语法": check_code_syntax(),
    "Python依赖": check_dependencies(),
    "系统资源": check_memory_usage(),
    "数据流": test_data_fetch(),
}

# 生成报告
print("\n" + "=" * 80)
print("诊断报告")
print("=" * 80)

passed = sum(1 for v in results.values() if v)
total = len(results)

print(f"\n测试项目: {passed}/{total} 通过")

for test_name, result in results.items():
    status = "[PASS]" if result else "[FAIL]"
    print(f"  {status} {test_name}")

if success:
    print(f"\n成功项 ({len(success)}):")
    for item in success[:5]:
        print(f"  ✅ {item}")

if warnings:
    print(f"\n警告项 ({len(warnings)}):")
    for item in warnings[:5]:
        print(f"  ⚠️ {item}")

if issues:
    print(f"\n问题项 ({len(issues)}):")
    for i, item in enumerate(issues, 1):
        print(f"  {i}. {item}")
    
    print("\n" + "=" * 80)
    if passed == total:
        print("✅ 系统状态: 完全健康")
        print("\n可以安全运行应用！")
        print("启动命令: streamlit run app_coinex.py")
    elif passed >= total * 0.7:
        print("⚠️ 系统状态: 基本可用")
        print("\n建议解决上述警告后再运行")
    else:
        print("❌ 系统状态: 存在问题")
        print("\n请先解决上述问题:")
    
    print("=" * 80)
