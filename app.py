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
    st_autorefresh(interval=5000, key="main_refresh")
    
    # 标题 + 时间
    c_title, c_time = st.columns([4, 1])
    with c_title:
        st.title("🚀 ETHUSDT 量化巡航系统 V2.0")
    with c_time:
        st.markdown(f"### ⏰ {datetime.datetime.now().strftime('%H:%M:%S')}")
    
    client = get_client()
    
    # 连接状态
    if 'connection_tested' not in st.session_state:
        results = client.test_all_connections()
        st.session_state['connection_tested'] = True
        st.session_state['connection_results'] = results
    
    # 侧边栏（精简）
    with st.sidebar:
        if 'connection_results' in st.session_state:
            results = st.session_state['connection_results']
            available = sum(1 for r in results.values() if r['status'])
            st.metric("🌐 节点", f"{available}/{len(results)}")
            with st.expander("详情"):
                for name, info in results.items():
                    icon = "✅" if info['status'] else "❌"
                    st.write(f"{icon} {name}")
        if st.button("🔄 重测"):
            st.session_state['connection_results'] = client.test_all_connections()
            st.rerun()
    
    # 获取数据
    with st.spinner("📡 获取数据..."):
        df, imbalance, walls, status_msg = get_market_data()
    
    if df.empty or df is None:
        st.error("❌ 连接失败")
        st.stop()
    
    last = df.iloc[-1]
    price = last['close']
    vol_ratio = last.get('vol_ratio', 1.0)
    
    # 高级信号分析
    advanced_signals = None
    if ADVANCED_SIGNALS_AVAILABLE and len(df) >= 50:
        try:
            df_hash = hash(df.to_json())
            advanced_signals = get_advanced_signals_cached(df_hash, df, imbalance, walls)
            if 'df' in advanced_signals:
                df = advanced_signals['df']
        except:
            pass
    
    # ========== K线图 ==========
    trade_signals = []
    rec, conf = "", 0
    sig_data = {}
    
    if advanced_signals and advanced_signals.get('confidence', 0) >= 50:
        rec = advanced_signals['recommendation']
        conf = advanced_signals['confidence']
        sig_data = advanced_signals.get('signals', {})
        
        if rec in ['做多', '做空']:
            sr = sig_data.get('support_resistance', {})
            ns = sr.get('nearest_support')
            nr = sr.get('nearest_resistance')
            
            sl = ns[1] if ns else price * 0.98
            tp = nr[1] if nr else price * 1.02
            if rec == '做空':
                sl = nr[1] if nr else price * 1.02
                tp = ns[1] if ns else price * 0.98
            
            trade_signals.append({
                'direction': 'LONG' if rec == '做多' else 'SHORT',
                'index': len(df) - 1,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence_level': 'HIGH' if conf >= 80 else 'MID'
            })
    
    fig = plot_enhanced_candlestick(df, advanced_signals, trade_signals)
    st.plotly_chart(fig, use_container_width=True)
    
    # ========== 核心指标行（6列）==========
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("💰 价格", f"${price:.2f}")
    with m2:
        delta_v = "放量" if vol_ratio > 1.5 else "缩量" if vol_ratio < 0.7 else ""
        st.metric("📊 量比", f"{vol_ratio:.2f}", delta=delta_v)
    with m3:
        imb_s = calculate_order_imbalance(100*(1+imbalance), 100*(1-imbalance)).get('status', '')
        st.metric("⚖️ 盘口", f"{imbalance:.2f}", delta=imb_s)
    with m4:
        atr = df['atr_pct'].iloc[-1] if 'atr_pct' in df.columns else 0
        st.metric("📈 波动", f"{atr:.2f}%")
    with m5:
        funding = sig_data.get('funding_rate', {})
        st.metric("💵 费率", f"{funding.get('funding_rate', 0):.4f}%")
    with m6:
        oi = sig_data.get('open_interest', {})
        st.metric("📦 持仓", f"{oi.get('open_interest', 0):.0f}")
    
    # ========== 核心区域 ==========
    st.markdown("---")
    col_left, col_right = st.columns([1, 1])
    
    # === 左侧：信号 + 交易计划 ===
    with col_left:
        if advanced_signals and 'signals' in advanced_signals:
            # 综合建议（醒目显示）
            if rec == "做多":
                st.success(f"🟢 **{rec}** | 置信度 {conf:.0f}%")
            elif rec == "做空":
                st.error(f"🔴 **{rec}** | 置信度 {conf:.0f}%")
            else:
                st.info(f"⚪ **{rec}** | 置信度 {conf:.0f}%")
            
            # 核心信息（一行）
            ms = sig_data.get('market_state', {})
            lstm = sig_data.get('lstm_prediction', {})
            st.write(f"🏛️ 市场: **{ms.get('state', '-')}** | 🤖 AI: **{lstm.get('trend', '-')}** ({lstm.get('probability', 0):.0f}%)")
            
            # 评分
            st.metric("📊 评分", f"多{advanced_signals['bullish_score']:.0f} / 空{advanced_signals['bearish_score']:.0f}")
            
            # 关键信号提醒（如有）
            alerts = []
            if sig_data.get('accumulation', {}).get('signal'):
                alerts.append("🔍主力吸筹")
            if sig_data.get('whale_pump', {}).get('signal'):
                alerts.append("🐋巨鲸拉升")
            if sig_data.get('crash_warning', {}).get('signal'):
                alerts.append("⚠️急跌风险")
            if sig_data.get('fake_breakout', {}).get('signal'):
                alerts.append("🎭假突破")
            if alerts:
                st.warning(" | ".join(alerts))
            
            # 支撑压力
            sr = sig_data.get('support_resistance', {})
            st.write(f"📍 {sr.get('description', '计算中')}")
            
            # 交易计划
            if rec in ["做多", "做空"] and conf >= 50:
                st.markdown("---")
                st.markdown("### 📋 交易计划")
                
                ns = sr.get('nearest_support')
                nr = sr.get('nearest_resistance')
                
                if rec == "做多":
                    sl = ns[1] if ns else price * 0.98
                    tp = nr[1] if nr else price * 1.02
                else:
                    sl = nr[1] if nr else price * 1.02
                    tp = ns[1] if ns else price * 0.98
                
                risk = abs(price - sl) / price * 100
                reward = abs(tp - price) / price * 100
                rr = reward / risk if risk > 0 else 0
                
                p1, p2, p3 = st.columns(3)
                p1.metric("🎯 入场", f"${price:.2f}")
                p2.metric("🛡️ 止损", f"${sl:.2f}", f"-{risk:.1f}%")
                p3.metric("💎 止盈", f"${tp:.2f}", f"+{reward:.1f}%")
                
                st.info(f"💰 盈亏比 **1:{rr:.1f}** | 建议仓位 **{min(2/risk, 50):.0f}%**")
                
                # 语音播报
                if conf >= 70:
                    try:
                        speak_alert(f"{rec}信号，置信度{conf:.0f}%，止损{sl:.0f}，止盈{tp:.0f}", "trade")
                    except:
                        pass
        else:
            st.info("等待信号分析...")
    
    # === 右侧：AI分析 ===
    with col_right:
        st.subheader("🧠 AI 分析")
        
        with st.spinner("分析中..."):
            if ADVANCED_SIGNALS_AVAILABLE and advanced_signals:
                prompt = generate_ai_prompt_v2(df, advanced_signals)
            else:
                prompt = f"分析ETHUSDT: 价格{price:.2f}, 量比{vol_ratio:.2f}。简要建议。"
            
            ai_report = get_ai_analysis(prompt)
            
            if "AI服务未启动" in ai_report:
                st.warning("AI服务离线")
                if advanced_signals:
                    st.info(advanced_signals.get('summary', '等待分析...'))
            else:
                st.markdown(ai_report)


if __name__ == "__main__":
    main()
