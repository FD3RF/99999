import requests
import json
import time
import sys
import traceback
from datetime import datetime

print("=" * 80)
print("ETHUSDT 量化系统 - 完整问题诊断")
print("=" * 80)
print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 问题清单
issues = []
solutions = []

def test_basic_connectivity():
    """测试基础网络连接"""
    print("\n[步骤 1] 测试基础网络连接")
    print("-" * 80)
    
    test_urls = [
        ("KuCoin", "https://api.kucoin.com/api/v1/timestamp"),
        ("Gate.io", "https://api.gateio.ws/api/v4/spot/time"),
        ("Binance", "https://api.binance.com/api/v3/ping"),
    ]
    
    success_count = 0
    for name, url in test_urls:
        try:
            start = time.time()
            resp = requests.get(url, timeout=5)
            latency = (time.time() - start) * 1000
            
            if resp.status_code == 200:
                print(f"  [OK] {name:15} {latency:>6.0f}ms")
                success_count += 1
            else:
                print(f"  [FAIL] {name:15} HTTP {resp.status_code}")
                issues.append(f"{name} 连接失败: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  [FAIL] {name:15} {str(e)[:50]}")
            issues.append(f"{name} 连接异常: {str(e)[:50]}")
    
    if success_count == 0:
        solutions.append("网络连接失败，请检查：\n    - 网络是否正常\n    - 是否需要配置代理\n    - 防火墙是否阻止")
        return False
    return True

def test_kline_data():
    """测试K线数据获取"""
    print("\n[步骤 2] 测试K线数据获取")
    print("-" * 80)
    
    # 测试 KuCoin
    try:
        url = "https://api.kucoin.com/api/v1/market/candles"
        params = {"symbol": "ETH-USDT", "type": "5min"}
        
        start = time.time()
        resp = requests.get(url, params=params, timeout=10)
        latency = (time.time() - start) * 1000
        
        if resp.status_code == 200:
            data = resp.json()
            klines = data.get('data', [])
            
            if klines:
                latest = klines[0]
                print(f"  [OK] KuCoin K线数据获取成功 ({latency:.0f}ms)")
                print(f"       数据量: {len(klines)} 条")
                print(f"       最新价格: ${float(latest[2]):.2f}")
                print(f"       时间戳: {datetime.fromtimestamp(int(latest[0])).strftime('%H:%M:%S')}")
                return True
            else:
                print(f"  [FAIL] K线数据为空")
                issues.append("K线数据为空")
                return False
        else:
            print(f"  [FAIL] HTTP {resp.status_code}")
            print(f"         响应: {resp.text[:100]}")
            issues.append(f"K线API返回 HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] 异常: {str(e)[:80]}")
        issues.append(f"K线获取异常: {str(e)[:80]}")
        return False

def test_depth_data():
    """测试订单簿数据获取"""
    print("\n[步骤 3] 测试订单簿数据获取")
    print("-" * 80)
    
    try:
        url = "https://api.kucoin.com/api/v1/market/orderbook/level2_20"
        params = {"symbol": "ETH-USDT"}
        
        start = time.time()
        resp = requests.get(url, params=params, timeout=10)
        latency = (time.time() - start) * 1000
        
        if resp.status_code == 200:
            data = resp.json()
            orderbook = data.get('data', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if bids and asks:
                print(f"  [OK] 订单簿数据获取成功 ({latency:.0f}ms)")
                print(f"       买盘: {len(bids)} 档")
                print(f"       卖盘: {len(asks)} 档")
                print(f"       最高买: ${float(bids[0][0]):.2f} ({float(bids[0][1]):.4f} ETH)")
                print(f"       最低卖: ${float(asks[0][0]):.2f} ({float(asks[0][1]):.4f} ETH)")
                
                # 计算盘口失衡
                bid_vol = sum(float(b[1]) for b in bids[:5])
                ask_vol = sum(float(a[1]) for a in asks[:5])
                imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) * 100
                print(f"       盘口失衡: {imbalance:+.2f}%")
                return True
            else:
                print(f"  [FAIL] 订单簿数据为空")
                issues.append("订单簿数据为空")
                return False
        else:
            print(f"  [FAIL] HTTP {resp.status_code}")
            issues.append(f"订单簿API返回 HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] 异常: {str(e)[:80]}")
        issues.append(f"订单簿获取异常: {str(e)[:80]}")
        return False

def test_streamlit_app():
    """测试 Streamlit 应用"""
    print("\n[步骤 4] 测试 Streamlit 应用响应")
    print("-" * 80)
    
    try:
        url = "http://localhost:8501"
        start = time.time()
        resp = requests.get(url, timeout=10)
        latency = (time.time() - start) * 1000
        
        if resp.status_code == 200:
            print(f"  [OK] Streamlit 应用响应正常 ({latency:.0f}ms)")
            print(f"       响应大小: {len(resp.text)} 字节")
            
            # 检查是否包含错误信息
            if "错误" in resp.text or "失败" in resp.text or "error" in resp.text.lower():
                print(f"       [警告] 页面可能包含错误信息")
                # 尝试提取错误信息
                if "无法获取行情数据" in resp.text:
                    issues.append("应用显示: 无法获取行情数据")
                elif "连接失败" in resp.text:
                    issues.append("应用显示: 连接失败")
            
            return True
        else:
            print(f"  [FAIL] HTTP {resp.status_code}")
            issues.append(f"Streamlit 返回 HTTP {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] 无法连接到 Streamlit 应用")
        issues.append("Streamlit 应用未运行或端口被占用")
        solutions.append("重启 Streamlit 应用: streamlit run app_v3.py")
        return False
    except Exception as e:
        print(f"  [FAIL] 异常: {str(e)[:80]}")
        issues.append(f"Streamlit 测试异常: {str(e)[:80]}")
        return False

def test_data_parsing():
    """测试数据解析逻辑"""
    print("\n[步骤 5] 测试数据解析逻辑")
    print("-" * 80)
    
    try:
        # 模拟 KuCoin 数据
        test_data = [
            ["1704067200", "2013.06", "2015.5", "2010.0", "2012.5", "1234.56", "2481234.5"],
            ["1704066900", "2012.5", "2014.0", "2011.0", "2013.06", "1111.22", "2234567.8"],
        ]
        
        import pandas as pd
        
        df = pd.DataFrame(test_data, columns=[
            "time", "open", "close", "high", "low", "volume", "turnover"
        ])
        
        # 测试数据转换
        cols = ["open", "high", "low", "close", "volume"]
        df[cols] = df[cols].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit='s')
        
        print(f"  [OK] 数据解析成功")
        print(f"       DataFrame 形状: {df.shape}")
        print(f"       时间范围: {df['time'].min()} ~ {df['time'].max()}")
        print(f"       价格范围: ${df['low'].min():.2f} ~ ${df['high'].max():.2f}")
        return True
        
    except Exception as e:
        print(f"  [FAIL] 数据解析失败: {str(e)}")
        issues.append(f"数据解析错误: {str(e)}")
        return False

def check_code_issues():
    """检查代码问题"""
    print("\n[步骤 6] 检查代码潜在问题")
    print("-" * 80)
    
    issues_found = []
    
    try:
        with open('app_v3.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 检查常见问题
        checks = [
            ("缓存装饰器使用", "@st.cache_data" in code and "client" in code, 
             "缓存函数中使用了全局客户端对象，可能导致序列化问题"),
            ("异常处理", "try:" in code and "except" in code, 
             "代码包含异常处理"),
            ("空数据检查", "df.empty" in code or "if not df" in code, 
             "包含空数据检查"),
            ("超时设置", "timeout=" in code, 
             "包含请求超时设置"),
        ]
        
        for check_name, result, desc in checks:
            status = "[OK]" if result else "[WARN]"
            print(f"  {status} {check_name}: {desc}")
            if not result:
                issues_found.append(desc)
        
        return len(issues_found) == 0
        
    except Exception as e:
        print(f"  [FAIL] 代码检查失败: {str(e)}")
        return False

# 运行所有测试
print("\n开始全面诊断...")
print("=" * 80)

results = {
    "基础连接": test_basic_connectivity(),
    "K线数据": test_kline_data(),
    "订单簿数据": test_depth_data(),
    "应用响应": test_streamlit_app(),
    "数据解析": test_data_parsing(),
    "代码检查": check_code_issues(),
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

# 问题列表
if issues:
    print(f"\n发现 {len(issues)} 个问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")

# 解决方案
if solutions:
    print(f"\n建议解决方案:")
    for i, solution in enumerate(solutions, 1):
        print(f"  {i}. {solution}")

# 最终结论
print("\n" + "=" * 80)
if success_count == total_count:
    print("[结论] 所有测试通过！系统运行正常。")
    print("如果应用仍显示错误，请尝试:")
    print("  1. 刷新浏览器（Ctrl+F5）")
    print("  2. 清除浏览器缓存")
    print("  3. 重启 Streamlit 应用")
elif success_count >= total_count * 0.6:
    print("[结论] 部分测试失败，但系统基本可用。")
    print("请检查上述问题列表并尝试解决。")
else:
    print("[结论] 多项测试失败，系统可能无法正常工作。")
    print("请按照建议解决方案逐一排查。")

print("=" * 80)
