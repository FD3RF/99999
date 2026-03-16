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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 自动刷新
def auto_refresh(interval_ms=5000):
    import streamlit.components.v1 as components
    refresh_code = f"""
    <script>
    setTimeout(function() {{ window.location.reload(); }}, {interval_ms});
    </script>
    """
    components.html(refresh_code, height=0)

# 导入高级信号模块
try:
    from advanced_signals_v2 import (
        calculate_vwap, calculate_ema, calculate_cvd, calculate_atr,
        detect_market_state, calculate_support_resistance_v2, calculate_order_imbalance,
        detect_accumulation_v2, lstm_predict_v2, fake_breakout_v2, whale_pump_v2,
        crash_warning_v2, volume_price_mnemonics_v2, get_funding_rate, get_open_interest,
        get_liquidations, comprehensive_signal_analysis_v2, speak_alert
    )
    ADVANCED_SIGNALS_AVAILABLE = True
except ImportError as e:
    ADVANCED_SIGNALS_AVAILABLE = False
    print(f"高级信号模块未加载: {e}")
    
    def calculate_order_imbalance(bid_vol, ask_vol):
        total = bid_vol + ask_vol
        if total == 0: return {'imbalance': 0, 'status': '无数据'}
        imb = (bid_vol - ask_vol) / total
        status = "买盘优势" if imb > 0.3 else "卖盘优势" if imb < -0.3 else "平衡"
        return {'imbalance': imb, 'status': status}
    
    def speak_alert(text, alert_type="default"): pass

# 页面配置
st.set_page_config(page_title="ETHUSDT 量化巡航系统 V2.0", layout="wide", initial_sidebar_state="expanded")

# 深色主题
st.markdown("""
<style>
    .stApp { background-color: #0e1117 !important; color: #fafafa !important; }
    section[data-testid="stSidebar"] { background-color: #1a1a2e !important; }
    h1, h2, h3, h4, h5, h6 { color: #fafafa !important; }
    [data-testid="stMetric"] { background-color: #1e1e2e !important; border-radius: 10px; padding: 15px; border: 1px solid #2d2d3d; }
    [data-testid="stAlert"] { background-color: #1e1e2e !important; border: 1px solid #3d3d4d !important; }
    .stMarkdown p, .stMarkdown li { color: #e5e5e5 !important; }
</style>
""", unsafe_allow_html=True)

# 交易所客户端
class MultiExchangeClientV2:
    EXCHANGES = {
        "Binance": {"urls": ["https://api.binance.com"], "kline_endpoint": "/api/v3/klines", "depth_endpoint": "/api/v3/depth", "test_url": "/api/v3/ping"},
        "OKX": {"urls": ["https://www.okx.com"], "kline_endpoint": "/api/v5/market/candles", "depth_endpoint": "/api/v5/market/books", "test_url": "/api/v5/public/time"},
        "KuCoin": {"urls": ["https://api.kucoin.com"], "kline_endpoint": "/api/v1/market/candles", "depth_endpoint": "/api/v1/market/orderbook/level2_20", "test_url": "/api/v1/status"},
        "Gate.io": {"urls": ["https://api.gateio.ws"], "kline_endpoint": "/api/v4/spot/candlesticks", "depth_endpoint": "/api/v4/spot/order_book", "test_url": "/api/v4/ping"}
    }
    
    def __init__(self):
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.available_exchanges = {}
    
    def test_all_connections(self):
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
        all_prices, all_dfs, all_imbalances = [], [], []
        for exchange_name, config in self.EXCHANGES.items():
            if exchange_name not in self.available_exchanges: continue
            try:
                base_url = self.available_exchanges[exchange_name]
                kline_url = f"{base_url}{config['kline_endpoint']}"
                
                if exchange_name == "Binance":
                    params = {"symbol": "ETHUSDT", "interval": "5m", "limit": 200}
                    kline_resp = self.session.get(kline_url, params=params, timeout=10)
                    if kline_resp.status_code == 200:
                        data = kline_resp.json()
                        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'] + [f'x{i}' for i in range(6, 12)])
                        df = df[['time', 'open', 'high', 'low', 'close', 'volume']].astype(float)
                        df['time'] = pd.to_datetime(df['time'], unit='ms')
                        all_dfs.append((exchange_name, df))
                        all_prices.append(df['close'].iloc[-1])
                        all_imbalances.append(0)
                elif exchange_name == "OKX":
                    params = {"instId": "ETH-USDT", "bar": "5m", "limit": 200}
                    kline_resp = self.session.get(kline_url, params=params, timeout=10)
                    if kline_resp.status_code == 200:
                        data = kline_resp.json().get('data', [])
                        if data:
                            df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
                            df = df[['time', 'open', 'high', 'low', 'close', 'volume']].astype(float)
                            df['time'] = pd.to_datetime(df['time'], unit='ms')
                            df = df.iloc[::-1].reset_index(drop=True)
                            all_dfs.append((exchange_name, df))
                            all_prices.append(df['close'].iloc[-1])
                            all_imbalances.append(0)
            except Exception as e:
                continue
        
        if not all_dfs:
            return pd.DataFrame(), 0, [], "所有节点连接失败"
        
        best_df = all_dfs[0][1]
        avg_imbalance = sum(all_imbalances) / len(all_imbalances) if all_imbalances else 0
        status_msg = f"数据来自 {len(all_dfs)} 个交易所"
        
        return best_df, avg_imbalance, [], status_msg

def get_client():
    if 'client' not in st.session_state:
        st.session_state['client'] = MultiExchangeClientV2()
    return st.session_state['client']

def get_market_data():
    client = get_client()
    return client.fetch_klines_and_depth()

def get_advanced_signals_cached(df_hash, df, imbalance, walls):
    return comprehensive_signal_analysis_v2(df, imbalance=imbalance, walls=walls)

def get_ai_analysis(prompt):
    return "AI服务离线"

def plot_enhanced_candlestick(df, advanced_signals=None, trade_signals=None):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.5, 0.25, 0.25], subplot_titles=('K线图', '成交量', 'CVD'))
    
    # K线
    fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K线'), row=1, col=1)
    
    # EMA
    if 'ema21' in df.columns:
        fig.add_trace(go.Scatter(x=df['time'], y=df['ema21'], line=dict(color='#FFD700', width=1), name='EMA21'), row=1, col=1)
    if 'ema200' in df.columns:
        fig.add_trace(go.Scatter(x=df['time'], y=df['ema200'], line=dict(color='#00BFFF', width=1), name='EMA200'), row=1, col=1)
    
    # 支撑阻力
    if advanced_signals and 'signals' in advanced_signals:
        sr = advanced_signals['signals'].get('support_resistance', {})
        if sr.get('nearest_support'):
            fig.add_hline(y=sr['nearest_support'][1], line_dash="dash", line_color="#00FF00", opacity=0.8, row=1, col=1)
        if sr.get('nearest_resistance'):
            fig.add_hline(y=sr['nearest_resistance'][1], line_dash="dash", line_color="#FF0000", opacity=0.8, row=1, col=1)
    
    # 入场标记
    if trade_signals:
        for signal in trade_signals:
            idx = signal.get('index', len(df) - 1)
            if idx < len(df):
                row_data = df.iloc[idx]
                price = row_data['close']
                marker_symbol = 'triangle-up' if signal['direction'] == 'LONG' else 'triangle-down'
                marker_color = '#00FF00' if signal['direction'] == 'LONG' else '#FF0000'
                fig.add_trace(go.Scatter(x=[row_data['time']], y=[price], mode='markers', marker=dict(symbol=marker_symbol, size=15, color=marker_color), name=f"入场-{signal['direction']}"), row=1, col=1)
    
    # 成交量
    colors = ['#00FF00' if df.iloc[i]['close'] >= df.iloc[i]['open'] else '#FF0000' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df['time'], y=df['volume'], marker_color=colors, name='成交量', opacity=0.7), row=2, col=1)
    
    # CVD
    if 'cvd' in df.columns:
        fig.add_trace(go.Scatter(x=df['time'], y=df['cvd'], line=dict(color='cyan', width=1.5), name='CVD', fill='tozeroy', fillcolor='rgba(0, 255, 255, 0.2)'), row=3, col=1)
    
    fig.update_layout(template='plotly_dark', height=600, showlegend=True, plot_bgcolor='#0e1117', paper_bgcolor='#0e1117', font=dict(color='#e5e5e5'))
    
    return fig

# 主程序
def main():
    auto_refresh(5000)
    
    c_title, c_time = st.columns([4, 1])
    with c_title:
        st.title("🚀 ETHUSDT 量化巡航系统 V2.0")
    with c_time:
        st.markdown(f"### ⏰ {datetime.datetime.now().strftime('%H:%M:%S')}")
    
    client = get_client()
    
    if 'connection_tested' not in st.session_state:
        st.session_state['connection_results'] = client.test_all_connections()
        st.session_state['connection_tested'] = True
    
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
    
    with st.spinner("📡 获取数据..."):
        df, imbalance, walls, status_msg = get_market_data()
    
    if df.empty or df is None:
        st.error("❌ 连接失败")
        st.stop()

    # 历史回放：按日期范围过滤
    df = df.sort_values('time').reset_index(drop=True)
    min_date = df['time'].min().date()
    max_date = df['time'].max().date()

    with st.sidebar:
        st.markdown("---")
        st.subheader("🕰️ 历史回放")
        start_date = st.date_input("起始日期", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("结束日期", value=max_date, min_value=min_date, max_value=max_date)

    if start_date > end_date:
        st.error("❌ 起始日期不能晚于结束日期")
        st.stop()

    date_mask = (df['time'].dt.date >= start_date) & (df['time'].dt.date <= end_date)
    df = df.loc[date_mask].reset_index(drop=True)

    if df.empty:
        st.warning("⚠️ 当前日期范围无数据，请调整历史回放区间")
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
    
    # K线图
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
    
    # 核心指标行
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1: st.metric("💰 价格", f"${price:.2f}")
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
    
    # 核心区域
    st.markdown("---")
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        if advanced_signals and 'signals' in advanced_signals:
            if rec == "做多":
                st.success(f"🟢 **{rec}** | 置信度 {conf:.0f}%")
            elif rec == "做空":
                st.error(f"🔴 **{rec}** | 置信度 {conf:.0f}%")
            else:
                st.info(f"⚪ **{rec}** | 置信度 {conf:.0f}%")
            
            ms = sig_data.get('market_state', {})
            lstm = sig_data.get('lstm_prediction', {})
            st.write(f"🏛️ 市场: **{ms.get('state', '-')}** | 🤖 AI: **{lstm.get('trend', '-')}** ({lstm.get('probability', 0):.0f}%)")
            
            st.metric("📊 评分", f"多{advanced_signals['bullish_score']:.0f} / 空{advanced_signals['bearish_score']:.0f}")
            
            # 多周期趋势
            mtf = sig_data.get('multi_timeframe', {})
            if mtf:
                st.write(f"📈 **多周期趋势**: {mtf.get('description', '-')}")
            
            # MACD
            macd = sig_data.get('macd', {})
            if macd:
                cross = macd.get('cross', '')
                if cross:
                    st.info(f"📊 MACD **{cross}** | {macd.get('trend', '')}")
            
            # 仲裁结果
            arb = sig_data.get('signal_arbitration', {})
            if arb:
                st.info(f"📋 **仲裁结果**: {arb.get('final_decision', '')} - {arb.get('reason', '')}")
            
            # 关键信号
            alerts = []
            if sig_data.get('accumulation', {}).get('signal'): alerts.append("🔍主力吸筹")
            if sig_data.get('whale_pump', {}).get('signal'): alerts.append("🐋巨鲸拉升")
            if sig_data.get('crash_warning', {}).get('signal'): alerts.append("⚠️急跌风险")
            if sig_data.get('fake_breakout', {}).get('signal'): alerts.append("🎭假突破")
            if alerts: st.warning(" | ".join(alerts))
            
            # 支撑压力
            sr = sig_data.get('support_resistance', {})
            st.write(f"📍 {sr.get('description', '计算中')}")
            
            # 交易计划
            st.markdown("---")
            st.markdown("### 📋 交易计划" if rec in ["做多", "做空"] else "### 📊 参考区间")
            
            ns = sr.get('nearest_support')
            nr = sr.get('nearest_resistance')
            
            sl = ns[1] if ns else price * 0.98
            tp = nr[1] if nr else price * 1.02
            
            if rec == "做空":
                sl = nr[1] if nr else price * 1.02
                tp = ns[1] if ns else price * 0.98
            
            # 修复：如果止盈价格等于入场价，使用ATR动态计算
            atr = df['atr'].iloc[-1] if 'atr' in df.columns else price * 0.01
            if rec == "做空":
                # 做空止损在上方，止盈在下方
                if sl <= price:  # 止损应该在入场价上方
                    sl = price + atr * 1.5
                if tp >= price or abs(tp - price) < 1:  # 止盈应该在入场价下方
                    tp = price - atr * 2
            else:
                # 做多止损在下方，止盈在上方
                if sl >= price:  # 止损应该在入场价下方
                    sl = price - atr * 1.5
                if tp <= price or abs(tp - price) < 1:  # 止盈应该在入场价上方
                    tp = price + atr * 2
            
            risk = abs(price - sl) / price * 100
            reward = abs(tp - price) / price * 100
            rr = reward / risk if risk > 0 else 0
            
            p1, p2, p3 = st.columns(3)
            p1.metric("🎯 入场" if rec in ["做多", "做空"] else "📍 支撑", f"${price:.2f}" if rec in ["做多", "做空"] else f"${sl:.2f}")
            p2.metric("🛡️ 止损" if rec in ["做多", "做空"] else "📍 当前", f"${sl:.2f}" if rec in ["做多", "做空"] else f"${price:.2f}")
            p3.metric("💎 止盈" if rec in ["做多", "做空"] else "📍 压力", f"${tp:.2f}")
            
            if rec in ["做多", "做空"]:
                st.info(f"💰 盈亏比 **1:{rr:.1f}** | 建议仓位 **{min(2/risk, 50):.0f}%**")
            else:
                total_range = abs(tp - sl) / price * 100
                st.info(f"📊 区间波动 **{total_range:.1f}%**")
            
            if rec in ["做多", "做空"] and conf >= 70:
                try:
                    speak_alert(f"{rec}信号，置信度{conf:.0f}%，止损{sl:.0f}，止盈{tp:.0f}", "trade")
                except:
                    pass
        else:
            st.info("等待信号分析...")
    
    with col_right:
        st.subheader("🧠 AI 分析")
        st.warning("AI服务离线")
        if advanced_signals:
            st.info(advanced_signals.get('summary', '等待分析...'))

if __name__ == "__main__":
    main()
