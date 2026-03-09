import requests
import time
import sys
import io

# 设置控制台编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

urls = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision"
]

print("测试币安节点连接...\n")

for url in urls:
    try:
        start = time.time()
        resp = requests.get(f"{url}/api/v3/ping", timeout=5)
        latency = (time.time() - start) * 1000
        print(f"✅ {url}: {resp.status_code} ({latency:.0f}ms)")
    except Exception as e:
        print(f"❌ {url}: {str(e)[:50]}")

print("\n测试K线数据获取...")
try:
    resp = requests.get(
        "https://data-api.binance.vision/api/v3/klines",
        params={"symbol": "ETHUSDT", "interval": "5m", "limit": 5},
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ 成功获取 {len(data)} 条K线数据")
        print(f"最新价格: {data[-1][4]} USDT")
    else:
        print(f"❌ 获取失败: {resp.status_code}")
except Exception as e:
    print(f"❌ 错误: {e}")
