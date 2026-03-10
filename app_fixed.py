import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
import threading
import datetime
import os
from streamlit_autorefresh import st_autorefresh
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ========== 1. 页面配置 ==========
st.set_page_config(
    page_title="ETHUSDT 多交易所量化系统", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ========== 2. 交易所客户端（无状态，可序列化）==========
EXCHANGES = {
    "KuCoin": {
        "priority": 1,
        "base_url": "https://api.kucoin.com",
        "kline_endpoint": "/api/v1/market/candles",
        "depth_endpoint": "/api/v1/market/orderbook/level2_20",
        "params": {"symbol": "ETH-USDT", "type": "5min"}
    },
    "Gate.io": {
        "priority": 2,
        "base_url": "https://api.gateio.ws",
        "kline_endpoint": "/api/v4/spot/candlesticks",
        "depth_endpoint": "/api/v4/spot/order_book",
        "params": {"currency_pair": "ETH_USDT", "interval": "5m", "limit": 200}
    },
    "Binance": {
        "priority": 3,
        "base_url": "https://api.binance.com",
        "kline_endpoint": "/api/v3/klines",
        "depth_endpoint": "/api/v3/depth",
        "params": {"symbol": "ETHUSDT", "interval": "5m", "limit": 200}
    },
}

# 全局 Session（使用 cache_resource 缓存）
@st.cache_resource
def get_session():
    """获取全局 Session 对象"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# ========== 3. 数据获取函数（纯函数，无副作用）==========
@st.cache_data(ttl=5, show_spinner=False)
def fetch_klines_and_depth(_session):
    """
    获取K线和订单簿数据
    注意：_session 参数前缀 _ 表示不参与缓存键计算
    """
    # 按优先级尝试交易所
    sorted_exchanges = sorted(EXCHANGES.items(), key=lambda x: x[1]['priority'])
    
    for exchange_name, config in sorted_exchanges:
        try:
            base_url = config['base_url']
            
            # 获取K线
            kline_url = f"{base_url}{config['kline_endpoint']}"
            kline_resp = _session.get(kline_url, params=config['params'], timeout=10)
            
            if kline_resp.status_code != 200:
                continue
            
            # 获取订单簿
            depth_params = {"symbol": "ETH-USDT"} if exchange_name == "KuCoin" else \
                          {"currency_pair": "ETH_USDT"} if exchange_name == "Gate.io" else \
                          {"symbol": "ETHUSDT"}
            
            depth_url = f"{base_url}{config['depth_endpoint']}"
            depth_resp = _session.get(depth_url, params=depth_params, timeout=10)
            
            if depth_resp.status_code != 200:
                continue
            
            # 解析数据
            klines = kline_resp.json()
            depth = depth_resp.json()
            
            df, imbalance, walls, depth_desc = parse_exchange_data(
                exchange_name, klines, depth
            )
            
            if df is not None and not df.empty:
                return df, imbalance, walls, f"{exchange_name} | {depth_desc}"
                
        except Exception as e:
            print(f"{exchange_name} 失败: {e}")
            continue
    
    return None, 0, {}, "所有交易所连接失败"

def parse_exchange_data(exchange_name, klines, depth):
    """解析交易所数据"""
    try:
        if exchange_name == "KuCoin":
            return parse_kucoin(klines, depth)
        elif exchange_name == "Gate.io":
            return parse_gate(klines, depth)
        elif exchange_name == "Binance":
            return parse_binance(klines, depth)
    except Exception as e:
        print(f"解析 {exchange_name} 失败: {e}")
        return None, 0, {}, f"解析错误: {e}"

def parse_kucoin(klines, depth):
    """解析 KuCoin 数据"""
    data = klines.get('data', [])
    if not data:
        return None, 0, {}, "无数据"
    
    df = pd.DataFrame(data, columns=[
        "time","open","close","high","low","volume","turnover"
    ])
    df = df[["time","open","high","low","close","volume"]]
    cols = ["open","high","low","close","volume"]
    df[cols] = df[cols].astype(float)
    df["time"] = pd.to_datetime(df["time"].astype(int), unit='s')
    df = df.sort_values("time").reset_index(drop=True)
    
    bids = depth.get('data', {}).get('bids', [])
    asks = depth.get('data', {}).get('asks', [])
    bid_vol = sum(float(b[1]) for b in bids[:10]) if bids else 0
    ask_vol = sum(float(a[1]) for a in asks[:10]) if asks else 0
    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
    
    walls = detect_walls(bids, asks, bid_vol, ask_vol)
    depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
    
    return df, imbalance, walls, depth_desc

def parse_gate(klines, depth):
    """解析 Gate.io 数据"""
    if not klines:
        return None, 0, {}, "无数据"
    
    df = pd.DataFrame(klines, columns=["timestamp","volume","close","high","low","open"])
    df = df[["timestamp","open","high","low","close","volume"]]
    df.columns = ["time","open","high","low","close","volume"]
    cols = ["open","high","low","close","volume"]
    df[cols] = df[cols].astype(float)
    df["time"] = pd.to_datetime(df["time"].astype(int), unit='s')
    df = df.sort_values("time").reset_index(drop=True)
    
    bids = depth.get('bids', [])
    asks = depth.get('asks', [])
    bid_vol = sum(float(b[1]) for b in bids[:10]) if bids else 0
    ask_vol = sum(float(a[1]) for a in asks[:10]) if asks else 0
    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
    
    walls = detect_walls(bids, asks, bid_vol, ask_vol)
    depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
    
    return df, imbalance, walls, depth_desc

def parse_binance(klines, depth):
    """解析币安数据"""
    if not klines:
        return None, 0, {}, "无数据"
    
    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume","ct","qv","n","tb","tq","ig"
    ])
    cols = ["open","high","low","close","volume"]
    df[cols] = df[cols].astype(float)
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    
    bids = depth.get("bids", [])
    asks = depth.get("asks", [])
    bid_vol = sum(float(b[1]) for b in bids[:10]) if bids else 0
    ask_vol = sum(float(a[1]) for a in asks[:10]) if asks else 0
    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
    
    walls = detect_walls(bids, asks, bid_vol, ask_vol)
    depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
    
    return df, imbalance, walls, depth_desc

def detect_walls(bids, asks, bid_vol, ask_vol):
    """检测大单墙"""
    walls = {}
    if not bids or not asks:
        return walls
    
    avg_bid = bid_vol / min(len(bids), 10)
    avg_ask = ask_vol / min(len(asks), 10)
    
    for order in bids[:20]:
        if float(order[1]) > avg_bid * 3:
            walls['support'] = float(order[0])
            break
    
    for order in asks[:20]:
        if float(order[1]) > avg_ask * 3:
            walls['resistance'] = float(order[0])
            break
    
    return walls

# ========== 4. 测试连接 ==========
@st.cache_data(ttl=60)
def test_all_connections():
    """测试所有交易所连接"""
    session = get_session()
    results = {}
    
    test_urls = {
        "KuCoin": "https://api.kucoin.com/api/v1/timestamp",
        "Gate.io": "https://api.gateio.ws/api/v4/spot/time",
        "Binance": "https://api.binance.com/api/v3/ping",
    }
    
    for name, url in test_urls.items():
        try:
            start = time.time()
            resp = session.get(url, timeout=3)
            latency = (time.time() - start) * 1000
            results[name] = {"status": resp.status_code == 200, "latency": latency}
        except Exception as e:
            results[name] = {"status": False, "error": str(e)[:40]}
    
    return results

# ========== 5. AI 功能 ==========
def get_ai_analysis(prompt):
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "deepseek-r1:7b", "prompt": prompt, "stream": False, "options": {"temperature": 0.3}},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json().get("response", "AI分析超时")
        return "AI服务连接失败"
    except:
        return "AI服务未启动"

# ========== 6. 主程序 ==========
def main():
    st_autorefresh(interval=10000, key="main_refresh")
    
    st.title("🚀 ETHUSDT 多交易所量化系统")
    
    # 获取 Session
    session = get_session()
    
    # 启动时自动测试连接
    if 'connection_tested' not in st.session_state:
        with st.spinner("🔍 测试节点连接..."):
            results = test_all_connections()
            st.session_state['connection_results'] = results
            st.session_state['connection_tested'] = True
    
    # 侧边栏 - 连接状态
    with st.sidebar:
        st.markdown("### 🌐 节点状态")
        
        if 'connection_results' in st.session_state:
            results = st.session_state['connection_results']
            available = sum(1 for r in results.values() if r['status'])
            st.metric("可用节点", f"{available}/{len(results)}")
            
            with st.expander("详细状态", expanded=False):
                for name, info in results.items():
                    if info['status']:
                        st.success(f"✅ {name}: {info['latency']:.0f}ms")
                    else:
                        st.error(f"❌ {name}: {info.get('error', '连接失败')}")
        
        if st.button("🔄 重新测试连接", key="test_conn"):
            st.session_state['connection_tested'] = False
            st.rerun()
    
    # 显示时间
    st.markdown(f"**系统时间**: {datetime.datetime.now().strftime('%H:%M:%S')}")
    
    # 获取数据
    with st.spinner("📡 获取数据中..."):
        df, imbalance, walls, status_msg = fetch_klines_and_depth(session)
    
    if df is None or df.empty:
        st.error("❌ 数据获取失败")
        st.warning(f"**详情**: {status_msg}")
        st.stop()
    
    # 显示数据源
    st.info(f"📡 {status_msg}")
    
    # 计算指标
    if len(df) >= 50:
        df["ma20"] = df["close"].rolling(20).mean()
        df["ma50"] = df["close"].rolling(50).mean()
        df["vol_ma"] = df["volume"].rolling(20).mean()
        df["vol_ratio"] = df["volume"] / df["vol_ma"]
    else:
        df["ma20"] = df["close"]
        df["ma50"] = df["close"]
        df["vol_ma"] = df["volume"]
        df["vol_ratio"] = 1.0
    
    # 计算状态
    last = df.iloc[-1]
    price = last['close']
    vol_ratio = last['vol_ratio']
    trend = "上涨" if last['ma20'] > last['ma50'] else "下跌"
    
    # 信号生成
    signals = []
    if len(df) > 1:
        if last['close'] > last['ma20']: 
            signals.append("价格站上MA20")
        if vol_ratio > 2.0: 
            signals.append(f"巨量异动({vol_ratio:.1f}倍)")
        if imbalance > 0.4: 
            signals.append("买盘压倒")
        elif imbalance < -0.4: 
            signals.append("卖盘压倒")
    
    # 共振判断
    resonance = "无共振"
    if trend == "上涨" and imbalance > 0.3: 
        resonance = "多头共振"
    elif trend == "下跌" and imbalance < -0.3: 
        resonance = "空头共振"
    
    # 页面布局
    col_chart, col_ai = st.columns([1.5, 1])
    
    with col_chart:
        st.subheader("📈 实时行情 (5m)")
        
        # K线图
        fig = go.Figure()
        # K线（绿色上涨，红色下跌 - 中国标准）
        fig.add_trace(go.Candlestick(
            x=df['time'], open=df['open'], high=df['high'], 
            low=df['low'], close=df['close'], name='K线',
            increasing_line_color='green',    # 上涨 - 绿色
            decreasing_line_color='red',     # 下跌 - 红色
            increasing_fillcolor='green',
            decreasing_fillcolor='red'
        ))
        fig.add_trace(go.Scatter(
            x=df['time'], y=df['ma20'], 
            line=dict(color='orange', width=1), name='MA20'
        ))
        fig.add_trace(go.Scatter(
            x=df['time'], y=df['ma50'], 
            line=dict(color='blue', width=1), name='MA50'
        ))
        
        # 大单墙
        if 'support' in walls:
            fig.add_hline(y=walls['support'], line_dash="dash", line_color="green", 
                          annotation_text="支撑", annotation_position="right")
        if 'resistance' in walls:
            fig.add_hline(y=walls['resistance'], line_dash="dash", line_color="red", 
                          annotation_text="压力", annotation_position="right")
            
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        # 指标卡片
        c1, c2, c3 = st.columns(3)
        c1.metric("当前价格", f"{price:.2f}", 
                  f"{df['close'].iloc[-1] - df['close'].iloc[-2]:.2f}" if len(df) > 1 else "0.00")
        c2.metric("量比", f"{vol_ratio:.2f}", delta="放量" if vol_ratio > 1.5 else "缩量")
        c3.metric("盘口失衡", f"{imbalance:.2f}", 
                  delta="多头优势" if imbalance > 0.1 else "空头优势")

    with col_ai:
        st.subheader("🧠 AI 审计中心")
        
        if signals:
            st.write("**触发信号**:")
            st.write(", ".join([f"`{s}`" for s in signals]))
        else:
            st.write("**触发信号**: 无")
            
        st.markdown("---")
        
        # AI 分析
        with st.spinner("🕵️ AI分析中..."):
            prompt = f"""
            分析 ETHUSDT:
            价格: {price} 趋势: {trend} 量比: {vol_ratio:.2f} 盘口失衡: {imbalance:.2f}
            信号: {', '.join(signals)} 共振: {resonance}
            支撑: {walls.get('support', '无')} 压力: {walls.get('resistance', '无')}
            
            给出：市场判断、操作建议、风险等级
            """
            
            ai_report = get_ai_analysis(prompt)
            
            if "AI服务未启动" in ai_report:
                st.warning(ai_report)
                st.info("💡 备用建议：关注MA20支撑，结合量能操作")
            else:
                st.markdown(ai_report)

if __name__ == "__main__":
    main()
