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
from streamlit_autorefresh import st_autorefresh
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 导入高级信号模块
try:
    from advanced_signals import (
        detect_accumulation,
        whale_pump,
        crash_warning,
        multi_tf_resonance,
        volume_price_mnemonics,
        market_structure,
        fake_breakout,
        lstm_predict,
        calculate_support_resistance,
        ai_audit_ollama,
        get_deepseek_audit,
        comprehensive_signal_analysis,
        speak_alert
    )
    ADVANCED_SIGNALS_AVAILABLE = True
except ImportError:
    ADVANCED_SIGNALS_AVAILABLE = False
    print("⚠️ 高级信号模块未加载")

# ========== 1. 页面配置 ==========
st.set_page_config(
    page_title="ETHUSDT 全网节点量化系统", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ========== 2. 代理配置 ==========
# 从环境变量读取代理设置（用户可以在运行前设置）
PROXIES = {}
if os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY'):
    PROXIES = {
        'http': os.environ.get('HTTP_PROXY', os.environ.get('HTTPS_PROXY')),
        'https': os.environ.get('HTTPS_PROXY', os.environ.get('HTTP_PROXY'))
    }

# 在侧边栏显示代理状态
with st.sidebar:
    if PROXIES:
        st.success("✅ 代理已启用")
        st.caption(f"代理地址: {PROXIES['http']}")
    else:
        st.info("💡 如遇连接问题，可配置代理")
        with st.expander("代理配置说明"):
            st.code("""# Windows CMD:
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
streamlit run app_v3.py

# Windows PowerShell:
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
streamlit run app_v3.py""", language='bash')

# ========== 3. 多交易所客户端（支持代理）==========
class MultiExchangeClient:
    """
    多交易所客户端：
    - 优先级：KuCoin > Gate.io > Binance > OKX > CoinGecko
    - 支持代理配置
    - 自动故障转移
    """
    
    EXCHANGES = {
        "KuCoin": {
            "priority": 1,
            "urls": ["https://api.kucoin.com"],
            "kline_endpoint": "/api/v1/market/candles",
            "depth_endpoint": "/api/v1/market/orderbook/level2_20",
            "params": {"symbol": "ETH-USDT", "type": "5min"},
            "test_url": "/api/v1/timestamp"
        },
        "Gate.io": {
            "priority": 2,
            "urls": ["https://api.gateio.ws"],
            "kline_endpoint": "/api/v4/spot/candlesticks",
            "depth_endpoint": "/api/v4/spot/order_book",
            "params": {"currency_pair": "ETH_USDT", "interval": "5m", "limit": 200},
            "test_url": "/api/v4/spot/time"
        },
        "Binance": {
            "priority": 3,
            "urls": [
                "https://api.binance.com",
                "https://api1.binance.com",
                "https://data-api.binance.vision",
            ],
            "kline_endpoint": "/api/v3/klines",
            "depth_endpoint": "/api/v3/depth",
            "params": {"symbol": "ETHUSDT", "interval": "5m", "limit": 200},
            "test_url": "/api/v3/ping"
        },
        "OKX": {
            "priority": 4,
            "urls": ["https://www.okx.com"],
            "kline_endpoint": "/api/v5/market/candles",
            "depth_endpoint": "/api/v5/market/books",
            "params": {"instId": "ETH-USDT", "bar": "5m", "limit": 200},
            "test_url": "/api/v5/public/time"
        },
    }
    
    def __init__(self, proxies=None):
        self.session = requests.Session()
        
        # 配置代理
        if proxies:
            self.session.proxies.update(proxies)
            print(f"✅ 使用代理: {proxies}")
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.available_exchanges = {}
    
    def test_all_connections(self):
        """测试所有交易所连接"""
        results = {}
        
        for name, config in self.EXCHANGES.items():
            try:
                url = f"{config['urls'][0]}{config['test_url']}"
                start = time.time()
                resp = self.session.get(url, timeout=5)
                latency = (time.time() - start) * 1000
                
                if resp.status_code == 200:
                    results[name] = {"status": True, "latency": latency}
                    self.available_exchanges[name] = config['urls'][0]
                else:
                    results[name] = {"status": False, "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                results[name] = {"status": False, "error": str(e)[:40]}
        
        return results
    
    def fetch_klines_and_depth(self):
        """获取K线和订单簿数据（按优先级尝试）"""
        # 按优先级排序
        sorted_exchanges = sorted(
            self.EXCHANGES.items(), 
            key=lambda x: x[1]['priority']
        )
        
        for exchange_name, config in sorted_exchanges:
            for base_url in config['urls']:
                try:
                    # 获取K线
                    kline_url = f"{base_url}{config['kline_endpoint']}"
                    kline_resp = self.session.get(
                        kline_url,
                        params=config['params'],
                        timeout=10
                    )
                    
                    if kline_resp.status_code != 200:
                        continue
                    
                    # 获取订单簿
                    depth_params = {"symbol": "ETH-USDT", "limit": 20} if exchange_name == "KuCoin" else \
                                  {"currency_pair": "ETH_USDT", "limit": 20} if exchange_name == "Gate.io" else \
                                  {"symbol": "ETHUSDT", "limit": 20} if exchange_name == "Binance" else \
                                  {"instId": "ETH-USDT", "sz": 20}
                    
                    depth_url = f"{base_url}{config['depth_endpoint']}"
                    depth_resp = self.session.get(
                        depth_url,
                        params=depth_params,
                        timeout=10
                    )
                    
                    if depth_resp.status_code != 200:
                        continue
                    
                    # 解析数据
                    klines = kline_resp.json()
                    depth = depth_resp.json()
                    
                    df, imbalance, walls, depth_desc = self._parse_exchange_data(
                        exchange_name, klines, depth
                    )
                    
                    if df is not None and not df.empty:
                        return df, imbalance, walls, f"{exchange_name} | {depth_desc}"
                    
                except Exception as e:
                    print(f"{exchange_name} ({base_url}) 失败: {e}")
                    continue
        
        # 所有交易所都失败，尝试 CoinGecko 兜底
        return self._fetch_from_coingecko()
    
    def _parse_exchange_data(self, exchange_name, klines, depth):
        """根据交易所解析数据"""
        try:
            if exchange_name == "KuCoin":
                return self._parse_kucoin(klines, depth)
            elif exchange_name == "Gate.io":
                return self._parse_gate(klines, depth)
            elif exchange_name == "Binance":
                return self._parse_binance(klines, depth)
            elif exchange_name == "OKX":
                return self._parse_okx(klines, depth)
        except Exception as e:
            print(f"解析 {exchange_name} 数据失败: {e}")
            return None, 0, {}, f"解析错误: {e}"
    
    def _parse_kucoin(self, klines, depth):
        """解析 KuCoin 数据"""
        # KuCoin K线格式: [时间, 开, 收, 高, 低, 成交量, 成交额]
        data = klines.get('data', [])
        if not data:
            return None, 0, {}, "无数据"
        
        df = pd.DataFrame(data, columns=[
            "time","open","close","high","low","volume","turnover"
        ])
        df = df[["time","open","high","low","close","volume"]]
        cols = ["open","high","low","close","volume"]
        df[cols] = df[cols].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit='s')
        df = df.sort_values("time").reset_index(drop=True)
        
        # 订单簿
        bids = depth.get('data', {}).get('bids', [])
        asks = depth.get('data', {}).get('asks', [])
        bid_vol = sum(float(b[1]) for b in bids) if bids else 0
        ask_vol = sum(float(a[1]) for a in asks) if asks else 0
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
        
        walls = self._detect_walls(bids, asks, bid_vol, ask_vol)
        depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
        
        return df, imbalance, walls, depth_desc
    
    def _parse_gate(self, klines, depth):
        """解析 Gate.io 数据"""
        # Gate.io K线格式: [时间戳, 成交量, 收, 高, 低, 开]
        if not klines:
            return None, 0, {}, "无数据"
        
        df = pd.DataFrame(klines, columns=["timestamp","volume","close","high","low","open"])
        df = df[["timestamp","open","high","low","close","volume"]]
        df.columns = ["time","open","high","low","close","volume"]
        cols = ["open","high","low","close","volume"]
        df[cols] = df[cols].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit='s')
        df = df.sort_values("time").reset_index(drop=True)
        
        bids = depth.get('bids', [])
        asks = depth.get('asks', [])
        bid_vol = sum(float(b[1]) for b in bids) if bids else 0
        ask_vol = sum(float(a[1]) for a in asks) if asks else 0
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
        
        walls = self._detect_walls(bids, asks, bid_vol, ask_vol)
        depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
        
        return df, imbalance, walls, depth_desc
    
    def _parse_binance(self, klines, depth):
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
        bid_vol = sum(float(b[1]) for b in bids) if bids else 0
        ask_vol = sum(float(a[1]) for a in asks) if asks else 0
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
        
        walls = self._detect_walls(bids, asks, bid_vol, ask_vol)
        depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
        
        return df, imbalance, walls, depth_desc
    
    def _parse_okx(self, klines, depth):
        """解析 OKX 数据"""
        data = klines.get('data', [])
        if not data:
            return None, 0, {}, "无数据"
        
        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume","volCcy","volCcyQuote","confirm"
        ])
        cols = ["open","high","low","close","volume"]
        df[cols] = df[cols].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df = df.sort_values("time").reset_index(drop=True)
        
        bids = depth.get('data', [{}])[0].get('bids', [])
        asks = depth.get('data', [{}])[0].get('asks', [])
        bid_vol = sum(float(b[3]) for b in bids) if bids else 0
        ask_vol = sum(float(a[3]) for a in asks) if asks else 0
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
        
        walls = self._detect_walls(bids, asks, bid_vol, ask_vol, is_okx=True)
        depth_desc = f"买盘:{bid_vol:.1f} vs 卖盘:{ask_vol:.1f}"
        
        return df, imbalance, walls, depth_desc
    
    def _detect_walls(self, bids, asks, bid_vol, ask_vol, is_okx=False):
        """检测大单墙"""
        walls = {}
        if not bids or not asks:
            return walls
        
        avg_bid = bid_vol / len(bids) if bids else 0
        avg_ask = ask_vol / len(asks) if asks else 0
        
        for i, order in enumerate(bids):
            vol = float(order[3] if is_okx else order[1])
            if vol > avg_bid * 3:
                walls['support'] = float(order[0])
                break
        
        for i, order in enumerate(asks):
            vol = float(order[3] if is_okx else order[1])
            if vol > avg_ask * 3:
                walls['resistance'] = float(order[0])
                break
        
        return walls
    
    def _fetch_from_coingecko(self):
        """CoinGecko 兜底方案（只能获取价格，无K线）"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "ethereum",
                "vs_currencies": "usd",
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            }
            
            resp = self.session.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json().get('ethereum', {})
                price = data.get('usd', 0)
                change_24h = data.get('usd_24h_change', 0)
                vol_24h = data.get('usd_24h_vol', 0)
                
                # 创建一个简单的DataFrame（仅用于显示价格）
                df = pd.DataFrame({
                    'time': [datetime.datetime.now()],
                    'open': [price],
                    'high': [price],
                    'low': [price],
                    'close': [price],
                    'volume': [vol_24h]
                })
                
                return df, 0, {}, f"CoinGecko | 价格: ${price:.2f} | 24h变化: {change_24h:.2f}%"
            
        except Exception as e:
            print(f"CoinGecko 访问失败: {e}")
        
        return None, 0, {}, "所有数据源连接失败"

# ========== 4. 初始化客户端 ==========
@st.cache_resource
def get_client():
    return MultiExchangeClient(proxies=PROXIES if PROXIES else None)

# ========== 5. 核心功能 ==========
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

# ========== 6. 数据获取 ==========
@st.cache_data(ttl=5, show_spinner=False)
def get_market_data():
    """获取市场数据"""
    client = get_client()
    
    df, imbalance, walls, status_msg = client.fetch_klines_and_depth()
    
    if df is None or df.empty:
        return pd.DataFrame(), 0, {}, status_msg
    
    # 计算指标（如果数据足够）
    if len(df) >= 50:
        df["ma20"] = df["close"].rolling(20).mean()
        df["ma50"] = df["close"].rolling(50).mean()
        df["vol_ma"] = df["volume"].rolling(20).mean()
        df["vol_ratio"] = df["volume"] / df["vol_ma"]
    else:
        # CoinGecko 只有一条数据
        df["ma20"] = df["close"]
        df["ma50"] = df["close"]
        df["vol_ma"] = df["volume"]
        df["vol_ratio"] = 1.0
    
    return df, imbalance, walls, status_msg

# ========== 7. 主程序 ==========
def main():
    st_autorefresh(interval=10000, key="main_refresh")
    
    st.title("🚀 ETHUSDT 全网节点量化系统")
    
    client = get_client()
    
    # 启动时自动测试连接（仅首次）
    if 'connection_tested' not in st.session_state:
        st.info("🔍 首次启动，正在测试节点连接...")
        results = client.test_all_connections()
        st.session_state['connection_tested'] = True
        st.session_state['connection_results'] = results
    
    # 连接测试按钮和状态显示
    with st.sidebar:
        st.markdown("### 🌐 节点状态")
        
        # 显示之前测试的结果
        if 'connection_results' in st.session_state:
            results = st.session_state['connection_results']
            available_count = sum(1 for r in results.values() if r['status'])
            st.metric("可用节点", f"{available_count}/{len(results)}")
            
            with st.expander("详细状态", expanded=False):
                for name, info in results.items():
                    if info['status']:
                        st.success(f"✅ {name}: {info['latency']:.0f}ms")
                    else:
                        st.error(f"❌ {name}: {info.get('error', '连接失败')}")
        
        if st.button("🔄 重新测试连接", key="test_all"):
            with st.spinner("测试中..."):
                results = client.test_all_connections()
                st.session_state['connection_results'] = results
                st.rerun()
    
    st.markdown(f"**系统时间**: {datetime.datetime.now().strftime('%H:%M:%S')} | **数据源**: KuCoin/Gate.io/Binance/OKX/CoinGecko")
    
    # 获取数据
    with st.spinner("📡 正在获取数据（自动选择最优节点）..."):
        df, imbalance, walls, status_msg = get_market_data()
    
    if df.empty or df is None:
        st.error("❌ 所有节点连接失败")
        st.warning(f"**详情**: {status_msg}")
        
        st.markdown("### 🔧 解决方案")
        st.markdown("""
        1. **配置代理**（推荐）：
           - 在终端运行前设置环境变量
           - Windows CMD: `set HTTPS_PROXY=http://127.0.0.1:7890`
           - PowerShell: `$env:HTTPS_PROXY="http://127.0.0.1:7890"`
        
        2. **检查网络**：
           - 确认可以访问外网
           - 尝试关闭防火墙/杀毒软件
        
        3. **使用VPN**：
           - 连接海外节点后重启应用
        """)
        st.stop()
    
    # 显示数据源
    st.info(f"📡 {status_msg}")
    
    # 计算状态
    last = df.iloc[-1]
    price = last['close']
    vol_ratio = last.get('vol_ratio', 1.0)
    trend = "上涨" if last['ma20'] > last['ma50'] else "下跌" if len(df) > 1 else "未知"
    
    # ========== 高级信号分析 ==========
    advanced_signals = None
    if ADVANCED_SIGNALS_AVAILABLE and len(df) >= 20:
        with st.spinner("🔍 执行高级信号分析..."):
            try:
                advanced_signals = comprehensive_signal_analysis(df, order_imbalance=imbalance, walls=walls)
            except Exception as e:
                st.warning(f"高级信号分析失败: {e}")
    
    # 基础信号生成
    signals = []
    if len(df) > 1:
        if last['close'] > last['ma20']: signals.append("价格站上MA20")
        if vol_ratio > 2.0: signals.append(f"巨量异动({vol_ratio:.1f}倍)")
        if imbalance > 0.4: signals.append("买盘压倒")
        elif imbalance < -0.4: signals.append("卖盘压倒")
    
    # 共振判断
    resonance = "无共振"
    if trend == "上涨" and imbalance > 0.3: resonance = "多头共振"
    elif trend == "下跌" and imbalance < -0.3: resonance = "空头共振"
    
    # 页面布局
    if len(df) > 1:
        col_chart, col_ai = st.columns([1.5, 1])
    else:
        # CoinGecko 模式：只显示价格卡片
        col_chart, col_ai = st.columns([1, 1])
    
    with col_chart:
        if len(df) > 1:
            st.subheader("📈 实时行情 (5m)")
            fig = go.Figure()
            # K线图（绿色上涨，红色下跌 - 中国标准）
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
            
            # 高级支撑压力位
            if advanced_signals and 'signals' in advanced_signals:
                sr = advanced_signals['signals'].get('support_resistance', {})
                if sr.get('nearest_support'):
                    fig.add_hline(y=sr['nearest_support'][1], line_dash="dot", 
                                  line_color="green", opacity=0.5,
                                  annotation_text=f"支撑 {sr['nearest_support'][0]}", 
                                  annotation_position="right")
                if sr.get('nearest_resistance'):
                    fig.add_hline(y=sr['nearest_resistance'][1], line_dash="dot", 
                                  line_color="red", opacity=0.5,
                                  annotation_text=f"压力 {sr['nearest_resistance'][0]}", 
                                  annotation_position="right")
            elif 'support' in walls:
                fig.add_hline(y=walls['support'], line_dash="dash", line_color="green", 
                              annotation_text="支撑墙", annotation_position="right")
            if 'resistance' in walls:
                fig.add_hline(y=walls['resistance'], line_dash="dash", line_color="red", 
                              annotation_text="压力墙", annotation_position="right")
                
            fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.subheader("📊 当前价格")
            st.markdown(f"# ${price:.2f}")
            st.markdown(f"**成交量**: {last['volume']:.0f} USDT")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("当前价格", f"{price:.2f}", f"{df['close'].iloc[-1] - df['close'].iloc[-2]:.2f}" if len(df) > 1 else "0.00")
        c2.metric("量比", f"{vol_ratio:.2f}", delta="放量" if vol_ratio > 1.5 else "缩量")
        c3.metric("盘口失衡", f"{imbalance:.2f}", delta="多头优势" if imbalance > 0.1 else "空头优势")
        
        # ========== 高级信号显示 ==========
        if advanced_signals and 'signals' in advanced_signals:
            st.markdown("---")
            st.subheader("🎯 高级信号分析")
            
            # 综合建议
            rec = advanced_signals['recommendation']
            conf = advanced_signals['confidence']
            if rec == "做多":
                st.success(f"📊 **综合建议**: {rec} (置信度 {conf:.0f}%)")
            elif rec == "做空":
                st.error(f"📊 **综合建议**: {rec} (置信度 {conf:.0f}%)")
            else:
                st.info(f"📊 **综合建议**: {rec} (置信度 {conf:.0f}%)")
            
            # 各项指标
            sig_data = advanced_signals['signals']
            
            col1, col2 = st.columns(2)
            with col1:
                # 主力吸筹
                acc = sig_data.get('accumulation', {})
                if acc.get('signal'):
                    st.warning(f"🔍 **主力吸筹**: {acc['description']}")
                
                # 巨鲸拉升
                whale = sig_data.get('whale_pump', {})
                if whale.get('signal'):
                    st.success(f"🐋 **巨鲸拉升**: {whale['description']}")
                
                # 急跌风险
                crash = sig_data.get('crash_warning', {})
                if crash.get('signal'):
                    st.error(f"⚠️ **急跌风险**: {crash['description']} (风险等级: {crash.get('risk_level', '低')})")
                
                # LSTM预测
                lstm = sig_data.get('lstm_prediction', {})
                st.info(f"🤖 **LSTM预测**: {lstm.get('description', '分析中')}")
            
            with col2:
                # 量价口诀
                vp = sig_data.get('volume_price', {})
                st.write(f"📖 **量价口诀**: {vp.get('signal', '无信号')}")
                
                # 市场结构
                ms = sig_data.get('market_structure', {})
                st.write(f"🏛️ **市场结构**: {ms.get('description', '分析中')}")
                
                # 假突破
                fake = sig_data.get('fake_breakout', {})
                if fake.get('signal'):
                    st.warning(f"🎭 **假突破检测**: {fake.get('type', '检测到假突破')}")
                
                # 支撑压力
                sr = sig_data.get('support_resistance', {})
                st.write(f"📍 **支撑压力**: {sr.get('description', '计算中')}")

    with col_ai:
        st.subheader("🧠 AI 审计中心")
        
        # 显示基础信号
        if signals:
            st.write("**当前触发信号**:")
            st.write(", ".join([f"`{s}`" for s in signals]))
        else:
            st.write("**当前触发信号**: 无明确信号")
        
        # 显示共振判断
        st.write(f"**共振状态**: `{resonance}`")
        
        # 显示高级信号摘要
        if advanced_signals:
            st.markdown("---")
            st.markdown(f"**综合评分**:")
            st.write(f"- 做多得分: `{advanced_signals['bullish_score']:.0f}`")
            st.write(f"- 做空得分: `{advanced_signals['bearish_score']:.0f}`")
            
        st.markdown("---")
        
        # AI分析
        with st.spinner("🕵️ AI深度分析中..."):
            # 使用高级信号生成AI提示词
            if ADVANCED_SIGNALS_AVAILABLE and advanced_signals:
                prompt = ai_audit_ollama(df, imbalance)
            else:
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
                st.info("💡 备用建议：关注 MA20 支撑，结合量能操作")
                
                # 使用高级信号给出建议
                if advanced_signals:
                    st.info(f"📊 **智能建议**: {advanced_signals['summary']}")
            else:
                st.markdown(ai_report)
                
                # 语音播报重要信号（精准触发）
                if ADVANCED_SIGNALS_AVAILABLE and advanced_signals:
                    rec = advanced_signals['recommendation']
                    bull_score = advanced_signals['bullish_score']
                    bear_score = advanced_signals['bearish_score']
                    sig_data = advanced_signals.get('signals', {})
                    
                    # 高置信度信号播报
                    if rec in ["做多", "做空"] and advanced_signals['confidence'] >= 75:
                        speak_alert(f"重要提醒，{rec}信号确认，置信度{advanced_signals['confidence']:.0f}%")
                    
                    # 巨鲸拉升播报
                    whale = sig_data.get('whale_pump', {})
                    if whale.get('signal'):
                        speak_alert(f"巨鲸拉升检测，{whale.get('description', '大资金进场')}")
                    
                    # 急跌风险播报
                    crash = sig_data.get('crash_warning', {})
                    if crash.get('signal') and crash.get('risk_level') == '高':
                        speak_alert(f"危险，急跌风险高，{crash.get('description', '注意风险')}")
                    
                    # 主力吸筹播报
                    acc = sig_data.get('accumulation', {})
                    if acc.get('signal') and acc.get('strength', 0) >= 70:
                        speak_alert(f"主力吸筹信号，{acc.get('description', '关注做多机会')}")
                    
                    # 多头共振播报
                    if "多头共振" in resonance and vol_ratio > 1.5:
                        speak_alert(f"多头共振确认，量比{vol_ratio:.1f}，关注做多机会")
                    
                    # 空头共振播报  
                    elif "空头共振" in resonance:
                        speak_alert("空头共振，注意风险控制")

if __name__ == "__main__":
    main()
