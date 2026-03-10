import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
import datetime
import hashlib
import hmac
import random
from streamlit_autorefresh import st_autorefresh
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ========== 1. 页面配置 ==========
st.set_page_config(
    page_title="ETHUSDT 多节点企业级系统", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ========== 2. 多 API Key 管理 ==========
API_KEYS = [
    {
        "name": "API-1",
        "access_id": "ck_ffiiw9tghpmo",
        "secret_key": "ERhm1msKAewD2Xheg0tcLsvOsOIwV9Kma7ShFuOludA",
        "status": True,
        "priority": 1
    },
    {
        "name": "API-2",
        "access_id": "edb9c21086f141168d1a0fc3f5ff9422",
        "secret_key": "1GthyFAyFFvojDqN",
        "status": True,
        "priority": 2
    }
]

# ========== 3. CoinEx 客户端（支持负载均衡）==========
class CoinExClientLB:
    """CoinEx 客户端 - 支持多 API Key 负载均衡"""
    
    BASE_URL = "https://api.coinex.com"
    
    def __init__(self, api_keys: list):
        self.api_keys = api_keys
        self.current_index = 0
        self.session = requests.Session()
        
        # 配置重试
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        
        # 统计数据
        self.stats = {key['name']: {"requests": 0, "errors": 0} for key in api_keys}
    
    def _get_api_key(self):
        """获取下一个可用的 API Key（轮询负载均衡）"""
        # 优先使用优先级高的
        available_keys = [k for k in self.api_keys if k['status']]
        if not available_keys:
            raise Exception("无可用 API Key")
        
        # 按优先级排序
        available_keys.sort(key=lambda x: x['priority'])
        
        # 轮询选择
        api_key = available_keys[self.current_index % len(available_keys)]
        self.current_index += 1
        
        return api_key
    
    def _sign(self, params: dict, secret_key: str) -> str:
        """生成签名"""
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        signature = hmac.new(
            secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """发送请求（带负载均衡和故障转移）"""
        # 尝试所有 API Key
        for attempt in range(len(self.api_keys)):
            api_key = self._get_api_key()
            
            try:
                url = f"{self.BASE_URL}{endpoint}"
                
                # 公共接口
                public_endpoints = ["/v1/common/market/tickers", "/v1/market/kline", "/v1/market/depth"]
                
                if endpoint in public_endpoints or not params:
                    resp = self.session.get(url, params=params, timeout=10)
                else:
                    # 私有接口
                    params['access_id'] = api_key['access_id']
                    params['tonce'] = int(time.time() * 1000)
                    params['signature'] = self._sign(params, api_key['secret_key'])
                    resp = self.session.get(url, params=params, timeout=10) if method == "GET" else \
                           self.session.post(url, json=params, timeout=10)
                
                resp.raise_for_status()
                data = resp.json()
                
                # 更新统计
                self.stats[api_key['name']]["requests"] += 1
                
                if data.get('code') == 0:
                    return data.get('data', {})
                else:
                    # API 错误，尝试下一个
                    continue
                    
            except Exception as e:
                # 标记此 API Key 为不可用
                api_key['status'] = False
                self.stats[api_key['name']]["errors"] += 1
                print(f"{api_key['name']} 失败: {e}")
                continue
        
        # 所有 API Key 都失败
        raise Exception("所有 API Key 均不可用")

# ========== 4. 初始化客户端 ==========
@st.cache_resource
def get_client():
    """获取客户端实例"""
    return CoinExClientLB(API_KEYS)

# ========== 5. K线数据获取 ==========
@st.cache_data(ttl=5, max_entries=10, show_spinner="加载中...")
def get_kline_cached(symbol: str, interval: str = "5min", limit: int = 200) -> pd.DataFrame:
    """获取K线数据（企业级优化版）"""
    if not symbol:
        return pd.DataFrame()
    
    client = get_client()
    
    try:
        endpoint = "/v1/market/kline"
        params = {
            "market": symbol.upper(),
            "type": interval,
            "limit": limit
        }
        
        raw_data = client.request("GET", endpoint, params)
        
        if not raw_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(raw_data, columns=["time", "open", "high", "low", "close", "volume"])
        numeric_cols = ["open", "high", "low", "close", "volume"]
        df[numeric_cols] = df[numeric_cols].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        
        # 计算指标
        df["ma20"] = df["close"].rolling(20).mean()
        df["ma50"] = df["close"].rolling(50).mean()
        df["vol_ma"] = df["volume"].rolling(20).mean()
        df["vol_ratio"] = df["volume"] / df["vol_ma"]
        
        return df
        
    except Exception as e:
        st.error(f"K线获取失败: {str(e)}")
        return pd.DataFrame()

# ========== 6. 订单簿分析 ==========
@st.cache_data(ttl=2, max_entries=5, show_spinner=False)
def get_orderbook_analysis(symbol: str, limit: int = 20, wall_multiplier: float = 3.0) -> dict:
    """获取订单簿分析"""
    empty_result = {
        "imbalance": 0.0, "status": "NO_DATA", "description": "数据不足",
        "walls": {}, "bid_vol": 0.0, "ask_vol": 0.0
    }
    
    if not symbol:
        return empty_result
    
    client = get_client()
    
    try:
        endpoint = "/v1/market/depth"
        params = {"market": symbol.upper(), "limit": limit, "merge": 0}
        
        data = client.request("GET", endpoint, params)
        
        if not data:
            return empty_result
        
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        
        if not bids or not asks:
            return empty_result
        
        bid_vol = sum(float(b[1]) for b in bids)
        ask_vol = sum(float(a[1]) for a in asks)
        total_vol = bid_vol + ask_vol
        imbalance = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0.0
        
        # 状态判断
        if bid_vol > ask_vol * 1.5:
            status, desc_suffix = "BULLISH", "🔥 买盘强劲"
        elif ask_vol > bid_vol * 1.5:
            status, desc_suffix = "BEARISH", "📉 卖压沉重"
        else:
            status, desc_suffix = "NEUTRAL", "⚖️ 多空均衡"
        
        # 大单墙
        walls = {}
        if bids:
            avg_bid = bid_vol / len(bids)
            for price, qty in bids:
                if float(qty) > avg_bid * wall_multiplier:
                    walls['support'] = float(price)
                    break
        if asks:
            avg_ask = ask_vol / len(asks)
            for price, qty in asks:
                if float(qty) > avg_ask * wall_multiplier:
                    walls['resistance'] = float(price)
                    break
        
        return {
            "imbalance": round(imbalance, 4),
            "status": status,
            "description": f"买:{bid_vol:.1f} vs 卖:{ask_vol:.1f} {desc_suffix}",
            "walls": walls,
            "bid_vol": round(bid_vol, 4),
            "ask_vol": round(ask_vol, 4)
        }
        
    except Exception as e:
        return {**empty_result, "description": f"获取失败: {str(e)}", "status": "ERROR"}

# ========== 7. AI 分析 ==========
def get_ai_analysis_fast(prompt: str) -> str:
    """快速 AI 分析"""
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:1.5b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 100}
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            return resp.json().get("response", "AI响应为空")
        return "AI服务错误"
        
    except requests.exceptions.Timeout:
        return "⏱️ AI响应超时（建议使用快速模式）"
    except requests.exceptions.ConnectionError:
        return "❌ AI服务未启动\n\n启动: `ollama serve`"
    except Exception as e:
        return f"AI分析失败: {str(e)}"

# ========== 8. 主程序 ==========
def main():
    st_autorefresh(interval=10000, key="main_refresh")
    
    st.title("🚀 ETHUSDT 多节点企业级系统")
    
    SYMBOL = "ETHUSDT"
    
    # 侧边栏
    with st.sidebar:
        st.markdown("### ⚙️ 系统状态")
        
        # API Key 状态
        client = get_client()
        st.markdown("**API Key 状态:**")
        for api_key in API_KEYS:
            status_icon = "✅" if api_key['status'] else "❌"
            st.write(f"{status_icon} {api_key['name']}")
        
        # 统计信息
        with st.expander("📊 使用统计"):
            for name, stats in client.stats.items():
                st.write(f"{name}: {stats['requests']} 请求, {stats['errors']} 错误")
        
        # 刷新状态
        if st.button("🔄 重置状态"):
            for key in API_KEYS:
                key['status'] = True
            st.rerun()
    
    st.markdown(f"**系统时间**: {datetime.datetime.now().strftime('%H:%M:%S')} | **数据源**: CoinEx (负载均衡)")
    
    # 获取数据
    with st.spinner("📊 加载数据..."):
        df = get_kline_cached(SYMBOL, "5min", 200)
    
    if df.empty:
        st.error("❌ 数据获取失败")
        st.stop()
    
    ob_data = get_orderbook_analysis(SYMBOL, 20)
    
    # 计算状态
    last = df.iloc[-1]
    price = last['close']
    vol_ratio = last['vol_ratio']
    trend = "上涨" if last['ma20'] > last['ma50'] else "下跌"
    
    # 信号
    signals = []
    if last['close'] > last['ma20']: signals.append("价格站上MA20")
    if vol_ratio > 2.0: signals.append(f"巨量异动({vol_ratio:.1f}倍)")
    if ob_data['imbalance'] > 0.4: signals.append("买盘压倒")
    elif ob_data['imbalance'] < -0.4: signals.append("卖盘压倒")
    
    resonance = "多头共振" if trend == "上涨" and ob_data['imbalance'] > 0.3 else \
                "空头共振" if trend == "下跌" and ob_data['imbalance'] < -0.3 else "无共振"
    
    # 布局
    col_chart, col_ai = st.columns([1.5, 1])
    
    with col_chart:
        st.subheader("📈 实时行情 (5min)")
        
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
        fig.add_trace(go.Scatter(x=df['time'], y=df['ma20'], line=dict(color='orange', width=1), name='MA20'))
        fig.add_trace(go.Scatter(x=df['time'], y=df['ma50'], line=dict(color='blue', width=1), name='MA50'))
        
        walls = ob_data.get('walls', {})
        if 'support' in walls:
            fig.add_hline(y=walls['support'], line_dash="dash", line_color="green", 
                          annotation_text="支撑", annotation_position="right")
        if 'resistance' in walls:
            fig.add_hline(y=walls['resistance'], line_dash="dash", line_color="red", 
                          annotation_text="压力", annotation_position="right")
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("当前价格", f"{price:.2f}", f"{df['close'].iloc[-1] - df['close'].iloc[-2]:.2f}")
        c2.metric("量比", f"{vol_ratio:.2f}", delta="放量" if vol_ratio > 1.5 else "缩量")
        c3.metric("盘口失衡", f"{ob_data['imbalance']:.2f}", 
                  delta="多头优势" if ob_data['imbalance'] > 0.1 else "空头优势")
        c4.metric("市场情绪", ob_data['status'], ob_data['description'].split()[-1])
        
        st.info(f"**盘口详情**: {ob_data['description']}")

    with col_ai:
        st.subheader("🧠 AI 审计中心")
        
        if signals:
            st.write("**触发信号**:")
            st.write(", ".join([f"`{s}`" for s in signals]))
        else:
            st.write("**触发信号**: 无")
        
        st.markdown("---")
        
        with st.spinner("🕵️ DeepSeek-R1 分析中..."):
            prompt = f"""分析 ETHUSDT:
价格:{price:.0f} 趋势:{trend} 量比:{vol_ratio:.1f} 盘口:{ob_data['imbalance']:.2f}
信号:{','.join(signals[:3])} 共振:{resonance}
支撑:{walls.get('support','无')} 压力:{walls.get('resistance','无')}

简要给出:
1. 判断(吸筹/派发/震荡)
2. 操作建议
3. 风险(高/中/低)

限制100字内。"""
            
            ai_report = get_ai_analysis_fast(prompt)
            st.markdown(ai_report)

if __name__ == "__main__":
    main()
