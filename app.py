import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
import time
import threading
import datetime
import os
import sys
import re
import json
from streamlit_autorefresh import st_autorefresh
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ========== 1. 页面配置 (必须是第一个命令) ==========
st.set_page_config(
    page_title="ETHUSDT 机构级量化巡航系统 (抗封锁版)", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ========== 2. 智能客户端类 (核心：完美解决IP限制) ==========
class BinanceClient:
    """
    币安智能客户端：
    1. 多节点轮询：内置全球多个备用节点，一个IP被封自动切换。
    2. 自动重试：遇到网络波动或429错误，自动退避重试。
    3. 连接池复用：减少TCP握手开销。
    """
    # 币安官方多节点列表
    BASE_URLS = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
        "https://data-api.binance.vision", # 公共数据备用节点
    ]

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.session = requests.Session()
        self.current_url_index = 0
        
        # 配置重试策略：总共重试3次，适应 429/502/503 错误
        retry_strategy = Retry(
            total=3,
            backoff_factor=1, # 自动退避时间：1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        if self.api_key:
            self.session.headers.update({'X-MBX-APIKEY': self.api_key})

    def _get_base_url(self):
        """轮询获取可用节点，分散流量压力"""
        url = self.BASE_URLS[self.current_url_index]
        # 每次请求轮换节点
        self.current_url_index = (self.current_url_index + 1) % len(self.BASE_URLS)
        return url

    def safe_request(self, endpoint, params=None):
        """安全的请求方法，自带节点切换"""
        errors = []
        
        # 尝试所有节点
        for i in range(len(self.BASE_URLS)):
            url = f"{self._get_base_url()}{endpoint}"
            try:
                resp = self.session.get(url, params=params, timeout=10)
                
                # 核心逻辑：处理IP限制
                if resp.status_code == 429:
                    wait_time = int(resp.headers.get('Retry-After', 5))
                    print(f"⚠️ 触发限流，等待 {wait_time} 秒后切换节点...")
                    time.sleep(wait_time)
                    continue # 切换下一个节点重试
                
                if resp.status_code != 200:
                    errors.append(f"{url}: HTTP {resp.status_code}")
                    continue
                    
                return resp.json()
            except Exception as e:
                errors.append(f"{url}: {str(e)[:50]}")
                continue
        
        # 所有节点都失败
        error_msg = " | ".join(errors[-3:])  # 只显示最后3个错误
        raise Exception(f"所有节点访问失败: {error_msg}")

# 获取 API Key
try:
    api_key = st.secrets.get("BINANCE_API_KEY", "") if hasattr(st, 'secrets') else ""
except:
    api_key = ""

# 使用缓存资源创建客户端（避免重复创建）
@st.cache_resource
def get_client():
    return BinanceClient(api_key=api_key)

# ========== 3. 核心功能函数 ==========

# 语音播报 (后台线程)
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

# AI 服务检测与调用
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
        return "🤖 AI服务未启动 (请运行 ollama serve)"

# ========== 4. 数据获取 (带缓存，防止重复请求) ==========

SYMBOL = "ETHUSDT"

# 缓存5秒：同一个数据在5秒内无论页面刷新多少次，都只请求一次网络
@st.cache_data(ttl=5, show_spinner=False)
def get_market_data():
    """获取市场数据，带自动重试和节点切换"""
    client = get_client()
    
    # 并发获取K线和订单簿
    try:
        klines = client.safe_request("/api/v3/klines", {"symbol": SYMBOL, "interval": "5m", "limit": 200})
        depth = client.safe_request("/api/v3/depth", {"symbol": SYMBOL, "limit": 20})
    except Exception as e:
        st.error(f"API 请求异常: {e}")
        return pd.DataFrame(), 0, {}, f"错误: {str(e)}"
    
    # 详细错误检查
    if not klines:
        st.warning("⚠️ K线数据为空，可能触发了限流")
        return pd.DataFrame(), 0, {}, "K线数据获取失败"
    
    if not depth:
        st.warning("⚠️ 订单簿数据为空")
        depth = {"bids": [], "asks": []}
        
    # 处理K线
    try:
        df = pd.DataFrame(klines, columns=["time","open","high","low","close","volume","ct","qv","n","tb","tq","ig"])
        cols = ["open","high","low","close","volume"]
        df[cols] = df[cols].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit="ms")
    except Exception as e:
        st.error(f"数据处理错误: {e}")
        return pd.DataFrame(), 0, {}, f"数据处理失败: {str(e)}"
    
    # 处理订单簿
    bids = depth.get("bids", [])
    asks = depth.get("asks", [])
    bid_vol = sum(float(b[1]) for b in bids) if bids else 0
    ask_vol = sum(float(a[1]) for a in asks) if asks else 0
    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
    
    # 计算指标
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma50"] = df["close"].rolling(50).mean()
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]
    
    # 提取大单墙
    walls = {}
    if bids and asks:
        avg_bid = bid_vol / len(bids)
        avg_ask = ask_vol / len(asks)
        for p, q in bids:
            if float(q) > avg_bid * 3: walls['support'] = float(p); break
        for p, q in asks:
            if float(q) > avg_ask * 3: walls['resistance'] = float(p); break
            
    depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
    if bid_vol > ask_vol * 1.5: depth_desc += " (强劲)"
    elif ask_vol > bid_vol * 1.5: depth_desc += " (沉重)"
    
    return df, imbalance, walls, depth_desc

# ========== 5. 主程序 ==========
def main():
    # 自动刷新：每10秒刷新一次数据
    st_autorefresh(interval=10000, key="main_refresh")
    
    st.title("🚀 ETHUSDT 机构级量化巡航系统 (抗封锁版)")
    
    # 显示连接状态
    client = get_client()
    current_node = client.BASE_URLS[client.current_url_index]
    st.markdown(f"**系统时间**: {datetime.datetime.now().strftime('%H:%M:%S')} | **当前节点**: {current_node}")
    
    # 添加调试信息
    with st.expander("🔧 系统状态", expanded=False):
        st.write(f"客户端状态: 已初始化")
        st.write(f"API Key: {'已配置' if api_key else '未配置（使用公共限额）'}")
        st.write(f"可用节点数: {len(client.BASE_URLS)}")
    
    # 1. 获取数据
    with st.spinner("正在同步币安数据..."):
        df, imbalance, walls, depth_desc = get_market_data()
    
    # 详细错误诊断
    if df.empty:
        st.error("❌ 数据获取失败")
        st.warning(f"**错误详情**: {depth_desc}")
        
        # 显示网络诊断
        st.info("🔍 正在诊断网络连接...")
        for url in client.BASE_URLS[:3]:  # 只测试前3个节点
            try:
                import requests
                resp = requests.get(f"{url}/api/v3/ping", timeout=3)
                st.write(f"✅ {url}: {resp.status_code}")
            except Exception as e:
                st.write(f"❌ {url}: {str(e)[:30]}")
        
        st.stop()
    
    # 2. 计算状态
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
    
    # 3. 页面布局
    col_chart, col_ai = st.columns([1.5, 1])
    
    with col_chart:
        st.subheader("📈 实时行情 (5m)")
        fig = go.Figure()
        # K线（绿色上涨，红色下跌 - 中国标准）
        fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], 
                                     low=df['low'], close=df['close'], name='K线',
                                     increasing_line_color='green',    # 上涨 - 绿色
                                     decreasing_line_color='red',     # 下跌 - 红色
                                     increasing_fillcolor='green',
                                     decreasing_fillcolor='red'))
        # 均线
        fig.add_trace(go.Scatter(x=df['time'], y=df['ma20'], line=dict(color='orange', width=1), name='MA20'))
        fig.add_trace(go.Scatter(x=df['time'], y=df['ma50'], line=dict(color='blue', width=1), name='MA50'))
        
        # 标记大单墙
        if 'support' in walls:
            fig.add_hline(y=walls['support'], line_dash="dash", line_color="green", 
                          annotation_text="支撑墙", annotation_position="right")
        if 'resistance' in walls:
            fig.add_hline(y=walls['resistance'], line_dash="dash", line_color="red", 
                          annotation_text="压力墙", annotation_position="right")
            
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        # 关键指标
        c1, c2, c3 = st.columns(3)
        c1.metric("当前价格", f"{price:.2f}", f"{df['close'].iloc[-1] - df['close'].iloc[-2]:.2f}")
        c2.metric("量比", f"{vol_ratio:.2f}", delta="放量" if vol_ratio > 1.5 else "缩量")
        c3.metric("盘口失衡", f"{imbalance:.2f}", delta="多头优势" if imbalance > 0.1 else "空头优势")
        st.info(f"**盘口详情**: {depth_desc}")

    with col_ai:
        st.subheader("🧠 AI 审计中心")
        
        # 实时信号展示
        if signals:
            st.write("**当前触发信号**:")
            st.write(", ".join([f"`{s}`" for s in signals]))
        else:
            st.write("**当前触发信号**: 无明确信号")
            
        st.markdown("---")
        
        # AI 分析逻辑
        with st.spinner("🕵️ DeepSeek-R1 正在审计..."):
            # 构建 Prompt
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
            
            # 格式化输出
            if "AI服务未启动" in ai_report:
                st.warning(ai_report)
                st.info("👉 备用建议：请关注 MA20 支撑情况，结合量能操作。")
            else:
                st.markdown(ai_report)
                
                # 语音播报关键信号
                if "多头共振" in resonance and vol_ratio > 2.0:
                    speak("警告，检测到多头共振且成交量放大，关注做多机会")
                elif "空头共振" in resonance:
                    speak("警告，检测到空头共振，注意风险")

if __name__ == "__main__":
    main()
