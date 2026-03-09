import requests
import json

# 测试 CoinEx K线 API
url = "https://api.coinex.com/v1/market/kline"
params = {
    "market": "ETHUSDT",
    "type": "5min",
    "limit": 10
}

print("测试 CoinEx K线 API...")
print(f"URL: {url}")
print(f"参数: {params}")
print()

try:
    resp = requests.get(url, params=params, timeout=10)
    print(f"状态码: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\n响应数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if "data" in data:
            klines = data["data"]
            print(f"\nK线数据条数: {len(klines)}")
            if klines:
                print(f"\n第一条K线数据:")
                print(klines[0])
                print(f"\n列数: {len(klines[0])}")
    else:
        print(f"错误: {resp.text}")
        
except Exception as e:
    print(f"请求失败: {e}")
