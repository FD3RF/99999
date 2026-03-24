# data_fetcher.py
import requests
import pandas as pd
import time
from datetime import datetime
from config import KLINE_LIMIT

def fetch_eth_klines(limit=KLINE_LIMIT):
    """获取ETH/USDT K线数据 - 多数据源智能切换（移除模块级缓存装饰器）"""
    
    # 按顺序尝试，成功则返回（国内源优先）
    sources = [
        ("MEXC", _fetch_mexc, limit),
        ("Gate.io", _fetch_gate, limit),
        ("KuCoin", _fetch_kucoin, limit),
        ("CoinEx", _fetch_coinex, limit),
        ("OKX", _fetch_okx, limit),
        ("Binance", _fetch_binance, limit),
    ]
    
    for name, fetch_func, lim in sources:
        try:
            # 修复：添加指数退避重试
            df = _fetch_with_retry(fetch_func, lim, name)
            if df is not None and len(df) > 10:
                return df
        except Exception as e:
            # 修复：记录具体错误而非静默失败
            print(f"[{name}] 数据获取失败: {str(e)}")
            continue
    
    return None

def _fetch_with_retry(fetch_func, limit, source_name, max_retries=2, base_delay=1):
    """带指数退避的重试机制"""
    for attempt in range(max_retries + 1):
        try:
            df = fetch_func(limit)
            if df is not None and len(df) > 0:
                return df
        except (requests.RequestException, requests.Timeout) as e:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)  # 指数退避: 1s, 2s
                print(f"[{source_name}] 第{attempt+1}次失败，{delay}秒后重试: {str(e)}")
                time.sleep(delay)
            else:
                raise  # 最后一次失败抛出异常
    return None

def _fetch_mexc(limit):
    """MEXC数据源 - 国内稳定"""
    url = "https://api.mexc.com/api/v3/klines"
    params = {"symbol": "ETHUSDT", "interval": "5m", "limit": limit}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, params=params, headers=headers, timeout=8)
    data = response.json()
    
    if data and isinstance(data, list) and len(data) > 0:
        records = []
        for k in data:
            records.append({
                "timestamp": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })
        
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    return None

def _fetch_gate(limit):
    """Gate.io数据源"""
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {"currency_pair": "ETH_USDT", "interval": "5m", "limit": limit}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, params=params, headers=headers, timeout=8)
    data = response.json()
    
    if data and isinstance(data, list) and len(data) > 0:
        records = []
        for k in data:
            if len(k) >= 6:
                records.append({
                    "timestamp": int(k[0]),
                    "open": float(k[5]),
                    "high": float(k[3]),
                    "low": float(k[4]),
                    "close": float(k[2]),
                    "volume": float(k[1])
                })
        
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    return None

def _fetch_kucoin(limit):
    """KuCoin数据源"""
    url = "https://api.kucoin.com/api/v1/market/candles"
    params = {"type": "5min", "symbol": "ETH-USDT", "size": limit}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, params=params, headers=headers, timeout=8)
    data = response.json()
    
    if data.get("code") == "200000" and data.get("data"):
        klines = data["data"]
        records = []
        for k in klines:
            records.append({
                "timestamp": int(k[0]) * 1000,
                "open": float(k[1]),
                "high": float(k[3]),
                "low": float(k[4]),
                "close": float(k[2]),
                "volume": float(k[5])
            })
        
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    return None

def _fetch_coinex(limit):
    """CoinEx数据源"""
    url = "https://api.coinex.com/v1/market/kline"
    params = {"market": "ETHUSDT", "type": "5min", "limit": limit}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, params=params, headers=headers, timeout=8)
    data = response.json()
    
    if data.get("code") == 0 and data.get("data"):
        klines = data["data"]
        records = []
        for k in klines:
            records.append({
                "timestamp": int(k[0]) * 1000,
                "open": float(k[3]),
                "high": float(k[2]),
                "low": float(k[4]),
                "close": float(k[1]),
                "volume": float(k[5])
            })
        
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    return None

def _fetch_okx(limit):
    """OKX数据源"""
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": "ETH-USDT", "bar": "5m", "limit": limit}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, params=params, headers=headers, timeout=8)
    data = response.json()
    
    if data.get("code") == "0" and data.get("data"):
        klines = data["data"]
        records = []
        for k in klines:
            if len(k) >= 6:
                records.append({
                    "timestamp": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })
        
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    return None

def _fetch_binance(limit):
    """Binance数据源"""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "ETHUSDT", "interval": "5m", "limit": limit}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, params=params, headers=headers, timeout=8)
    data = response.json()
    
    if data and len(data) > 0:
        records = []
        for k in data:
            records.append({
                "timestamp": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })
        
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    return None

def get_realtime_price():
    """获取当前实时价格"""
    df = fetch_eth_klines(1)
    if df is not None and len(df) > 0:
        return df.iloc[-1]["close"]
    return None
