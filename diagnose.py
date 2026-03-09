import requests
import time
import json
import sys
import io

# 设置 UTF-8 编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 70)
print("ETHUSDT 量化系统 - 完整诊断测试")
print("=" * 70)

# 测试配置
TEST_EXCHANGES = [
    {
        "name": "KuCoin",
        "base_url": "https://api.kucoin.com",
        "kline_endpoint": "/api/v1/market/candles",
        "depth_endpoint": "/api/v1/market/orderbook/level2_20",
        "params": {"symbol": "ETH-USDT", "type": "5min"}
    },
    {
        "name": "Gate.io",
        "base_url": "https://api.gateio.ws",
        "kline_endpoint": "/api/v4/spot/candlesticks",
        "depth_endpoint": "/api/v4/spot/order_book",
        "params": {"currency_pair": "ETH_USDT", "interval": "5m", "limit": 10}
    },
    {
        "name": "Binance",
        "base_url": "https://api.binance.com",
        "kline_endpoint": "/api/v3/klines",
        "depth_endpoint": "/api/v3/depth",
        "params": {"symbol": "ETHUSDT", "interval": "5m", "limit": 10}
    },
]

def test_exchange(exchange):
    """测试单个交易所的完整数据获取流程"""
    print(f"\n{'='*70}")
    print(f"测试 {exchange['name']}")
    print(f"{'='*70}")
    
    session = requests.Session()
    
    # 1. 测试基础连接
    print("\n[1/4] 测试基础连接...")
    try:
        test_url = f"{exchange['base_url']}/api/v1/timestamp" if exchange['name'] == "KuCoin" else \
                   f"{exchange['base_url']}/api/v4/spot/time" if exchange['name'] == "Gate.io" else \
                   f"{exchange['base_url']}/api/v3/ping"
        
        start = time.time()
        resp = session.get(test_url, timeout=5)
        latency = (time.time() - start) * 1000
        
        if resp.status_code == 200:
            print(f"    [OK] 基础连接成功 ({latency:.0f}ms)")
        else:
            print(f"    [FAIL] HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"    [FAIL] 连接失败: {str(e)[:50]}")
        return False
    
    # 2. 测试K线数据获取
    print("\n[2/4] 测试K线数据获取...")
    try:
        kline_url = f"{exchange['base_url']}{exchange['kline_endpoint']}"
        start = time.time()
        resp = session.get(kline_url, params=exchange['params'], timeout=10)
        latency = (time.time() - start) * 1000
        
        if resp.status_code == 200:
            data = resp.json()
            
            # 解析数据
            if exchange['name'] == "KuCoin":
                klines = data.get('data', [])
                if klines:
                    latest = klines[0]
                    print(f"    [OK] K线数据获取成功 ({latency:.0f}ms)")
                    print(f"    数据量: {len(klines)} 条")
                    print(f"    最新价格: ${float(latest[2]):.2f}")
                else:
                    print(f"    [FAIL] K线数据为空")
                    return False
                    
            elif exchange['name'] == "Gate.io":
                klines = data if isinstance(data, list) else []
                if klines:
                    latest = klines[0]
                    print(f"    [OK] K线数据获取成功 ({latency:.0f}ms)")
                    print(f"    数据量: {len(klines)} 条")
                    print(f"    最新价格: ${float(latest[2]):.2f}")
                else:
                    print(f"    [FAIL] K线数据为空")
                    return False
                    
            elif exchange['name'] == "Binance":
                klines = data if isinstance(data, list) else []
                if klines:
                    latest = klines[-1]
                    print(f"    [OK] K线数据获取成功 ({latency:.0f}ms)")
                    print(f"    数据量: {len(klines)} 条")
                    print(f"    最新价格: ${float(latest[4]):.2f}")
                else:
                    print(f"    [FAIL] K线数据为空")
                    return False
        else:
            print(f"    [FAIL] HTTP {resp.status_code}")
            print(f"    响应: {resp.text[:100]}")
            return False
            
    except Exception as e:
        print(f"    [FAIL] K线获取失败: {str(e)[:80]}")
        return False
    
    # 3. 测试订单簿数据获取
    print("\n[3/4] 测试订单簿数据获取...")
    try:
        depth_params = {"symbol": "ETH-USDT"} if exchange['name'] == "KuCoin" else \
                      {"currency_pair": "ETH_USDT"} if exchange['name'] == "Gate.io" else \
                      {"symbol": "ETHUSDT"}
        
        depth_url = f"{exchange['base_url']}{exchange['depth_endpoint']}"
        start = time.time()
        resp = session.get(depth_url, params=depth_params, timeout=10)
        latency = (time.time() - start) * 1000
        
        if resp.status_code == 200:
            data = resp.json()
            
            # 解析订单簿
            if exchange['name'] == "KuCoin":
                bids = data.get('data', {}).get('bids', [])
                asks = data.get('data', {}).get('asks', [])
            elif exchange['name'] == "Gate.io":
                bids = data.get('bids', [])
                asks = data.get('asks', [])
            elif exchange['name'] == "Binance":
                bids = data.get('bids', [])
                asks = data.get('asks', [])
            
            if bids and asks:
                print(f"    [OK] 订单簿数据获取成功 ({latency:.0f}ms)")
                print(f"    买盘: {len(bids)} 档 | 卖盘: {len(asks)} 档")
                print(f"    最高买: ${float(bids[0][0]):.2f} | 最低卖: ${float(asks[0][0]):.2f}")
                
                # 计算买卖盘力量
                bid_vol = sum(float(b[1]) for b in bids[:5])
                ask_vol = sum(float(a[1]) for a in asks[:5])
                imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) * 100
                print(f"    盘口失衡: {imbalance:+.2f}% ({'多头优势' if imbalance > 0 else '空头优势'})")
            else:
                print(f"    [FAIL] 订单簿数据为空")
                return False
        else:
            print(f"    [FAIL] HTTP {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"    [FAIL] 订单簿获取失败: {str(e)[:80]}")
        return False
    
    # 4. 数据完整性验证
    print("\n[4/4] 数据完整性验证...")
    print("    [OK] 所有数据获取成功")
    print(f"\n{'='*70}")
    print(f"交易所 {exchange['name']} 测试通过 [OK]")
    print(f"{'='*70}")
    return True

# 运行测试
print("\n开始测试所有交易所...\n")

success_count = 0
recommended = None

for exchange in TEST_EXCHANGES:
    if test_exchange(exchange):
        success_count += 1
        if not recommended:
            recommended = exchange['name']

print(f"\n{'='*70}")
print(f"测试总结")
print(f"{'='*70}")
print(f"成功: {success_count}/{len(TEST_EXCHANGES)}")
print(f"推荐使用: {recommended if recommended else '无可用交易所'}")

if success_count > 0:
    print("\n[OK] 系统可以正常运行！")
    print(f"建议在 app_v3.py 中优先使用 {recommended}")
else:
    print("\n[FAIL] 所有交易所测试失败")
    print("可能的原因：")
    print("  1. 网络连接问题")
    print("  2. 需要配置代理")
    print("  3. 防火墙阻止")
    print("\n解决方案：")
    print("  set HTTPS_PROXY=http://127.0.0.1:7890")
    print("  streamlit run app_v3.py")
