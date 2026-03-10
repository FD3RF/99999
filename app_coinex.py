import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
import datetime
import hashlib
import hmac
import numpy as np
from streamlit_autorefresh import st_autorefresh
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 语音播报仅在Windows环境可用
TTS_AVAILABLE = False
if not st.secrets.get("CLOUD_DEPLOYMENT", False):
    try:
        import pyttsx3
        TTS_AVAILABLE = True
    except:
        TTS_AVAILABLE = False

# ========== 1. 页面配置 ==========
st.set_page_config(
    page_title="ETHUSDT 企业级量化系统", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ========== 2. CoinEx 客户端 ==========
class CoinExClient:
    """CoinEx 专业客户端"""
    
    BASE_URL = "https://api.coinex.com"
    
    def __init__(self, access_id: str, secret_key: str):
        self.access_id = access_id
        self.secret_key = secret_key
        self.session = requests.Session()
        
        # 配置重试
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
    
    def _sign(self, params: dict) -> str:
        """生成签名"""
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """发送请求"""
        url = f"{self.BASE_URL}{endpoint}"
        
        # 公共接口无需签名
        public_endpoints = ["/v1/common/market/tickers", "/v1/market/kline", "/v1/market/depth"]
        
        if endpoint in public_endpoints or not params:
            # 公共接口
            try:
                if method == "GET":
                    resp = self.session.get(url, params=params, timeout=10)
                else:
                    resp = self.session.post(url, json=params, timeout=10)
                
                resp.raise_for_status()
                data = resp.json()
                
                if data.get('code') == 0:
                    return data.get('data', {})
                else:
                    print(f"API Error: {data.get('message', 'Unknown error')}")
                    return None
            except Exception as e:
                print(f"Request failed: {e}")
                return None
        else:
            # 私有接口（需要签名）
            params['access_id'] = self.access_id
            params['tonce'] = int(time.time() * 1000)
            params['signature'] = self._sign(params)
            
            try:
                if method == "GET":
                    resp = self.session.get(url, params=params, timeout=10)
                else:
                    resp = self.session.post(url, json=params, timeout=10)
                
                resp.raise_for_status()
                data = resp.json()
                
                if data.get('code') == 0:
                    return data.get('data', {})
                else:
                    return None
            except Exception as e:
                print(f"Request failed: {e}")
                return None

# ========== 3. 初始化客户端 ==========
@st.cache_resource
def get_client():
    """获取客户端实例"""
    access_id = "ck_ffiiw9tghpmo"
    secret_key = "ERhm1msKAewD2Xheg0tcLsvOsOIwV9Kma7ShFuOludA"
    return CoinExClient(access_id, secret_key)

# ========== 4. K线数据获取 (优化版) ==========
@st.cache_data(ttl=5, max_entries=10, show_spinner="正在加载K线数据...")
def get_kline_cached(symbol: str, interval: str = "5min", limit: int = 200) -> pd.DataFrame:
    """
    获取并缓存K线数据 (企业级优化版)
    
    Args:
        symbol: 交易对 (如 'ETHUSDT')
        interval: K线周期 (1min, 5min, 1hour等)
        limit: 获取数量
    
    Returns:
        pd.DataFrame: 包含 OHLCV 数据的 DataFrame
    """
    if not symbol:
        return pd.DataFrame()
    
    client = get_client()
    
    try:
        # CoinEx K线接口
        endpoint = "/v1/market/kline"
        params = {
            "market": symbol.upper(),
            "type": interval,
            "limit": limit
        }
        
        raw_data = client.request("GET", endpoint, params)
        
        if not raw_data:
            return pd.DataFrame()
        
        # CoinEx 返回格式: [时间, 开, 收, 高, 低, 成交量, 成交额]
        df = pd.DataFrame(raw_data, columns=["time", "open", "close", "high", "low", "volume", "amount"])
        
        # 类型转换（向量化操作）
        numeric_cols = ["open", "high", "low", "close", "volume", "amount"]
        df[numeric_cols] = df[numeric_cols].astype(float)
        
        # 重新排列列顺序为标准格式
        df = df[["time", "open", "high", "low", "close", "volume"]]
        
        # 时间处理
        df["time"] = pd.to_datetime(df["time"], unit="s")
        
        # 计算技术指标
        df["ma20"] = df["close"].rolling(20).mean()
        df["ma50"] = df["close"].rolling(50).mean()
        df["vol_ma"] = df["volume"].rolling(20).mean()
        df["vol_ratio"] = df["volume"] / df["vol_ma"]
        
        return df
        
    except Exception as e:
        st.error(f"K线获取失败: {str(e)}")
        return pd.DataFrame()

# ========== 5. 订单簿分析 (优化版) ==========
@st.cache_data(ttl=2, max_entries=5, show_spinner=False)
def get_orderbook_analysis(symbol: str, limit: int = 20, wall_multiplier: float = 3.0) -> dict:
    """
    获取订单簿深度并分析买卖力量 (逻辑解耦版)
    
    Args:
        symbol: 交易对
        limit: 深度档位
        wall_multiplier: 识别"大单墙"的倍数阈值
    
    Returns:
        Dict: 包含失衡度、状态描述、关键价位的字典
    """
    empty_result = {
        "imbalance": 0.0, 
        "status": "NO_DATA", 
        "description": "数据不足", 
        "walls": {}, 
        "bid_vol": 0.0, 
        "ask_vol": 0.0
    }
    
    if not symbol:
        return empty_result
    
    client = get_client()
    
    try:
        endpoint = "/v1/market/depth"
        params = {
            "market": symbol.upper(),
            "limit": limit,
            "merge": 0
        }
        
        data = client.request("GET", endpoint, params)
        
        if not data:
            return empty_result
        
        # CoinEx 返回格式
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        
        if not bids or not asks:
            return empty_result
        
        # 核心指标计算
        bid_vol = sum(float(b[1]) for b in bids)
        ask_vol = sum(float(a[1]) for a in asks)
        total_vol = bid_vol + ask_vol
        
        # 防止除零错误
        imbalance = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0.0
        
        # 智能状态判断
        if bid_vol > ask_vol * 1.5:
            status = "BULLISH"
            desc_suffix = "🔥 买盘强劲"
        elif ask_vol > bid_vol * 1.5:
            status = "BEARISH"
            desc_suffix = "📉 卖压沉重"
        else:
            status = "NEUTRAL"
            desc_suffix = "⚖️ 多空均衡"
        
        description = f"买:{bid_vol:.1f} vs 卖:{ask_vol:.1f} {desc_suffix}"
        
        # 大单墙识别
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
            "description": description,
            "walls": walls,
            "bid_vol": round(bid_vol, 4),
            "ask_vol": round(ask_vol, 4)
        }
        
    except Exception as e:
        return {**empty_result, "description": f"获取失败: {str(e)}", "status": "ERROR"}

# ========== 6. 支撑阻力计算 ==========
def calculate_support_resistance(df):
    """计算支撑位和阻力位"""
    try:
        if len(df) < 5:
            return {"support": "数据不足", "resistance": "数据不足"}
        
        # 计算最近的高点和低点
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()
        
        # 计算支撑位（最近的低点）
        support = recent_low
        
        # 计算阻力位（最近的高点）
        resistance = recent_high
        
        # 计算当前价格相对于支撑阻力的位置
        current_price = df['close'].iloc[-1]
        
        # 判断支撑阻力强度
        support_strength = "强" if current_price - support > (resistance - support) * 0.3 else "弱"
        resistance_strength = "强" if resistance - current_price > (resistance - support) * 0.3 else "弱"
        
        return {
            "support": f"{support:.2f} ({support_strength})",
            "resistance": f"{resistance:.2f} ({resistance_strength})",
            "current": current_price
        }
    except Exception as e:
        return {"support": "计算错误", "resistance": "计算错误", "current": 0}

# ========== 7. 语音播报 ==========
def voice_alert(message):
    """语音播报提醒"""
    if TTS_AVAILABLE and not st.secrets.get("CLOUD_DEPLOYMENT", False):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(message)
            engine.runAndWait()
            return True
        except:
            return False
    return False

# ========== 8. AI 分析 (快速版) ==========
def get_ai_analysis_fast(prompt: str) -> str:
    """快速 AI 分析 - 使用 1.5B 模型"""
    try:
        # 尝试使用在线 DeepSeek API
        api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
        
        if api_key:
            # 使用 DeepSeek API
            import openai
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150
            )
            
            return response.choices[0].message.content
        else:
            # 尝试本地 Ollama
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "deepseek-r1:1.5b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 100
                    }
                },
                timeout=30
            )
            
            if resp.status_code == 200:
                return resp.json().get("response", "AI响应为空")
            else:
                return "⚠️ AI服务未配置\n\n请在 .streamlit/secrets.toml 中添加：\nDEEPSEEK_API_KEY = \"your_key\""
                
    except requests.exceptions.ConnectionError:
        return "⚠️ AI服务未启动\n\n解决方案：\n1. 配置 DeepSeek API Key（推荐）\n2. 或运行: ollama serve"
    except Exception as e:
        return f"⚠️ AI分析失败: {str(e)}"

# ========== 7. 主程序 ==========
def main():
    st_autorefresh(interval=10000, key="main_refresh")
    
    st.title("🚀 ETHUSDT 企业级量化系统")
    
    SYMBOL = "ETHUSDT"
    
    # 侧边栏
    with st.sidebar:
        st.markdown("### ⚙️ 系统配置")
        
        # AI 模型选择
        ai_mode = st.radio("AI 模式", ["快速 (1.5B)", "详细 (7B)"])
        
        # 连接测试
        if st.button("🔍 测试连接"):
            with st.spinner("测试中..."):
                try:
                    client = get_client()
                    data = client.request("GET", "/v1/common/market/tickers", {"limit": 1})
                    if data:
                        st.success("✅ CoinEx 连接正常")
                    else:
                        st.error("❌ 连接失败")
                except Exception as e:
                    st.error(f"❌ 错误: {str(e)}")
    
    st.markdown(f"**系统时间**: {datetime.datetime.now().strftime('%H:%M:%S')} | **数据源**: CoinEx")
    
    # 1. 获取K线数据
    with st.spinner("📊 加载K线数据..."):
        df = get_kline_cached(SYMBOL, "5min", 200)
    
    if df.empty:
        st.error("❌ K线数据获取失败")
        st.stop()
    
    # 2. 获取订单簿分析
    ob_data = get_orderbook_analysis(SYMBOL, 20)
    
    # 3. 计算支撑阻力
    support_resistance = calculate_support_resistance(df)
    
    # 4. 计算状态
    last = df.iloc[-1]
    price = last['close']
    vol_ratio = last['vol_ratio']
    trend = "上涨" if last['ma20'] > last['ma50'] else "下跌"
    
    # 信号生成
    signals = []
    if last['close'] > last['ma20']: signals.append("价格站上MA20")
    if vol_ratio > 2.0: signals.append(f"巨量异动({vol_ratio:.1f}倍)")
    if ob_data['imbalance'] > 0.4: signals.append("买盘压倒")
    elif ob_data['imbalance'] < -0.4: signals.append("卖盘压倒")
    
    # 共振判断
    resonance = "无共振"
    if trend == "上涨" and ob_data['imbalance'] > 0.3: resonance = "多头共振"
    elif trend == "下跌" and ob_data['imbalance'] < -0.3: resonance = "空头共振"
    
    # 4. 页面布局
    col_chart, col_ai = st.columns([1.5, 1])
    
    with col_chart:
        st.subheader("📈 实时行情 (5min)")
        
        # K线图
        fig = go.Figure()
        # K线图（绿色上涨，红色下跌 - 国际标准）
        fig.add_trace(go.Candlestick(
            x=df['time'], open=df['open'], high=df['high'], 
            low=df['low'], close=df['close'], name='K线',
            increasing_line_color='green',    # 涨 - 绿色
            decreasing_line_color='red',     # 跌 - 红色
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
        walls = ob_data.get('walls', {})
        if 'support' in walls:
            fig.add_hline(y=walls['support'], line_dash="dash", line_color="green", 
                          annotation_text="支撑", annotation_position="right")
        if 'resistance' in walls:
            fig.add_hline(y=walls['resistance'], line_dash="dash", line_color="red", 
                          annotation_text="压力", annotation_position="right")
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        # 指标卡片
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("当前价格", f"{price:.2f}", f"{df['close'].iloc[-1] - df['close'].iloc[-2]:.2f}")
        c2.metric("量比", f"{vol_ratio:.2f}", delta="放量" if vol_ratio > 1.5 else "缩量")
        c3.metric("盘口失衡", f"{ob_data['imbalance']:.2f}", 
                  delta="多头优势" if ob_data['imbalance'] > 0.1 else "空头优势")
        c4.metric("市场情绪", ob_data['status'], ob_data['description'].split()[-1])
        
        # 支撑阻力卡片
        c5, c6 = st.columns(2)
        c5.metric("支撑位", support_resistance["support"])
        c6.metric("阻力位", support_resistance["resistance"])
        
        st.info(f"**盘口详情**: {ob_data['description']}")
        
        # 语音播报（仅在有重大变化时）
        if len(signals) > 0 and abs(ob_data['imbalance']) > 0.3:
            alert_message = f"ETHUSDT 价格 {price:.2f}，{signals[0]}"
            if voice_alert(alert_message):
                st.success("🔊 语音播报已发送")
            else:
                st.info("💡 语音播报不可用（需要安装 pyttsx3）")

    with col_ai:
        st.subheader("🧠 AI 审计中心")
        
        if signals:
            st.write("**触发信号**:")
            st.write(", ".join([f"`{s}`" for s in signals]))
        else:
            st.write("**触发信号**: 无")
        
        st.markdown("---")
        
        # AI 分析
        model = "deepseek-r1:1.5b" if "快速" in ai_mode else "deepseek-r1:7b"
        timeout = 30 if "快速" in ai_mode else 120
        
        with st.spinner(f"🕵️ {model} 分析中..."):
            # 简化提示词
            prompt = f"""分析 ETHUSDT:
价格:{price:.0f} 趋势:{trend} 量比:{vol_ratio:.1f} 盘口:{ob_data['imbalance']:.2f}
信号:{','.join(signals[:3])} 共振:{resonance}
支撑:{walls.get('support','无')} 压力:{walls.get('resistance','无')}

简要给出:
1. 判断(吸筹/派发/震荡)
2. 操作建议
3. 风险(高/中/低)

限制100字内。"""
            
            try:
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 100 if "快速" in ai_mode else 200}
                    },
                    timeout=timeout
                )
                
                if resp.status_code == 200:
                    ai_report = resp.json().get("response", "")
                    if ai_report:
                        st.markdown(ai_report)
                        st.caption(f"_模型: {model}_")
                    else:
                        st.warning("AI返回空响应")
                else:
                    st.error(f"AI服务错误: HTTP {resp.status_code}")
                    
            except requests.exceptions.Timeout:
                st.error(f"⏱️ AI响应超时 ({timeout}秒)")
                st.info("💡 建议:\n- 使用快速模式\n- 或启动 GPU 加速")
            except requests.exceptions.ConnectionError:
                st.error("❌ AI服务未启动")
                st.code("ollama serve", language="bash")
            except Exception as e:
                st.error(f"AI分析失败: {str(e)}")

if __name__ == "__main__":
    main()
