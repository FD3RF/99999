#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ETHUSDT 量化系统 - 完整诊断工具
排查所有可能的问题并提供解决方案
"""

import os
import sys
import subprocess
import requests
import json
from datetime import datetime

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def print_section(title):
    """打印章节标题"""
    print(f"\n{'─' * 70}")
    print(f" {title}")
    print('─' * 70)

def check_python_version():
    """检查 Python 版本"""
    print_section("1. Python 环境检查")
    version = sys.version_info
    print(f"Python 版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("✅ Python 版本符合要求 (>= 3.8)")
        return True
    else:
        print("❌ Python 版本过低，需要 >= 3.8")
        return False

def check_required_packages():
    """检查必需的 Python 包"""
    print_section("2. Python 包检查")
    
    required_packages = {
        'streamlit': '1.28.0',
        'pandas': '2.0.0',
        'numpy': '1.24.0',
        'requests': '2.31.0',
        'plotly': '5.17.0'
    }
    
    all_ok = True
    for package, min_version in required_packages.items():
        try:
            module = __import__(package)
            version = getattr(module, '__version__', '未知')
            print(f"✅ {package}: {version}")
        except ImportError:
            print(f"❌ {package}: 未安装")
            all_ok = False
    
    return all_ok

def check_streamlit_process():
    """检查 Streamlit 进程"""
    print_section("3. Streamlit 进程检查")
    
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        lines = result.stdout.split('\n')
        streamlit_found = False
        
        for line in lines:
            if ':8501' in line and 'LISTENING' in line:
                parts = line.split()
                pid = parts[-1]
                print(f"✅ Streamlit 正在运行 (PID: {pid}, 端口: 8501)")
                streamlit_found = True
                break
        
        if not streamlit_found:
            print("⚠️ Streamlit 未在端口 8501 运行")
            print("   启动命令: streamlit run app_coinex.py")
        
        return streamlit_found
        
    except Exception as e:
        print(f"❌ 检查进程失败: {e}")
        return False

def check_api_connectivity():
    """检查 API 连接"""
    print_section("4. API 连接测试")
    
    apis = [
        ("CoinEx", "https://api.coinex.com/v1/common/market/tickers"),
        ("Binance", "https://api.binance.com/api/v3/ping"),
        ("KuCoin", "https://api.kucoin.com/api/v1/status"),
        ("DeepSeek AI", "http://localhost:11434/api/tags")
    ]
    
    available_apis = []
    
    for name, url in apis:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print(f"✅ {name}: 连接正常 ({resp.elapsed * 1000:.0f}ms)")
                available_apis.append(name)
            else:
                print(f"⚠️ {name}: HTTP {resp.status_code}")
        except requests.exceptions.Timeout:
            print(f"❌ {name}: 超时")
        except requests.exceptions.ConnectionError:
            print(f"❌ {name}: 连接失败")
        except Exception as e:
            print(f"❌ {name}: {type(e).__name__}")
    
    return len(available_apis) > 0

def check_secrets_file():
    """检查配置文件"""
    print_section("5. 配置文件检查")
    
    secrets_path = ".streamlit/secrets.toml"
    
    if os.path.exists(secrets_path):
        print(f"✅ 配置文件存在: {secrets_path}")
        
        try:
            with open(secrets_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 检查必需的配置项
            required_keys = [
                'COINEX_ACCESS_ID',
                'COINEX_SECRET_KEY'
            ]
            
            all_configured = True
            for key in required_keys:
                if key in content:
                    # 只显示是否配置，不显示实际值
                    print(f"✅ {key}: 已配置")
                else:
                    print(f"❌ {key}: 未配置")
                    all_configured = False
            
            # 检查可选配置
            if 'DEEPSEEK_API_KEY' in content:
                print("✅ DEEPSEEK_API_KEY: 已配置（AI 功能可用）")
            else:
                print("ℹ️ DEEPSEEK_API_KEY: 未配置（AI 功能不可用）")
            
            return all_configured
            
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return False
    else:
        print(f"❌ 配置文件不存在: {secrets_path}")
        print("   需要创建配置文件")
        return False

def check_git_status():
    """检查 Git 状态"""
    print_section("6. Git 状态检查")
    
    try:
        # 检查是否在 Git 仓库中
        result = subprocess.run(
            ['git', 'status'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ Git 仓库正常")
            
            # 检查远程仓库
            result = subprocess.run(
                ['git', 'remote', '-v'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'origin' in result.stdout:
                print("✅ 远程仓库已配置")
                # 提取仓库 URL
                for line in result.stdout.split('\n'):
                    if 'origin' in line and 'fetch' in line:
                        url = line.split()[1]
                        print(f"   仓库: {url}")
            else:
                print("⚠️ 远程仓库未配置")
            
            # 检查未提交的更改
            result = subprocess.run(
                ['git', 'status', '--short'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.stdout.strip():
                print("⚠️ 有未提交的更改:")
                print(result.stdout)
            else:
                print("✅ 工作区干净")
            
            return True
        else:
            print("❌ 不在 Git 仓库中")
            return False
            
    except Exception as e:
        print(f"❌ Git 检查失败: {e}")
        return False

def check_kline_data():
    """测试 K 线数据获取"""
    print_section("7. K线数据测试")
    
    try:
        # 测试 CoinEx API
        url = "https://api.coinex.com/v1/market/kline"
        params = {
            "market": "ETHUSDT",
            "type": "5min",
            "limit": 10
        }
        
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            
            if 'data' in data and len(data['data']) > 0:
                klines = data['data']
                first = klines[0]
                
                print(f"✅ K线数据获取成功")
                print(f"   数据条数: {len(klines)}")
                print(f"   列数: {len(first)}")
                print(f"   最新价格: ${first[4]} USDT")
                print(f"   时间: {datetime.fromtimestamp(first[0])}")
                
                # 检查数据格式
                if len(first) == 7:
                    print("✅ 数据格式正确 (7列)")
                else:
                    print(f"⚠️ 数据格式异常: 期望7列，实际{len(first)}列")
                
                return True
            else:
                print("❌ K线数据为空")
                return False
        else:
            print(f"❌ API 请求失败: HTTP {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ K线数据获取失败: {e}")
        return False

def check_ai_service():
    """检查 AI 服务"""
    print_section("8. AI 服务检查")
    
    # 检查 Ollama
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            models = data.get('models', [])
            
            print(f"✅ Ollama 服务运行中")
            print(f"   可用模型数: {len(models)}")
            
            # 检查是否有 DeepSeek 模型
            deepseek_models = [m for m in models if 'deepseek' in m.get('name', '').lower()]
            
            if deepseek_models:
                print(f"✅ DeepSeek 模型: {len(deepseek_models)} 个")
                for model in deepseek_models:
                    print(f"   - {model['name']}")
            else:
                print("ℹ️ 未找到 DeepSeek 模型")
                print("   下载命令: ollama pull deepseek-r1:1.5b")
            
            return True
        else:
            print(f"⚠️ Ollama 响应异常: HTTP {resp.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("ℹ️ Ollama 服务未运行")
        print("   启动命令: ollama serve")
        
        # 检查是否配置了 DeepSeek API
        if os.path.exists(".streamlit/secrets.toml"):
            with open(".streamlit/secrets.toml", 'r', encoding='utf-8') as f:
                if 'DEEPSEEK_API_KEY' in f.read():
                    print("✅ DeepSeek API Key 已配置（可使用在线 AI）")
                    return True
        
        return False
    except Exception as e:
        print(f"❌ AI 服务检查失败: {e}")
        return False

def generate_report():
    """生成诊断报告"""
    print_header("ETHUSDT 量化系统 - 完整诊断报告")
    
    print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行所有检查
    results = {
        "Python 环境": check_python_version(),
        "Python 包": check_required_packages(),
        "Streamlit 进程": check_streamlit_process(),
        "API 连接": check_api_connectivity(),
        "配置文件": check_secrets_file(),
        "Git 状态": check_git_status(),
        "K线数据": check_kline_data(),
        "AI 服务": check_ai_service()
    }
    
    # 生成总结
    print_header("诊断总结")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n通过项: {passed}/{total}")
    
    for item, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {item}")
    
    print("\n" + "=" * 70)
    
    if passed == total:
        print("🎉 所有检查通过！系统状态良好！")
    elif passed >= total * 0.7:
        print("⚠️ 大部分检查通过，但存在一些问题需要解决")
    else:
        print("❌ 发现多个问题，请根据上述提示进行修复")
    
    print("=" * 70)
    
    # 提供快速修复建议
    if passed < total:
        print("\n快速修复建议:")
        
        if not results["Python 包"]:
            print("  • 安装依赖: pip install -r requirements.txt")
        
        if not results["Streamlit 进程"]:
            print("  • 启动应用: streamlit run app_coinex.py")
        
        if not results["配置文件"]:
            print("  • 创建配置: 参考 .streamlit/secrets.toml.example")
        
        if not results["AI 服务"]:
            print("  • 启用 AI: ollama serve 或配置 DEEPSEEK_API_KEY")

if __name__ == "__main__":
    try:
        generate_report()
    except KeyboardInterrupt:
        print("\n\n诊断已取消")
    except Exception as e:
        print(f"\n\n诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
