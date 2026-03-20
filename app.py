# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime

from data_fetcher import fetch_eth_klines
from indicators import (
    calculate_macd, calculate_volume_metrics,
    find_swing_points, identify_candlestick_patterns,
    calculate_support_resistance
)
from signal_engine import SignalEngine
from config import *

st.set_page_config(page_title="以太坊AI合约交易系统", page_icon="📊", layout="wide")

# 自定义CSS
st.markdown("""
<style>
    .signal-box { padding:20px; border-radius:10px; margin:10px 0; font-family:monospace; }
    .long-signal { background-color:#d4edda; border-left:5px solid #28a745; }
    .short-signal { background-color:#f8d7da; border-left:5px solid #dc3545; }
    .conflict-signal { background-color:#fff3cd; border-left:5px solid #ffc107; }
    .mnemonic { font-size:1.1em; font-weight:bold; color:#2c3e50; background-color:#f8f9fa; padding:10px; border-radius:5px; border:1px solid #dee2e6; }
    .price-badge { font-size:1.5em; font-weight:bold; padding:10px; background-color:#e9ecef; border-radius:5px; text-align:center; }
    .support-resistance { padding:10px; margin:5px 0; border-radius:5px; text-align:center; font-weight:bold; }
    .support { background-color:#d4edda; color:#155724; }
    .resistance { background-color:#f8d7da; color:#721c24; }
    .current-price { font-size:2em; font-weight:bold; text-align:center; }
</style>
""", unsafe_allow_html=True)

st.title("📊 以太坊5分钟合约 · AI智能交易系统")
st.markdown("---")

# 语音播报函数
def generate_speech_text(signals, price, direction):
    """生成语音播报文本"""
    if not signals:
        return None
    
    sig = signals[0]
    if sig["direction"] == "CONFLICT":
        return "警告，多空信号冲突，请观望"
    
    direction_text = "做多" if sig["direction"] == "LONG" else "做空"
    price_text = f"当前价格{price:.2f}美元"
    entry_text = f"建议入场价{sig['entry']:.2f}"
    stop_text = f"止损价{sig['stop_loss']:.2f}"
    target_text = f"止盈价{sig['target']:.2f}"
    type_text = sig['type']
    
    return f"注意，{direction_text}信号，{price_text}，{type_text}，{entry_text}，{stop_text}，{target_text}"

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 系统配置")
    refresh_rate = st.slider("刷新频率(秒)", 10, 120, 30, 10)
    point_value = st.number_input("合约点值(U/点)", value=DEFAULT_POINT_VALUE, min_value=1)
    total_capital = st.number_input("总资金(U)", min_value=100, value=10000, step=1000)
    risk_percent = st.slider("单笔风险(%)", 0.5, 5.0, MAX_RISK_PER_TRADE*100, 0.5) / 100
    
    # 语音播报开关（折叠）
    st.markdown("---")
    with st.expander("🔊 语音播报设置"):
        enable_voice = st.checkbox("开启语音提醒", value=True)
        voice_interval = st.slider("播报间隔(分钟)", 1, 30, 5)
    
    st.markdown("---")
    st.subheader("📜 交易口诀")
    with st.expander("做多口诀"):
        st.info("趋势回调做多：缩量回踩底不破，金叉放量突破前高，红柱放大直接多。\n\n陷阱诱空做多：放量急跌底不破，恐慌释放收阳反手多。\n\n横盘突破做多：缩量横盘MACD粘合，放量突破立即多。")
    with st.expander("做空口诀"):
        st.warning("趋势反弹做空：缩量反弹顶不过，死叉放量跌破前低，绿柱放大直接空。\n\n陷阱诱多做空：放量急涨顶不破，回落收阴反手空。\n\n横盘突破做空：缩量横盘MACD粘合，放量跌破立即空。")

    if st.button("🔄 立即刷新"):
        st.cache_data.clear()
        st.rerun()

# 初始化session state
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []
    st.session_state.consecutive_losses = 0
    st.session_state.last_signal_time = None
    st.session_state.daily_loss_count = 0
    st.session_state.last_trade_day = datetime.now().date()
    st.session_state.last_voice_time = None
    st.session_state.last_signal_text = ""
    st.session_state.spoken_signals = []

# 主界面
col1, col2 = st.columns([2, 1])

placeholder = st.empty()

while True:
    with placeholder.container():
        df = fetch_eth_klines()
        if df is not None and len(df) > 30:
            # 计算指标
            df = calculate_macd(df)
            df = calculate_volume_metrics(df)
            df = find_swing_points(df)
            df = identify_candlestick_patterns(df)
            
            # 计算支撑位压力位
            support, resistance = calculate_support_resistance(df)
            
            current_price = df.iloc[-1]["close"]
            prev_price = df.iloc[-2]["close"]
            price_change = current_price - prev_price
            price_change_pct = (price_change / prev_price) * 100
            
            with col1:
                # 当前价格显示
                price_color = "#28a745" if price_change >= 0 else "#dc3545"
                st.markdown(f"""
                <div class="current-price">
                    ETH/USDT: <span style="color:{price_color}">${current_price:.2f}</span>
                    <span style="font-size:0.6em; color:{price_color}">({price_change:+.2f} / {price_change_pct:+.2f}%)</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 支撑位压力位
                st.markdown(f"""
                <div class="support-resistance support">🔵 支撑位: ${support:.2f}</div>
                <div class="support-resistance resistance">🔴 压力位: ${resistance:.2f}</div>
                """, unsafe_allow_html=True)
                
                # K线图
                st.markdown("#### 📈 5分钟K线图")
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                                    row_heights=[0.6, 0.2, 0.2],
                                    subplot_titles=("价格", "成交量", "MACD"))
                
                # K线
                fig.add_trace(go.Candlestick(x=df["timestamp"], open=df["open"], high=df["high"],
                                              low=df["low"], close=df["close"], name="ETH/USDT",
                                              increasing_line_color='#26a69a', decreasing_line_color='#ef5350'),
                              row=1, col=1)
                
                # 添加当前价格线
                fig.add_hline(y=current_price, line_dash="dash", line_color="yellow", 
                             line_width=2, annotation_text=f"当前价: {current_price:.2f}", 
                             row=1, col=1)
                
                # 添加支撑位线
                fig.add_hline(y=support, line_dash="dot", line_color="blue", line_width=1,
                             annotation_text=f"支撑: {support:.2f}", row=1, col=1)
                
                # 添加压力位线
                fig.add_hline(y=resistance, line_dash="dot", line_color="red", line_width=1,
                             annotation_text=f"压力: {resistance:.2f}", row=1, col=1)
                
                # 成交量
                colors = ['#26a69a' if row['open'] < row['close'] else '#ef5350' for _, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], marker_color=colors, showlegend=False), row=2, col=1)
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["volume_ma20"], name="20日均量",
                                         line=dict(color='orange', width=2, dash='dash')), row=2, col=1)
                
                # MACD
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["dif"], name="DIF", line=dict(color='blue', width=2)), row=3, col=1)
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["dea"], name="DEA", line=dict(color='red', width=2)), row=3, col=1)
                macd_colors = ['red' if val >= 0 else 'green' for val in df["macd_hist"]]
                fig.add_trace(go.Bar(x=df["timestamp"], y=df["macd_hist"], marker_color=macd_colors, showlegend=False), row=3, col=1)
                
                fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

                # K线详情精简展示 - 整合到K线图下方
                lat = df.iloc[-1]
                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("开盘", f"${lat['open']:.2f}")
                k2.metric("最高", f"${lat['high']:.2f}")
                k3.metric("最低", f"${lat['low']:.2f}")
                k4.metric("收盘", f"${lat['close']:.2f}")
                k5.metric("成交量", f"{lat['volume']:.0f}", delta=lat['volume_status'])

            with col2:
                st.markdown("#### 🎯 AI交易信号")
                
                engine = SignalEngine(df, support, resistance)
                signals = engine.get_all_signals()
                
                # 语音播报
                voice_text = generate_speech_text(signals, current_price, "neutral")
                
                if signals:
                    for sig in signals:
                        if sig["direction"] == "LONG":
                            st.markdown(f"""
                            <div class="signal-box long-signal">
                                <h3 style="color:#28a745;">📈 做多</h3>
                                <p><strong>入场:</strong> ${sig['entry']:.2f}</p>
                                <p><strong>止损:</strong> ${sig['stop_loss']:.2f} (-{abs(sig['entry']-sig['stop_loss'])/sig['entry']*100:.2f}%)</p>
                                <p><strong>止盈:</strong> ${sig['target']:.2f}</p>
                                <div class="mnemonic">📖 {sig['mnemonic']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        elif sig["direction"] == "SHORT":
                            st.markdown(f"""
                            <div class="signal-box short-signal">
                                <h3 style="color:#dc3545;">📉 做空</h3>
                                <p><strong>入场:</strong> ${sig['entry']:.2f}</p>
                                <p><strong>止损:</strong> ${sig['stop_loss']:.2f} (+{abs(sig['entry']-sig['stop_loss'])/sig['entry']*100:.2f}%)</p>
                                <p><strong>止盈:</strong> ${sig['target']:.2f}</p>
                                <div class="mnemonic">📖 {sig['mnemonic']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="signal-box conflict-signal">
                                <h3 style="color:#ffc107;">⚠️ 信号冲突</h3>
                                <p>{sig['reason']}</p>
                            </div>
                            """, unsafe_allow_html=True)

                        # 语音播报（带去重机制）
                        if sig["direction"] in ["LONG", "SHORT"] and enable_voice:
                            signal_id = f"{sig['type']}_{sig['entry']:.2f}_{sig['direction']}"
                            if signal_id not in st.session_state.spoken_signals:
                                # 添加到已播报列表
                                st.session_state.spoken_signals.append(signal_id)
                                if len(st.session_state.spoken_signals) > 50:
                                    st.session_state.spoken_signals = st.session_state.spoken_signals[-50:]
                                # 构造播报文本
                                direction_text = "做多" if sig["direction"] == "LONG" else "做空"
                                speech_text = f"注意，{direction_text}信号，{sig['type']}，入场价{sig['entry']:.2f}，止损{sig['stop_loss']:.2f}，止盈{sig['target']:.2f}"
                                # 触发语音播报
                                st.components.v1.html(f"""
                                <script>
                                    var utterance = new SpeechSynthesisUtterance("{speech_text}");
                                    utterance.lang = 'zh-CN';
                                    utterance.rate = 1.0;
                                    window.speechSynthesis.speak(utterance);
                                </script>
                                """, height=0)

                        # 记录信号
                        if sig["direction"] in ["LONG", "SHORT"]:
                            now = datetime.now()
                            if (not st.session_state.last_signal_time or
                                (now - st.session_state.last_signal_time).seconds > 300 or
                                (st.session_state.trade_history and st.session_state.trade_history[-1]["type"] != sig["type"])):
                                st.session_state.trade_history.append({
                                    "time": now.strftime("%H:%M"),
                                    "type": sig["type"],
                                    "direction": sig["direction"],
                                    "entry": sig["entry"]
                                })
                                st.session_state.last_signal_time = now
                else:
                    st.info("⏳ 暂无信号，等待市场条件...")

                # 精简布局：仓位和系统状态放一行
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**💼 仓位**")
                    if signals and signals[0]["direction"] in ["LONG", "SHORT"]:
                        sig = signals[0]
                        stop_dist = abs(sig["entry"] - sig["stop_loss"])
                        max_loss = total_capital * risk_percent
                        position = max_loss / (stop_dist * point_value) if stop_dist > 0 else 0
                        st.metric("建议仓位", f"{position:.1f} 张")
                        st.caption(f"最大亏损: ${max_loss:.0f}")
                    else:
                        st.caption("等待信号...")

                with col_b:
                    st.markdown("**📡 系统**")
                    st.caption(f"更新: {datetime.now().strftime('%H:%M:%S')}")
                    st.caption(f"K线: {len(df)}")

                # 风控状态小字展示
                st.caption(f"⚠️ 连亏 {st.session_state.consecutive_losses} | 日亏 {st.session_state.daily_loss_count}")

                # 信号历史（可选展开）
                if st.session_state.trade_history:
                    with st.expander("📋 信号记录"):
                        for t in st.session_state.trade_history[-5:]:
                            st.text(f"{t['time']} {t['direction']} {t['type']}")
        
        else:
            st.error("无法获取数据")
    
    # 自动刷新
    time.sleep(refresh_rate)
    st.cache_data.clear()
    st.rerun()
