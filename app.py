import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import threading
import datetime
import os
import sys
from streamlit_autorefresh import st_autorefresh
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 导入升级版高级信号模块
try:
    from advanced_signals_v2 import (
        calculate_vwap,
        calculate_ema,
        calculate_cvd,
        calculate_atr,
        detect_market_state,
        calculate_support_resistance_v2,
        calculate_order_imbalance,
        detect_accumulation_v2,
        lstm_predict_v2,
        fake_breakout_v2,
        whale_pump_v2,
        crash_warning_v2,
        volume_price_mnemonics_v2,
        get_funding_rate,
        get_open_interest,
        get_liquidations,
        comprehensive_signal_analysis_v2,
        speak_alert
    )
    ADVANCED_SIGNALS_AVAILABLE = True
except ImportError as e:
    ADVANCED_SIGNALS_AVAILABLE = False
    print(f"⚠️ 升级版高级信号模块未加载: {e}")

# ========== 1. 页面配置 ==========
st.set_page_config(
    page_title="ETHUSDT 机构级量化巡航系统 V2.0", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ========== 深色主题样式 ==========
st.markdown("""
<style>
    /* 全局深色背景 */
    .stApp {
        background-color: #0e1117 !important;
        color: #fafafa !important;
    }
    
    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: #1a1a2e !important;
    }
    
    /* 标题文字 */
    h1, h2, h3, h4, h5, h6 {
        color: #fafafa !important;
    }
    
    /* Metric卡片 */
    [data-testid="stMetric"] {
        background-color: #1e1e2e !important;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #2d2d3d;
    }
    [data-testid="stMetric"] label {
        color: #9ca3af !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #fafafa !important;
        font-size: 1.5rem !important;
    }
    
    /* Info/Success/Warning/Error框 */
    [data-testid="stAlert"] {
        background-color: #1e1e2e !important;
        border: 1px solid #3d3d4d !important;
    }
    [data-testid="stAlert"] p {
        color: #fafafa !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1e1e2e !important;
        color: #fafafa !important;
    }
    .streamlit-expanderContent {
        background-color: #1a1a2e !important;
    }
    
    /* 按钮 */
    .stButton button {
        background-color: #2d2d3d !important;
        color: #fafafa !important;
        border: 1px solid #3d3d4d !important;
    }
    .stButton button:hover {
        background-color: #3d3d4d !important;
        border-color: #4d4d5d !important;
    }
    
    /* 输入框 */
    .stTextInput input, .stNumberInput input {
        background-color: #1e1e2e !important;
        color: #fafafa !important;
        border-color: #3d3d4d !important;
    }
    
    /* Selectbox */
    .stSelectbox div[data-baseweb="select"] {
        background-color: #1e1e2e !important;
    }
    
    /* DataFrame/表格 */
    .stDataFrame {
        background-color: #1e1e2e !important;
    }
    table {
        background-color: #1e1e2e !important;
        color: #fafafa !important;
    }
    thead th {
        background-color: #2d2d3d !important;
        color: #fafafa !important;
    }
    tbody tr {
        background-color: #1e1e2e !important;
    }
    tbody tr:hover {
        background-color: #2d2d3d !important;
    }
    
    /* 分隔线 */
    hr {
        border-color: #3d3d4d !important;
    }
    
    /* 列容器 */
    [data-testid="column"] {
        background-color: transparent !important;
    }
    
    /* Markdown文本 */
    .stMarkdown p, .stMarkdown li {
        color: #e5e5e5 !important;
    }
    
    /* 成功/错误/警告颜色 */
    .element-container .stSuccess {
        background-color: rgba(34, 197, 94, 0.15) !important;
        border-color: #22c55e !important;
    }
    .element-container .stError {
        background-color: rgba(239, 68, 68, 0.15) !important;
        border-color: #ef4444 !important;
    }
    .element-container .stWarning {
        background-color: rgba(234, 179, 8, 0.15) !important;
        border-color: #eab308 !important;
    }
    .element-container .stInfo {
        background-color: rgba(59, 130, 246, 0.15) !important;
        border-color: #3b82f6 !important;
    }
    
    /* 代码块 */
    code {
        background-color: #2d2d3d !important;
        color: #e5e5e5 !important;
    }
    
    /* 图表容器背景 */
    .plotly-chart {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# ========== 2. 代理配置 ==========
PROXIES = {}
if os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY'):
    PROXIES = {
        'http': os.environ.get('HTTP_PROXY', os.environ.get('HTTPS_PROXY')),
        'https': os.environ.get('HTTPS_PROXY', os.environ.get('HTTP_PROXY'))
    }

# ========== 3. 多交易所客户端（升级版）==========
class MultiExchangeClientV2:
    """
    多交易所客户端 V2.0
    - 支持代理配置
    - 自动故障转移
    - 价格统一（多交易所平均）
    - API断线自动重连
    """
    
    EXCHANGES = {
        "Binance": {
            "priority": 1,
            "urls": ["https://api.binance.com", "https://api1.binance.com", "https://data-api.binance.vision"],
            "kline_endpoint": "/api/v3/klines",
            "depth_endpoint": "/api/v3/depth",
            "params": {"symbol": "ETHUSDT", "interval": "5m", "limit": 200},
            "test_url": "/api/v3/ping"
        },
        "OKX": {
            "priority": 2,
            "urls": ["https://www.okx.com"],
            "kline_endpoint": "/api/v5/market/candles",
            "depth_endpoint": "/api/v5/market/books",
            "params": {"instId": "ETH-USDT", "bar": "5m", "limit": 200},
            "test_url": "/api/v5/public/time"
        },
        "KuCoin": {
            "priority": 3,
            "urls": ["https://api.kucoin.com"],
            "kline_endpoint": "/api/v1/market/candles",
            "depth_endpoint": "/api/v1/market/orderbook/level2_20",
            "params": {"symbol": "ETH-USDT", "type": "5min"},
            "test_url": "/api/v1/timestamp"
        },
        "Gate.io": {
            "priority": 4,
            "urls": ["https://api.gateio.ws"],
            "kline_endpoint": "/api/v4/spot/candlesticks",
            "depth_endpoint": "/api/v4/spot/order_book",
            "params": {"currency_pair": "ETH_USDT", "interval": "5m", "limit": 200},
            "test_url": "/api/v4/spot/time"
        },
    }
    
    def __init__(self, proxies=None):
        self.session = requests.Session()
        
        # 配置代理
        if proxies:
            self.session.proxies.update(proxies)
            print(f"✅ 使用代理: {proxies}")
        
        # 配置重试策略（断线自动重连）
        retry_strategy = Retry(
            total=5,  # 增加重试次数
            backoff_factor=2,  # 指数退避
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.available_exchanges = {}
        self.connection_errors = {}
    
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
        """
        获取K线和订单簿数据（多交易所统一价格）
        返回：DataFrame, 盘口失衡, 大单墙, 状态信息
        """
        # 收集所有可用交易所的数据
        all_prices = []
        all_dfs = []
        all_imbalances = []
        
        for exchange_name, config in self.EXCHANGES.items():
            if exchange_name not in self.available_exchanges:
                continue
            
            try:
                base_url = self.available_exchanges[exchange_name]
                
                # 获取K线
                kline_url = f"{base_url}{config['kline_endpoint']}"
                kline_resp = self.session.get(kline_url, params=config['params'], timeout=10)
                
                if kline_resp.status_code != 200:
                    continue
                
                # 获取订单簿
                depth_params = self._get_depth_params(exchange_name)
                depth_url = f"{base_url}{config['depth_endpoint']}"
                depth_resp = self.session.get(depth_url, params=depth_params, timeout=10)
                
                if depth_resp.status_code != 200:
                    continue
                
                # 解析数据
                klines = kline_resp.json()
                depth = depth_resp.json()
                
                df, imbalance, walls, price = self._parse_exchange_data_v2(exchange_name, klines, depth)
                
                if df is not None and not df.empty:
                    all_dfs.append((exchange_name, df))
                    all_imbalances.append(imbalance)
                    if price > 0:
                        all_prices.append(price)
                
            except Exception as e:
                self.connection_errors[exchange_name] = str(e)
                print(f"{exchange_name} 获取失败: {e}")
                continue
        
        # 如果没有任何数据，尝试CoinGecko兜底
        if not all_dfs:
            return self._fetch_from_coingecko()
        
        # 【关键】多交易所价格统一
        if len(all_prices) >= 2:
            # VWAP价格
            unified_price = sum(all_prices) / len(all_prices)
            status_msg = f"VWAP价格: ${unified_price:.2f} (来自{len(all_prices)}个交易所)"
        else:
            unified_price = all_prices[0] if all_prices else 0
            status_msg = f"单交易所价格: ${unified_price:.2f}"
        
        # 使用最优交易所的数据（优先级最高的）
        best_df = all_dfs[0][1]
        best_imbalance = all_imbalances[0] if all_imbalances else 0
        
        # 计算平均盘口失衡
        if all_imbalances:
            avg_imbalance = sum(all_imbalances) / len(all_imbalances)
        else:
            avg_imbalance = 0
        
        return best_df, avg_imbalance, {}, status_msg
    
    def _get_depth_params(self, exchange_name: str) -> dict:
        """获取订单簿参数"""
        params_map = {
            "KuCoin": {"symbol": "ETH-USDT", "limit": 20},
            "Gate.io": {"currency_pair": "ETH_USDT", "limit": 20},
            "Binance": {"symbol": "ETHUSDT", "limit": 20},
            "OKX": {"instId": "ETH-USDT", "sz": 20}
        }
        return params_map.get(exchange_name, {})
    
    def _parse_exchange_data_v2(self, exchange_name: str, klines, depth) -> tuple:
        """解析交易所数据（返回DataFrame, imbalance, walls, current_price）"""
        try:
            if exchange_name == "Binance":
                return self._parse_binance_v2(klines, depth)
            elif exchange_name == "OKX":
                return self._parse_okx_v2(klines, depth)
            elif exchange_name == "KuCoin":
                return self._parse_kucoin_v2(klines, depth)
            elif exchange_name == "Gate.io":
                return self._parse_gate_v2(klines, depth)
        except Exception as e:
            print(f"解析 {exchange_name} 数据失败: {e}")
            return None, 0, {}, 0
    
    def _parse_binance_v2(self, klines, depth):
        """解析币安数据"""
        if not klines:
            return None, 0, {}, 0
        
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
        
        # 使用优化后的盘口失衡算法
        imbalance_data = calculate_order_imbalance(bid_vol, ask_vol)
        imbalance = imbalance_data['imbalance']
        
        current_price = df['close'].iloc[-1]
        
        return df, imbalance, {}, current_price
    
    def _parse_okx_v2(self, klines, depth):
        """解析OKX数据"""
        data = klines.get('data', [])
        if not data:
            return None, 0, {}, 0
        
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
        
        imbalance_data = calculate_order_imbalance(bid_vol, ask_vol)
        imbalance = imbalance_data['imbalance']
        
        current_price = df['close'].iloc[-1]
        
        return df, imbalance, {}, current_price
    
    def _parse_kucoin_v2(self, klines, depth):
        """解析KuCoin数据"""
        data = klines.get('data', [])
        if not data:
            return None, 0, {}, 0
        
        df = pd.DataFrame(data, columns=["time","open","close","high","low","volume","turnover"])
        df = df[["time","open","high","low","close","volume"]]
        cols = ["open","high","low","close","volume"]
        df[cols] = df[cols].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit='s')
        df = df.sort_values("time").reset_index(drop=True)
        
        bids = depth.get('data', {}).get('bids', [])
        asks = depth.get('data', {}).get('asks', [])
        bid_vol = sum(float(b[1]) for b in bids) if bids else 0
        ask_vol = sum(float(a[1]) for a in asks) if asks else 0
        
        imbalance_data = calculate_order_imbalance(bid_vol, ask_vol)
        imbalance = imbalance_data['imbalance']
        
        current_price = df['close'].iloc[-1]
        
        return df, imbalance, {}, current_price
    
    def _parse_gate_v2(self, klines, depth):
        """解析Gate.io数据"""
        if not klines:
            return None, 0, {}, 0
        
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
        
        imbalance_data = calculate_order_imbalance(bid_vol, ask_vol)
        imbalance = imbalance_data['imbalance']
        
        current_price = df['close'].iloc[-1]
        
        return df, imbalance, {}, current_price
    
    def _fetch_from_coingecko(self):
        """CoinGecko兜底方案"""
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
    return MultiExchangeClientV2(proxies=PROXIES if PROXIES else None)


# ========== 5. AI 分析 ==========
def get_ai_analysis(prompt):
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "deepseek-r1:1.5b", "prompt": prompt, "stream": False, "options": {"temperature": 0.3, "num_predict": 150}},
            timeout=20
        )
        if resp.status_code == 200:
            return resp.json().get("response", "AI分析超时")
        return "AI服务连接失败"
    except:
        return "AI服务未启动"


# ========== 6. 数据获取 ==========
# 缓存市场数据，减少API调用
@st.cache_data(ttl=5, show_spinner=False)
def get_market_data():
    """获取市场数据（缓存5秒）"""
    client = get_client()
    
    df, imbalance, walls, status_msg = client.fetch_klines_and_depth()
    
    if df is None or df.empty:
        return pd.DataFrame(), 0, {}, status_msg
    
    # 计算基础指标
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
    
    return df, imbalance, walls, status_msg


# 缓存高级信号分析结果
@st.cache_data(ttl=10, show_spinner=False)
def get_advanced_signals_cached(df_hash, df, imbalance, walls):
    """缓存高级信号分析（10秒）"""
    return comprehensive_signal_analysis_v2(df, order_imbalance=imbalance, walls=walls)


# ========== 7. 生成AI审计提示词 ==========
def generate_ai_prompt_v2(df, advanced_signals):
    """生成升级版AI审计提示词"""
    if not advanced_signals or 'signals' not in advanced_signals:
        return "数据不足"
    
    last = df.iloc[-1]
    sig = advanced_signals['signals']
    
    # 安全获取EMA和VWAP数据
    ema21_val = df['ema21'].iloc[-1] if 'ema21' in df.columns and not df['ema21'].empty else 'N/A'
    ema200_val = df['ema200'].iloc[-1] if 'ema200' in df.columns and not df['ema200'].empty else 'N/A'
    vwap_val = df['vwap'].iloc[-1] if 'vwap' in df.columns and not df['vwap'].empty else 'N/A'
    
    prompt = f"""
作为量化交易AI分析师，分析ETHUSDT当前市场状态：

【价格数据】
当前价格: {last['close']:.2f}
EMA21: {ema21_val if ema21_val == 'N/A' else f'{ema21_val:.2f}'}
EMA200: {ema200_val if ema200_val == 'N/A' else f'{ema200_val:.2f}'}
VWAP: {vwap_val if vwap_val == 'N/A' else f'{vwap_val:.2f}'}
量比: {last.get('vol_ratio', 1):.2f}

【市场状态】
{sig.get('market_state', {}).get('description', '分析中')}

【核心信号】
1. LSTM预测: {sig.get('lstm_prediction', {}).get('description', '分析中')}
2. 主力吸筹: {sig.get('accumulation', {}).get('description', '无')} (强度{sig.get('accumulation', {}).get('strength', 0)})
3. 巨鲸拉升: {sig.get('whale_pump', {}).get('description', '无')} (强度{sig.get('whale_pump', {}).get('strength', 0)})
4. 急跌风险: {sig.get('crash_warning', {}).get('description', '无')} (风险{sig.get('crash_warning', {}).get('risk_level', '低')})
5. 量价口诀: {sig.get('volume_price', {}).get('mnemonic', '无')}
6. 假突破: {sig.get('fake_breakout', {}).get('description', '无')}

【支撑压力】
{sig.get('support_resistance', {}).get('description', '计算中')}

【资金情绪】
{sig.get('funding_rate', {}).get('description', '未知')}
{sig.get('open_interest', {}).get('description', '未知')}

【综合建议】
{advanced_signals['summary']}

请简要回答（100字内）：
1. 当前市场状态判断
2. 操作建议
3. 风险等级
"""
    return prompt


# ========== 8. 增强版K线图绘制 ==========
def plot_enhanced_candlestick(df, advanced_signals=None, trade_signals=None):
    """绘制增强版K线图 - 包含入场标记、止损止盈线、放量突破、CVD"""
    
    # 创建子图：K线 + 成交量 + CVD
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=('K线图', '成交量', 'CVD订单流')
    )
    
    # === K线图 ===
    fig.add_trace(go.Candlestick(
        x=df['time'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K线',
        increasing_line_color='#00FF00',
        decreasing_line_color='#FF0000',
        increasing_fillcolor='#00FF00',
        decreasing_fillcolor='#FF0000'
    ), row=1, col=1)
    
    # === EMA21 ===
    if 'ema21' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['time'], y=df['ema21'],
            line=dict(color='#FFA500', width=1.5),
            name='EMA21'
        ), row=1, col=1)
    
    # === EMA200 ===
    if 'ema200' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['time'], y=df['ema200'],
            line=dict(color='#1E90FF', width=1.5),
            name='EMA200'
        ), row=1, col=1)
    
    # === VWAP ===
    if 'vwap' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['time'], y=df['vwap'],
            line=dict(color='#9370DB', width=1.5, dash='dot'),
            name='VWAP'
        ), row=1, col=1)
    
    # === 支撑压力位（增强版）===
    if advanced_signals and 'signals' in advanced_signals:
        sr = advanced_signals['signals'].get('support_resistance', {})
        
        # 支撑位（带区域填充）
        if sr.get('nearest_support'):
            support_price = sr['nearest_support'][1]
            fig.add_hline(y=support_price, line_dash="dash", 
                         line_color="#00FF00", opacity=0.8, line_width=2,
                         annotation_text=f"支撑 ${support_price:.2f}",
                         annotation_position="right",
                         row=1, col=1)
            # 支撑区域
            fig.add_hrect(y0=support_price * 0.998, y1=support_price * 1.002,
                         fillcolor="green", opacity=0.1, line_width=0,
                         row=1, col=1)
        
        # 阻力位（带区域填充）
        if sr.get('nearest_resistance'):
            resistance_price = sr['nearest_resistance'][1]
            fig.add_hline(y=resistance_price, line_dash="dash",
                         line_color="#FF0000", opacity=0.8, line_width=2,
                         annotation_text=f"阻力 ${resistance_price:.2f}",
                         annotation_position="right",
                         row=1, col=1)
            # 阻力区域
            fig.add_hrect(y0=resistance_price * 0.998, y1=resistance_price * 1.002,
                         fillcolor="red", opacity=0.1, line_width=0,
                         row=1, col=1)
    
    # === 放量突破标注 ===
    if 'vol_ratio' in df.columns:
        vol_ratio = df['vol_ratio']
        high_vol_mask = vol_ratio > 1.5
        
        # 放量K线高亮
        for idx in df[high_vol_mask].index:
            row_data = df.loc[idx]
            # 放量标记
            fig.add_trace(go.Scatter(
                x=[row_data['time']], y=[row_data['low'] * 0.998],
                mode='markers',
                marker=dict(symbol='triangle-up', size=12, color='#FFD700', line=dict(color='#FFD700', width=2)),
                name='放量突破' if idx == df[high_vol_mask].index[0] else '',
                showlegend=True if idx == df[high_vol_mask].index[0] else False
            ), row=1, col=1)
    
    # === 交易信号标记（入场三角）===
    if trade_signals:
        for signal in trade_signals:
            idx = signal.get('index', len(df) - 1)
            if idx < len(df):
                row_data = df.iloc[idx]
                price = row_data['close']
                time_val = row_data['time']
                
                # 入场三角
                if signal['direction'] == 'LONG':
                    marker_symbol = 'triangle-up'
                    marker_color = '#00FF00'
                    y_position = price * 0.998  # 做多三角在K线下方
                else:
                    marker_symbol = 'triangle-down'
                    marker_color = '#FF0000'
                    y_position = price * 1.002  # 做空三角在K线上方
                
                # 根据置信度调整大小和样式
                marker_size = 18 if signal.get('confidence_level') == 'HIGH' else 14
                line_color = '#FFD700' if signal.get('confidence_level') == 'HIGH' else '#FFFFFF'
                
                fig.add_trace(go.Scatter(
                    x=[time_val], y=[y_position],
                    mode='markers+text',
                    marker=dict(
                        symbol=marker_symbol, 
                        size=marker_size, 
                        color=marker_color, 
                        line=dict(color=line_color, width=2)
                    ),
                    text=['入场' + ('做多' if signal['direction'] == 'LONG' else '做空')],
                    textposition='bottom center' if signal['direction'] == 'LONG' else 'top center',
                    textfont=dict(size=10, color=marker_color),
                    name=f"入场-{signal['direction']}",
                    showlegend=True
                ), row=1, col=1)
                
                # 止损线（橙红色虚线 + 区域填充）
                stop_loss = signal.get('stop_loss', price * 0.98)
                fig.add_hline(y=stop_loss, line_dash="dot",
                             line_color="#FF4500", opacity=0.9, line_width=2,
                             annotation_text=f"止损 ${stop_loss:.2f}",
                             annotation_position="left",
                             annotation_font=dict(size=11, color="#FF4500"),
                             row=1, col=1)
                # 止损区域
                if signal['direction'] == 'LONG':
                    fig.add_hrect(y0=stop_loss * 0.998, y1=stop_loss,
                                 fillcolor="#FF4500", opacity=0.15, line_width=0,
                                 row=1, col=1)
                
                # 止盈线（绿色虚线 + 区域填充）
                take_profit = signal.get('take_profit', price * 1.02)
                fig.add_hline(y=take_profit, line_dash="dot",
                             line_color="#32CD32", opacity=0.9, line_width=2,
                             annotation_text=f"止盈 ${take_profit:.2f}",
                             annotation_position="left",
                             annotation_font=dict(size=11, color="#32CD32"),
                             row=1, col=1)
                # 止盈区域
                if signal['direction'] == 'LONG':
                    fig.add_hrect(y0=take_profit, y1=take_profit * 1.002,
                                 fillcolor="#32CD32", opacity=0.15, line_width=0,
                                 row=1, col=1)
                
                # 半仓止盈线（虚线）
                if signal['direction'] == 'LONG':
                    half_profit = price + (take_profit - price) * 0.5
                else:
                    half_profit = price - (price - take_profit) * 0.5
                    
                fig.add_hline(y=half_profit, line_dash="dash",
                             line_color="#FFD700", opacity=0.6, line_width=1,
                             annotation_text=f"半仓 ${half_profit:.2f}",
                             annotation_position="left",
                             annotation_font=dict(size=9, color="#FFD700"),
                             row=1, col=1)
    
    # === 成交量柱状图 ===
    colors = ['#00FF00' if df.iloc[i]['close'] >= df.iloc[i]['open'] else '#FF0000' 
              for i in range(len(df))]
    
    # 放量高亮
    if 'vol_ratio' in df.columns:
        colors = ['#FFD700' if df.iloc[i]['vol_ratio'] > 1.5 else colors[i] 
                  for i in range(len(df))]
    
    fig.add_trace(go.Bar(
        x=df['time'], y=df['volume'],
        marker_color=colors,
        name='成交量',
        opacity=0.7
    ), row=2, col=1)
    
    # 成交量均线
    if 'vol_ma' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['time'], y=df['vol_ma'],
            line=dict(color='yellow', width=1),
            name='VOL MA20'
        ), row=2, col=1)
    
    # === CVD订单流 ===
    if 'cvd' in df.columns:
        cvd = df['cvd']
        fig.add_trace(go.Scatter(
            x=df['time'], y=cvd,
            line=dict(color='cyan', width=1.5),
            name='CVD',
            fill='tozeroy',
            fillcolor='rgba(0, 255, 255, 0.2)'
        ), row=3, col=1)
        
        # CVD正值/负值区域
        fig.add_trace(go.Scatter(
            x=df['time'], y=cvd.clip(lower=0),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 0, 0.3)',
            line=dict(color='rgba(0,255,0,0)'),
            name='CVD多',
            showlegend=False
        ), row=3, col=1)
        
        fig.add_trace(go.Scatter(
            x=df['time'], y=cvd.clip(upper=0),
            fill='tozeroy',
            fillcolor='rgba(255, 0, 0, 0.3)',
            line=dict(color='rgba(255,0,0,0)'),
            name='CVD空',
            showlegend=False
        ), row=3, col=1)
    
    # === 布局设置（深色主题）===
    fig.update_layout(
        template='plotly_dark',
        height=600,
        showlegend=True,
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1,
            font=dict(color='#e5e5e5', size=10),
            bgcolor='rgba(30, 30, 46, 0.8)'
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
        xaxis3_rangeslider_visible=False,
        # 深色背景
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='#e5e5e5')
    )
    
    # 设置所有坐标轴深色主题
    fig.update_xaxes(
        title_text="时间", 
        row=3, col=1,
        gridcolor='#2d2d3d',
        linecolor='#3d3d4d',
        tickfont=dict(color='#9ca3af')
    )
    fig.update_yaxes(
        title_text="价格", 
        row=1, col=1,
        gridcolor='#2d2d3d',
        linecolor='#3d3d4d',
        tickfont=dict(color='#9ca3af')
    )
    fig.update_yaxes(
        title_text="成交量", 
        row=2, col=1,
        gridcolor='#2d2d3d',
        linecolor='#3d3d4d',
        tickfont=dict(color='#9ca3af')
    )
    fig.update_yaxes(
        title_text="CVD", 
        row=3, col=1,
        gridcolor='#2d2d3d',
        linecolor='#3d3d4d',
        tickfont=dict(color='#9ca3af')
    )
    
    return fig


# ========== 9. 主程序 ==========
def main():
    # 【关键修复】使用st_autorefresh
    st_autorefresh(interval=5000, key="main_refresh")  # 5秒刷新
    
    st.title("🚀 ETHUSDT 机构级量化巡航系统 V2.0")
    
    client = get_client()
    
    # 连接状态管理
    if 'connection_tested' not in st.session_state:
        st.info("🔍 首次启动，正在测试节点连接...")
        results = client.test_all_connections()
        st.session_state['connection_tested'] = True
        st.session_state['connection_results'] = results
    
    # 侧边栏
    with st.sidebar:
        st.markdown("### 🌐 节点状态")
        
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
        
        # 显示升级信息
        st.markdown("---")
        st.markdown("### ⚡ V2.0 升级内容")
        st.markdown("""
        ✅ LSTM概率限制(85%上限)
        ✅ Dropout防过拟合
        ✅ VWAP机构成本
        ✅ CVD订单流
        ✅ EMA21/EMA200
        ✅ ATR波动率
        ✅ 成交量密集区
        ✅ 多交易所价格统一
        ✅ Funding Rate
        ✅ Open Interest
        ✅ 爆仓监控
        ✅ 语音播报
        ✅ 增强K线视觉图
        """)
    
    st.markdown(f"**系统时间**: {datetime.datetime.now().strftime('%H:%M:%S')} | **刷新间隔**: 5秒")
    
    # 获取数据
    with st.spinner("📡 正在获取数据..."):
        df, imbalance, walls, status_msg = get_market_data()
    
    if df.empty or df is None:
        st.error("❌ 所有节点连接失败")
        st.warning(f"**详情**: {status_msg}")
        st.stop()
    
    # 显示数据源
    st.info(f"📡 {status_msg}")
    
    # 计算基础状态
    last = df.iloc[-1]
    price = last['close']
    vol_ratio = last.get('vol_ratio', 1.0)
    
    # ========== 高级信号分析 ==========
    advanced_signals = None
    if ADVANCED_SIGNALS_AVAILABLE and len(df) >= 50:
        with st.spinner("🔍 执行高级信号分析..."):
            try:
                # 使用缓存的高级信号分析
                df_hash = hash(df.to_json())  # 创建数据哈希作为缓存键
                advanced_signals = get_advanced_signals_cached(df_hash, df, imbalance, walls)
                # 获取计算后的DataFrame
                if 'df' in advanced_signals:
                    df = advanced_signals['df']
            except Exception as e:
                st.warning(f"高级信号分析失败: {e}")
    
    # 基础信号生成
    signals = []
    if len(df) > 1:
        if 'ema21' in df.columns and last['close'] > df['ema21'].iloc[-1]:
            signals.append("价格站上EMA21")
        if vol_ratio > 2.0:
            signals.append(f"巨量异动({vol_ratio:.1f}倍)")
        
        imbalance_data = calculate_order_imbalance(100*(1+imbalance), 100*(1-imbalance))
        if imbalance > 0.3:
            signals.append(f"买盘优势({imbalance:.2f})")
        elif imbalance < -0.3:
            signals.append(f"卖盘优势({imbalance:.2f})")
    
    # ========== 增强版K线图 ==========
    st.subheader("📈 增强版K线图")
    
    # 生成交易信号（如果有）
    trade_signals = []
    if advanced_signals and advanced_signals.get('confidence', 0) >= 50:
        rec = advanced_signals['recommendation']
        if rec in ['做多', '做空']:
            sr = advanced_signals['signals'].get('support_resistance', {})
            
            # 安全获取止损止盈价格
            nearest_support = sr.get('nearest_support')
            nearest_resistance = sr.get('nearest_resistance')
            
            # 止损：做多用支撑，做空用阻力
            if rec == '做多':
                stop_loss = nearest_support[1] if nearest_support else price * 0.98
                take_profit = nearest_resistance[1] if nearest_resistance else price * 1.02
            else:
                stop_loss = nearest_resistance[1] if nearest_resistance else price * 1.02
                take_profit = nearest_support[1] if nearest_support else price * 0.98
            
            trade_signals.append({
                'direction': 'LONG' if rec == '做多' else 'SHORT',
                'index': len(df) - 1,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence_level': 'HIGH' if advanced_signals['confidence'] >= 80 else 'MID'
            })
    
    fig = plot_enhanced_candlestick(df, advanced_signals, trade_signals)
    st.plotly_chart(fig, use_container_width=True)
    
    # 基础指标
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("当前价格", f"{price:.2f}")
    c2.metric("量比", f"{vol_ratio:.2f}", delta="放量" if vol_ratio > 1.5 else "缩量")
    
    imbalance_data = calculate_order_imbalance(100*(1+imbalance), 100*(1-imbalance))
    c3.metric("盘口失衡", f"{imbalance:.2f}", delta=imbalance_data['status'])
    
    # ATR波动率
    if 'atr_pct' in df.columns:
        atr_pct = df['atr_pct'].iloc[-1]
        c4.metric("ATR波动率", f"{atr_pct:.2f}%")
    
    # ========== 🎯 综合信号分析 和 🧠 AI审计中心 并排显示 ==========
    st.markdown("---")
    col_signal, col_ai = st.columns([1.2, 1])
    
    # === 🎯 综合信号分析（左侧）===
    with col_signal:
        st.subheader("🎯 综合信号分析")
        
        if advanced_signals and 'signals' in advanced_signals:
            # 综合建议
            rec = advanced_signals['recommendation']
            conf = advanced_signals['confidence']
            
            # 语音播报重要信号（置信度>70%）
            if conf >= 70:
                alert_text = f"注意，ETHUSDT {rec}信号，置信度{conf:.0f}%"
                try:
                    speak_alert(alert_text)
                except:
                    pass  # 忽略语音播报错误
            
            if rec == "做多":
                st.success(f"📊 **综合建议**: {rec} (置信度 {conf:.0f}%)")
            elif rec == "做空":
                st.error(f"📊 **综合建议**: {rec} (置信度 {conf:.0f}%)")
            else:
                st.info(f"📊 **综合建议**: {rec} (置信度 {conf:.0f}%)")
            
            sig_data = advanced_signals['signals']
            
            # 第一行
            col1, col2, col3 = st.columns(3)
            with col1:
                # 市场状态
                ms = sig_data.get('market_state', {})
                st.info(f"🏛️ **市场状态**: {ms.get('state', '分析中')} (强度{ms.get('strength', 0):.0f})")
                
                # LSTM预测
                lstm = sig_data.get('lstm_prediction', {})
                st.info(f"🤖 **AI预测**: {lstm.get('trend', '分析中')} ({lstm.get('probability', 0):.0f}%)")
            
            with col2:
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
                    st.error(f"⚠️ **急跌风险**: {crash['description']}")
            
            with col3:
                # 假突破
                fake = sig_data.get('fake_breakout', {})
                if fake.get('signal'):
                    st.warning(f"🎭 **假突破**: {fake.get('type', '检测到')}")
                
                # 支撑压力
                sr = sig_data.get('support_resistance', {})
                st.write(f"📍 **支撑压力**: {sr.get('description', '计算中')}")
                
                # 量价口诀
                vp = sig_data.get('volume_price', {})
                if vp.get('mnemonic'):
                    st.write(f"📖 **量价口诀**: {vp['mnemonic']}")
            
            # 资金情绪
            st.markdown("---")
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                funding = sig_data.get('funding_rate', {})
                st.metric("资金费率", f"{funding.get('funding_rate', 0):.4f}%", delta=funding.get('status', '未知'))
            
            with col_f2:
                oi = sig_data.get('open_interest', {})
                st.metric("持仓量", f"{oi.get('open_interest', 0):.0f}")
            
            with col_f3:
                st.metric("综合评分", f"多{advanced_signals['bullish_score']:.0f} / 空{advanced_signals['bearish_score']:.0f}")
            
            # ========== 进场交易计划 ==========
            if rec in ["做多", "做空"] and conf >= 50:
                st.markdown("---")
                st.markdown("### 📋 **进场交易计划**")
                
                sr = sig_data.get('support_resistance', {})
                nearest_support = sr.get('nearest_support')
                nearest_resistance = sr.get('nearest_resistance')
                
                # 计算关键价格
                entry_price = price
                if rec == "做多":
                    stop_loss = nearest_support[1] if nearest_support else price * 0.98
                    take_profit = nearest_resistance[1] if nearest_resistance else price * 1.02
                    risk_pct = (entry_price - stop_loss) / entry_price * 100
                    reward_pct = (take_profit - entry_price) / entry_price * 100
                else:
                    stop_loss = nearest_resistance[1] if nearest_resistance else price * 1.02
                    take_profit = nearest_support[1] if nearest_support else price * 0.98
                    risk_pct = (stop_loss - entry_price) / entry_price * 100
                    reward_pct = (entry_price - take_profit) / entry_price * 100
                
                # 盈亏比
                risk_reward = reward_pct / risk_pct if risk_pct > 0 else 0
                
                # 仓位建议（基于风险1-2%）
                suggested_position = min(2.0 / risk_pct, 50) if risk_pct > 0 else 10
                
                # 显示交易计划
                plan_col1, plan_col2, plan_col3 = st.columns(3)
                
                with plan_col1:
                    st.markdown(f"""
                    **🎯 入场信息**
                    - 方向: `{'🟢 做多' if rec == '做多' else '🔴 做空'}`
                    - 入场价: `${entry_price:.2f}`
                    - 置信度: `{conf:.0f}%`
                    - 信号强度: `{'强' if conf >= 80 else '中' if conf >= 60 else '弱'}`
                    """)
                
                with plan_col2:
                    st.markdown(f"""
                    **🛡️ 风险控制**
                    - 止损价: `${stop_loss:.2f}`
                    - 风险: `{risk_pct:.2f}%`
                    - 止盈价: `${take_profit:.2f}`
                    - 目标: `{reward_pct:.2f}%`
                    """)
                
                with plan_col3:
                    st.markdown(f"""
                    **💰 仓位建议**
                    - 盈亏比: `1:{risk_reward:.1f}`
                    - 建议仓位: `{suggested_position:.1f}%`
                    - 半仓止盈: `${entry_price + (take_profit - entry_price) * 0.5 if rec == '做多' else entry_price - (entry_price - take_profit) * 0.5:.2f}`
                    - 风险等级: `{'低' if risk_pct < 1 else '中' if risk_pct < 2 else '高'}`
                    """)
                
                # 交易提示
                if conf >= 70 and risk_reward >= 2:
                    st.success(f"✅ **交易建议**: 置信度高+盈亏比优，建议按计划执行")
                    speak_alert(f"{rec}信号，入场价{entry_price:.0f}，止损{stop_loss:.0f}，止盈{take_profit:.0f}，盈亏比1比{risk_reward:.1f}")
                elif conf >= 60:
                    st.warning(f"⚠️ **交易建议**: 置信度中等，建议轻仓试探")
                else:
                    st.info(f"ℹ️ **交易建议**: 置信度较低，建议观望等待确认")
                
                # 语音播报交易计划
                try:
                    speak_alert(f"{rec}交易计划已生成，入场{entry_price:.0f}，止损{stop_loss:.0f}，止盈{take_profit:.0f}")
                except:
                    pass
        else:
            st.info("等待高级信号分析...")
    
    # === 🧠 AI审计中心（右侧）===
    with col_ai:
        st.subheader("🧠 AI 审计中心")
        
        # 显示基础信号
        if signals:
            st.write("**当前触发信号**:")
            st.write(", ".join([f"`{s}`" for s in signals]))
        else:
            st.write("**当前触发信号**: 无明确信号")
        
        # 显示高级信号摘要
        if advanced_signals:
            st.markdown("---")
            st.markdown(f"**综合评分**:")
            st.write(f"- 做多得分: `{advanced_signals['bullish_score']:.0f}`")
            st.write(f"- 做空得分: `{advanced_signals['bearish_score']:.0f}`")
        
        st.markdown("---")
        
        # AI分析
        with st.spinner("🕵️ AI深度分析中..."):
            if ADVANCED_SIGNALS_AVAILABLE and advanced_signals:
                prompt = generate_ai_prompt_v2(df, advanced_signals)
            else:
                prompt = f"分析ETHUSDT: 价格{price:.2f}, 量比{vol_ratio:.2f}, 盘口{imbalance:.2f}。给出简要操作建议（100字内）。"
            
            ai_report = get_ai_analysis(prompt)
            
            if "AI服务未启动" in ai_report:
                st.warning(ai_report)
                st.info("💡 备用建议：关注 EMA21 支撑，结合量能操作")
                if advanced_signals:
                    st.info(f"📊 **智能建议**: {advanced_signals['summary']}")
            else:
                st.markdown(ai_report)
                
                # ========== 语音播报 ==========
                if ADVANCED_SIGNALS_AVAILABLE and advanced_signals:
                    rec = advanced_signals['recommendation']
                    sig_data = advanced_signals.get('signals', {})
                    
                    # 高置信度信号播报
                    if rec in ["做多", "做空"] and advanced_signals['confidence'] >= 70:
                        speak_alert(f"{rec}信号确认，置信度{advanced_signals['confidence']:.0f}%")
                    
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
                    if acc.get('signal') and acc.get('strength', 0) >= 60:
                        speak_alert(f"主力吸筹信号，{acc.get('description', '关注做多机会')}")
                    
                    # 爆仓监控播报
                    liq = sig_data.get('liquidations', {})
                    if liq.get('total_large_trades', 0) > 5:
                        speak_alert(f"大额交易激增，多{liq.get('long_liquidations', 0)}空{liq.get('short_liquidations', 0)}")


if __name__ == "__main__":
    main()
