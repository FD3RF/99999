import requests
import time

print("测试 AI 服务...")
print("=" * 60)

try:
    start = time.time()
    
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "deepseek-r1:1.5b",
            "prompt": "用一句话解释什么是量化交易",
            "stream": False,
            "options": {"num_predict": 50, "temperature": 0.3}
        },
        timeout=15
    )
    
    elapsed = time.time() - start
    print(f"状态码: {resp.status_code}")
    print(f"响应时间: {elapsed:.1f}秒")
    
    if resp.status_code == 200:
        response = resp.json().get("response", "")
        print(f"AI 回复: {response[:200]}")
        print("\n测试成功!")
    else:
        print(f"错误: HTTP {resp.status_code}")
        print(f"响应: {resp.text[:100]}")
        
except requests.exceptions.Timeout:
    print("超时: AI 服务响应时间超过 15 秒")
    
except requests.exceptions.ConnectionError:
    print("连接失败: AI 服务未启动")
    print("启动命令: ollama serve")
    
except Exception as e:
    print(f"错误: {str(e)}")
