import requests
import json
import sys
import subprocess
import os

print("=" * 80)
print("AI 服务诊断 - DeepSeek-R1 (Ollama)")
print("=" * 80)

# 测试步骤
def test_ollama_installed():
    """测试 Ollama 是否已安装"""
    print("\n[步骤 1] 检查 Ollama 是否已安装")
    print("-" * 80)
    
    try:
        # 尝试运行 ollama --version
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("  [OK] Ollama 已安装")
            print(f"       版本信息: {result.stdout.strip()}")
            return True
        else:
            print("  [FAIL] Ollama 未正确安装")
            return False
            
    except FileNotFoundError:
        print("  [FAIL] Ollama 未安装")
        print("         找不到 'ollama' 命令")
        return False
    except Exception as e:
        print(f"  [FAIL] 检查失败: {str(e)}")
        return False

def test_ollama_service():
    """测试 Ollama 服务是否运行"""
    print("\n[步骤 2] 检查 Ollama 服务状态")
    print("-" * 80)
    
    try:
        resp = requests.get("http://localhost:11434/api/version", timeout=3)
        
        if resp.status_code == 200:
            data = resp.json()
            print("  [OK] Ollama 服务正在运行")
            print(f"       服务版本: {data.get('version', 'unknown')}")
            return True
        else:
            print(f"  [FAIL] 服务响应异常: HTTP {resp.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("  [FAIL] 无法连接到 Ollama 服务")
        print("         服务未启动或端口被占用")
        return False
    except Exception as e:
        print(f"  [FAIL] 连接失败: {str(e)}")
        return False

def test_model_exists():
    """测试 DeepSeek 模型是否已下载"""
    print("\n[步骤 3] 检查 DeepSeek-R1 模型")
    print("-" * 80)
    
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            models = data.get('models', [])
            
            # 查找 deepseek 模型
            deepseek_models = [m for m in models if 'deepseek' in m.get('name', '').lower()]
            
            if deepseek_models:
                print("  [OK] 找到 DeepSeek 模型")
                for model in deepseek_models:
                    name = model.get('name', 'unknown')
                    size = model.get('size', 0) / (1024**3)  # 转换为 GB
                    print(f"       - {name} ({size:.2f} GB)")
                return True
            else:
                print("  [FAIL] 未找到 DeepSeek 模型")
                print("       已安装的模型:")
                if models:
                    for m in models[:5]:
                        print(f"         - {m.get('name', 'unknown')}")
                else:
                    print("         (无)")
                return False
        else:
            print(f"  [FAIL] API 返回错误: HTTP {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] 检查失败: {str(e)}")
        return False

def test_model_generation():
    """测试模型生成能力"""
    print("\n[步骤 4] 测试模型生成能力")
    print("-" * 80)
    
    try:
        # 简单的测试请求
        test_prompt = "用一句话解释什么是量化交易"
        
        print(f"  测试提示: {test_prompt}")
        print("  正在生成回复...")
        
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:7b",
                "prompt": test_prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 50}
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            response = data.get('response', '')
            
            if response:
                print("  [OK] 模型生成成功")
                print(f"       回复: {response[:100]}...")
                return True
            else:
                print("  [FAIL] 模型返回空响应")
                return False
        else:
            print(f"  [FAIL] 生成失败: HTTP {resp.status_code}")
            print(f"         响应: {resp.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("  [FAIL] 请求超时（30秒）")
        print("         模型可能正在加载或性能不足")
        return False
    except Exception as e:
        print(f"  [FAIL] 测试失败: {str(e)}")
        return False

# 运行诊断
print("\n开始全面诊断...")

results = {
    "Ollama 安装": test_ollama_installed(),
    "服务状态": test_ollama_service(),
    "模型存在": test_model_exists(),
    "生成测试": test_model_generation(),
}

# 总结
print("\n" + "=" * 80)
print("诊断总结")
print("=" * 80)

success_count = sum(1 for v in results.values() if v)
total_count = len(results)

print(f"\n测试通过: {success_count}/{total_count}")

for test_name, result in results.items():
    status = "[PASS]" if result else "[FAIL]"
    print(f"  {status} {test_name}")

# 根据结果给出解决方案
print("\n" + "=" * 80)
print("解决方案")
print("=" * 80)

if not results["Ollama 安装"]:
    print("\n问题: Ollama 未安装")
    print("\n解决方案:")
    print("  1. 访问 https://ollama.com/download")
    print("  2. 下载 Windows 版本")
    print("  3. 运行安装程序")
    print("  4. 重启命令行窗口后再次运行诊断")

elif not results["服务状态"]:
    print("\n问题: Ollama 服务未运行")
    print("\n解决方案:")
    print("  方法 1: 在命令行运行")
    print("    ollama serve")
    print("\n  方法 2: 启动 Ollama 应用程序")
    print("    - 在开始菜单找到 Ollama")
    print("    - 或运行: start ollama")
    print("\n  方法 3: 后台启动（PowerShell）")
    print("    Start-Process ollama -ArgumentList 'serve' -WindowStyle Hidden")

elif not results["模型存在"]:
    print("\n问题: DeepSeek 模型未下载")
    print("\n解决方案:")
    print("  1. 下载 DeepSeek-R1 模型 (约 4.7 GB):")
    print("     ollama pull deepseek-r1:7b")
    print("\n  2. 或使用更小的模型:")
    print("     ollama pull deepseek-r1:1.5b  (约 1.5 GB)")
    print("     ollama pull deepseek-r1:8b    (约 5.3 GB)")
    print("\n  3. 查看已安装模型:")
    print("     ollama list")
    print("\n  4. 下载进度会实时显示，请耐心等待")

elif not results["生成测试"]:
    print("\n问题: 模型生成失败")
    print("\n可能原因:")
    print("  1. 模型文件损坏")
    print("  2. 内存不足（需要至少 8GB RAM）")
    print("  3. GPU 资源不足")
    print("\n解决方案:")
    print("  1. 重新下载模型:")
    print("     ollama pull deepseek-r1:7b")
    print("\n  2. 使用更小的模型:")
    print("     ollama pull deepseek-r1:1.5b")
    print("\n  3. 检查系统资源:")
    print("     - 关闭其他占用内存的程序")
    print("     - 确保有足够的磁盘空间")

else:
    print("\n所有测试通过！AI 服务正常工作。")
    print("\n使用说明:")
    print("  - 应用会自动调用 AI 进行市场分析")
    print("  - 确保在启动 Streamlit 前先运行: ollama serve")
    print("  - 首次生成可能较慢，后续会加快")

print("\n" + "=" * 80)
