import requests
import time

print("=" * 60)
print("测试各大交易所API连接情况")
print("=" * 60)

# 测试多个交易所
apis = [
    ("币安主站", "https://api.binance.com/api/v3/ping"),
    ("币安备用1", "https://api1.binance.com/api/v3/ping"),
    ("币安备用2", "https://api2.binance.com/api/v3/ping"),
    ("币安Vision", "https://data-api.binance.vision/api/v3/ping"),
    ("OKX", "https://www.okx.com/api/v5/public/time"),
    ("火币", "https://api.huobi.pro/v1/common/timestamp"),
    ("Gate.io", "https://api.gateio.ws/api/v4/spot/time"),
    ("KuCoin", "https://api.kucoin.com/api/v1/timestamp"),
    ("Bybit", "https://api.bybit.com/v2/public/time"),
    ("CoinEx", "https://api.coinex.com/v1/common/market/tickers"),
    ("MEXC", "https://api.mexc.com/api/v3/ping"),
]

results = []
for name, url in apis:
    try:
        start = time.time()
        resp = requests.get(url, timeout=5)
        latency = (time.time() - start) * 1000
        if resp.status_code == 200:
            results.append((name, "✅ 成功", f"{latency:.0f}ms"))
        else:
            results.append((name, "❌ 失败", f"HTTP {resp.status_code}"))
    except Exception as e:
        results.append((name, "❌ 超时/错误", str(e)[:30]))

print("\n测试结果：")
print("-" * 60)
for name, status, detail in results:
    print(f"{name:15} {status:10} {detail}")

# 找出可用的交易所
available = [r for r in results if "成功" in r[1]]
print("\n" + "=" * 60)
if available:
    print(f"[OK] 可用的交易所: {len(available)}/{len(apis)}")
    print(f"建议使用: {available[0][0]}")
else:
    print("[X] 所有交易所都无法访问")
    print("\n解决方案：")
    print("1. 使用代理/VPN")
    print("2. 使用国内镜像站点")
    print("3. 使用WebSocket连接")
    print("4. 使用聚合数据API")
