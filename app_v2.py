import streamlit as st
import pandas as pd
import numpy as np
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

# ========== 2. 多交易所支持 ==========
class MultiExchangeClient:
    """多交易所客户端，支持自动切换"""
    
    EXCHANGES = {
        "Binance": {
            "urls": [
                "https://api.binance.com",
                "https://api1.binance.com",
                "https://api2.binance.com",
                "https://data-api.binance.vision",
            ],
            "kline_endpoint": "/api/v3/klines",
            "depth_endpoint": "/api/v3/depth",
            "params": {"symbol": "ETHUSDT", "interval": "5m", "limit": 200},
            "depth_params": {"symbol": "ETHUSDT", "limit": 20},
        },
        "OKX": {
            "urls": ["https://www.okx.com"],
            "kline_endpoint": "/api/v5/market/candles",
            "depth_endpoint": "/api/v5/market/books",
            "params": {"instId": "ETH-USDT", "bar": "5m", "limit": 200},
            "depth_params": {"instId": "ETH-USDT", "sz": 20},
        },
        "Gate.io": {
            "urls": ["https://api.gateio.ws"],
            "kline_endpoint": "/api/v4/spot/candlesticks",
            "depth_endpoint": "/api/v4/spot/order_book",
            "params": {"currency_pair": "ETH_USDT", "interval": "5m", "limit": 200},
            "depth_params": {"currency_pair": "ETH_USDT", "limit": 20},
        },
    }
    
    def __init__(self):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.current_exchange = "Binance"
        self.current_url_index = 0
    
    def test_connection(self):
        """测试所有交易所连接"""
        results = {}
        for name, config in self.EXCHANGES.items():
            try:
                url = config["urls"][0]
                if name == "Binance":
                    test_url = f"{url}/api/v3/ping"
                elif name == "OKX":
                    test_url = f"{url}/api/v5/public/time"
                else:
                    test_url = f"{url}/api/v4/spot/time"
                
                resp = self.session.get(test_url, timeout=3)
                results[name] = resp.status_code == 200
            except:
                results[name] = False
        return results
    
    def fetch_data(self, exchange_name=None):
        """获取数据，支持自动切换交易所"""
        if exchange_name:
            exchanges_to_try = [exchange_name]
        else:
            # 按优先级尝试
            exchanges_to_try = ["Binance", "OKX", "Gate.io"]
        
        for exchange in exchanges_to_try:
            if exchange not in self.EXCHANGES:
                continue
            
            config = self.EXCHANGES[exchange]
            
            for url in config["urls"]:
                try:
                    # 获取K线
                    kline_url = f"{url}{config['kline_endpoint']}"
                    kline_resp = self.session.get(
                        kline_url, 
                        params=config["params"], 
                        timeout=10
                    )
                    
                    if kline_resp.status_code != 200:
                        continue
                    
                    # 获取订单簿
                    depth_url = f"{url}{config['depth_endpoint']}"
                    depth_resp = self.session.get(
                        depth_url,
                        params=config["depth_params"],
                        timeout=10
                    )
                    
                    if depth_resp.status_code != 200:
                        continue
                    
                    # 解析数据
                    klines = kline_resp.json()
                    depth = depth_resp.json()
                    
                    return self._parse_data(exchange, klines, depth)
                    
                except Exception as e:
                    print(f"{exchange} ({url}) 失败: {e}")
                    continue
        
        return None, None, None, "所有交易所连接失败"
    
    def _parse_data(self, exchange, klines, depth):
        """解析不同交易所的数据格式"""
        try:
            if exchange == "Binance":
                return self._parse_binance(klines, depth)
            elif exchange == "OKX":
                return self._parse_okx(klines, depth)
            elif exchange == "Gate.io":
                return self._parse_gate(klines, depth)
        except Exception as e:
            return None, None, None, f"数据解析错误: {e}"
    
    def _parse_binance(self, klines, depth):
        """解析币安数据"""
        df = pd.DataFrame(klines, columns=[
            "time","open","high","low","close","volume","ct","qv","n","tb","tq","ig"
        ])
        cols = ["open","high","low","close","volume"]
        df[cols] = df[cols].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        
        bids = depth.get("bids", [])
        asks = depth.get("asks", [])
        bid_vol = sum(float(b[1]) for b in bids) if bids else 0
        ask_vol = sum(float(a[1]) for a in asks) if asks else 0
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
        
        walls = {}
        if bids and asks:
            avg_bid = bid_vol / len(bids) if bids else 0
            avg_ask = ask_vol / len(asks) if asks else 0
            for p, q in bids:
                if float(q) > avg_bid * 3:
                    walls['support'] = float(p)
                    break
            for p, q in asks:
                if float(q) > avg_ask * 3:
                    walls['resistance'] = float(p)
                    break
        
        depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
        return df, imbalance, walls, depth_desc
    
    def _parse_okx(self, klines, depth):
        """解析OKX数据"""
        # OKX格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        df = pd.DataFrame(klines, columns=[
            "time","open","high","low","close","volume","volCcy","volCcyQuote","confirm"
        ])
        cols = ["open","high","low","close","volume"]
        df[cols] = df[cols].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df = df.sort_values("time").reset_index(drop=True)
        
        bids = depth.get("data", [{}])[0].get("bids", [])
        asks = depth.get("data", [{}])[0].get("asks", [])
        bid_vol = sum(float(b[3]) for b in bids) if bids else 0  # 累计量
        ask_vol = sum(float(a[3]) for a in asks) if asks else 0
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
        
        walls = {}
        if bids and asks:
            avg_bid = bid_vol / len(bids) if bids else 0
            avg_ask = ask_vol / len(asks) if asks else 0
            for bid in bids:
                if float(bid[3]) > avg_bid * 3:
                    walls['support'] = float(bid[0])
                    break
            for ask in asks:
                if float(ask[3]) > avg_ask * 3:
                    walls['resistance'] = float(ask[0])
                    break
        
        depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
        return df, imbalance, walls, depth_desc
    
    def _parse_gate(self, klines, depth):
        """解析Gate.io数据"""
        # Gate.io格式: [ts, vol, close, high, low, open]
        df = pd.DataFrame(klines, columns=["timestamp","volume","close","high","low","open"])
        df = df[["timestamp","open","high","low","close","volume"]]
        df.columns = ["time","open","high","low","close","volume"]
        cols = ["open","high","low","close","volume"]
        df[cols] = df[cols].astype(float)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        
        bids = depth.get("bids", [])
        asks = depth.get("asks", [])
        bid_vol = sum(float(b[1]) for b in bids) if bids else 0
        ask_vol = sum(float(a[1]) for a in asks) if asks else 0
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
        
        walls = {}
        if bids and asks:
            avg_bid = bid_vol / len(bids) if bids else 0
            avg_ask = ask_vol / len(asks) if asks else 0
            for p, q in bids:
                if float(q) > avg_bid * 3:
                    walls['support'] = float(p)
                    break
            for p, q in asks:
                if float(q) > avg_ask * 3:
                    walls['resistance'] = float(p)
                    break
        
        depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
        return df, imbalance, walls, depth_desc

# ========== 3. 初始化客户端 ==========
@st.cache_resource
def get_client():
    return MultiExchangeClient()

# ========== 4. 核心功能函数 ==========

def speak(text):
    def _speak():
        try:
            if os.name == "nt":
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.say(text)
                engine.runAndWait()
        except: pass
    threading.Thread(target=_speak, daemon=True).start()

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
        return "AI服务未启动 (请运行 ollama serve)"

# ========== 5. 数据获取 ==========
SYMBOL = "ETHUSDT"

@st.cache_data(ttl=5, show_spinner=False)
def get_market_data():
    """获取市场数据"""
    client = get_client()
    
    df, imbalance, walls, error_msg = client.fetch_data()
    
    if df is None:
        return pd.DataFrame(), 0, {}, error_msg
    
    # 计算指标
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma50"] = df["close"].rolling(50).mean()
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]
    
    return df, imbalance, walls, error_msg

# ========== 6. 主程序 ==========
def main():
    st_autorefresh(interval=10000, key="main_refresh")
    
    st.title("ETHUSDT 多交易所量化系统")
    
    client = get_client()
    
    # 测试连接状态
    with st.sidebar:
        st.header("交易所状态")
        if st.button("测试连接", key="test_conn"):
            with st.spinner("测试中..."):
                results = client.test_connection()
                for name, status in results.items():
                    st.write(f"{'✅' if status else '❌'} {name}")
    
    st.markdown(f"**系统时间**: {datetime.datetime.now().strftime('%H:%M:%S')}")
    
    # 获取数据
    with st.spinner("正在获取数据..."):
        df, imbalance, walls, status_msg = get_market_data()
    
    if df.empty:
        st.error("数据获取失败")
        st.warning(f"**详情**: {status_msg}")
        st.stop()
    
    # 计算状态
    last = df.iloc[-1]
    price = last['close']
    vol_ratio = last['vol_ratio']
    trend = "上涨" if last['ma20'] > last['ma50'] else "下跌"
    
    # 信号生成
    signals = []
    if last['close'] > last['ma20']: signals.append("价格站上MA20")
    if vol_ratio > 2.0: signals.append(f"巨量异动({vol_ratio:.1f}倍)")
    if imbalance > 0.4: signals.append("买盘压倒")
    elif imbalance < -0.4: signals.append("卖盘压倒")
    
    # 共振判断
    resonance = "无共振"
    if trend == "上涨" and imbalance > 0.3: resonance = "多头共振"
    elif trend == "下跌" and imbalance < -0.3: resonance = "空头共振"
    
    # 页面布局
    col_chart, col_ai = st.columns([1.5, 1])
    
    with col_chart:
        st.subheader("实时行情 (5m)")
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
        
        if 'support' in walls:
            fig.add_hline(y=walls['support'], line_dash="dash", line_color="green", 
                          annotation_text="支撑墙", annotation_position="right")
        if 'resistance' in walls:
            fig.add_hline(y=walls['resistance'], line_dash="dash", line_color="red", 
                          annotation_text="压力墙", annotation_position="right")
            
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("当前价格", f"{price:.2f}", f"{df['close'].iloc[-1] - df['close'].iloc[-2]:.2f}")
        c2.metric("量比", f"{vol_ratio:.2f}", delta="放量" if vol_ratio > 1.5 else "缩量")
        c3.metric("盘口失衡", f"{imbalance:.2f}", delta="多头优势" if imbalance > 0.1 else "空头优势")
        st.info(f"**盘口详情**: {status_msg}")

    with col_ai:
        st.subheader("AI 审计中心")
        
        if signals:
            st.write("**当前触发信号**:")
            st.write(", ".join([f"`{s}`" for s in signals]))
        else:
            st.write("**当前触发信号**: 无明确信号")
            
        st.markdown("---")
        
        with st.spinner("DeepSeek-R1 正在审计..."):
            prompt = f"""
            作为量化交易员，分析 ETHUSDT 数据：
            价格: {price} 趋势: {trend} 量比: {vol_ratio:.2f} 盘口失衡: {imbalance:.2f}
            信号: {', '.join(signals)} 共振状态: {resonance}
            大单支撑: {walls.get('support', '无')} 压力: {walls.get('resistance', '无')}
            
            请给出：
            1. 市场结构判断 (吸筹/派发/震荡)
            2. 关键操作建议 (入场/止损/止盈)
            3. 风险等级 (高/中/低)
            """
            
            ai_report = get_ai_analysis(prompt)
            
            if "AI服务未启动" in ai_report:
                st.warning(ai_report)
                st.info("备用建议：请关注 MA20 支撑情况，结合量能操作。")
            else:
                st.markdown(ai_report)
                
                if "多头共振" in resonance and vol_ratio > 2.0:
                    speak("警告，检测到多头共振且成交量放大，关注做多机会")
                elif "空头共振" in resonance:
                    speak("警告，检测到空头共振，注意风险")

if __name__ == "__main__":
    main()
