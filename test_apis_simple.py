import requests
import time

print("Testing Exchange APIs...")
print("=" * 60)

apis = [
    ("Binance Main", "https://api.binance.com/api/v3/ping"),
    ("Binance Vision", "https://data-api.binance.vision/api/v3/ping"),
    ("OKX", "https://www.okx.com/api/v5/public/time"),
    ("Huobi", "https://api.huobi.pro/v1/common/timestamp"),
    ("Gate.io", "https://api.gateio.ws/api/v4/spot/time"),
    ("KuCoin", "https://api.kucoin.com/api/v1/timestamp"),
    ("Bybit", "https://api.bybit.com/v2/public/time"),
    ("CoinEx", "https://api.coinex.com/v1/common/market/tickers"),
    ("MEXC", "https://api.mexc.com/api/v3/ping"),
]

available = []
for name, url in apis:
    try:
        start = time.time()
        resp = requests.get(url, timeout=5)
        latency = (time.time() - start) * 1000
        if resp.status_code == 200:
            print(f"[OK] {name:20} {latency:>6.0f}ms")
            available.append(name)
        else:
            print(f"[FAIL] {name:20} HTTP {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] {name:20} {str(e)[:40]}")

print("=" * 60)
print(f"Available: {len(available)}/{len(apis)}")
if available:
    print(f"Recommended: {available[0]}")
