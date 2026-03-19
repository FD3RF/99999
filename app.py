# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime

from data_fetcher import fetch_eth_klines, get_realtime_price
from indicators import (
    calculate_macd, calculate_volume_metrics,
    find_swing_points, identify_candlestick_patterns
)
from signal_engine import SignalEngine
from config import *

st.set_page_config(page_title="以太坊5分钟合约AI播报系统", page_icon="📊", layout="wide")

# 自定义CSS
st.markdown("""
<style>
    .signal-box { padding:20px; border-radius:10px; margin:10px 0; font-family:monospace; }
    .long-signal { background-color:#d4edda; border-left:5px solid #28a745; }
    .short-signal { background-color:#f8d7da; border-left:5px solid #dc3545; }
    .conflict-signal { background-color:#fff3cd; border-left:5px solid #ffc107; }
    .mnemonic { font-size:1.1em; font-weight:bold; color:#2c3e50; background-color:#f8f9fa; padding:10px; border-radius:5px; border:1px solid #dee2e6; }
    .price-badge { font-size:1.5em; font-weight:bold; padding:10px; background-color:#e9ecef; border-radius:5px; text-align:center; }
</style>
""", unsafe_allow_html=True)

st.title("📊 以太坊5分钟合约 · AI精准播报系统（终极完美口诀版）")
st.markdown("---")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 系统配置")
    refresh_rate = st.slider("数据刷新频率（秒）", 10, 120, 30, 10)
    point_value = st.number_input("合约点值 (U/点)", value=DEFAULT_POINT_VALUE, min_value=1)
    total_capital = st.number_input("总资金 (U)", min_value=100, value=10000, step=1000)
    risk_percent = st.slider("单笔风险 (%)", 0.5, 5.0, MAX_RISK_PER_TRADE*100, 0.5) / 100

    st.markdown("---")
    st.subheader("📜 交易圣经摘要")
    with st.expander("做多口诀"):
        st.info("趋势回调做多：缩量回踩底不破，底背离/金叉等放量；放量起涨破前高，红柱放大直接多。\n\n陷阱诱空做多：放量急跌底不破，底背离现长脚线；恐慌释放即机会，企稳收阳反手多。\n\n横盘突破做多：缩量横盘低点托，MACD粘合小K线；谁先放量向上突，突破区间立即多。\n\n趋势延续做多：强势上涨中，放量阳线创新高，MACD红柱持续放大，下一根开盘追多。")
    with st.expander("做空口诀"):
        st.warning("趋势反弹做空：缩量反弹顶不过，顶背离/死叉等放量；放量下跌破前低，绿柱放大直接空。\n\n陷阱诱多做空：放量急涨顶不破，顶背离现长上影；多头陷阱莫追高，回落收阴反手空。\n\n横盘突破做空：缩量横盘高点压，MACD粘合小K线；谁先放量向下破，跌破区间立即空。\n\n趋势延续做空：强势下跌中，放量阴线创新低，MACD绿柱持续放大，下一根开盘追空。")
    with st.expander("总则"):
        st.success("信号冲突则观望，连续止损即休息。缩量是提醒，放量是信号，MACD辨强弱，K线定形态。严守纪律，盈亏比至上，长期执行方为王。")

    if st.button("🔄 立即刷新数据"):
        st.cache_data.clear()
        st.rerun()

# 初始化session state
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []
    st.session_state.consecutive_losses = 0
    st.session_state.last_signal_time = None
    st.session_state.daily_loss_count = 0
    st.session_state.last_trade_day = datetime.now().date()

# 主界面
col1, col2 = st.columns([2, 1])

placeholder = st.empty()
refresh_counter = st.empty()

while True:
    with placeholder.container():
        df = fetch_eth_klines()
        if df is not None and len(df) > 30:
            # 计算指标
            df = calculate_macd(df)
            df = calculate_volume_metrics(df)
            df = find_swing_points(df)
            df = identify_candlestick_patterns(df)

            current_price = df.iloc[-1]["close"]
            prev_price = df.iloc[-2]["close"]
            price_change = current_price - prev_price
            price_change_pct = (price_change / prev_price) * 100

            with col1:
                st.markdown(f"""
                <div class="price-badge">
                    ETH/USDT: ${current_price:.2f}
                    <span style="color: {'#28a745' if price_change >= 0 else '#dc3545'};">
                        ({price_change:+.2f} / {price_change_pct:+.2f}%)
                    </span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### 📈 5分钟K线图（实时）")
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                                    row_heights=[0.6, 0.2, 0.2],
                                    subplot_titles=("价格", "成交量", "MACD"))
                # K线
                fig.add_trace(go.Candlestick(x=df["timestamp"], open=df["open"], high=df["high"],
                                              low=df["low"], close=df["close"], name="ETH/USDT",
                                              increasing_line_color='#26a69a', decreasing_line_color='#ef5350'),
                              row=1, col=1)
                # 成交量
                colors = ['#26a69a' if row['open'] < row['close'] else '#ef5350' for _, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], name="成交量", marker_color=colors, showlegend=False), row=2, col=1)
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["volume_ma20"], name="20周期均量线",
                                         line=dict(color='orange', width=2, dash='dash')), row=2, col=1)
                # MACD
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["dif"], name="DIF", line=dict(color='blue', width=2)), row=3, col=1)
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["dea"], name="DEA", line=dict(color='red', width=2)), row=3, col=1)
                macd_colors = ['red' if val >= 0 else 'green' for val in df["macd_hist"]]
                fig.add_trace(go.Bar(x=df["timestamp"], y=df["macd_hist"], name="MACD柱", marker_color=macd_colors, showlegend=False), row=3, col=1)

                fig.update_layout(height=700, xaxis_rangeslider_visible=False, template="plotly_dark", hovermode="x unified")
                fig.update_xaxes(title_text="时间", row=3, col=1)
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("📋 当前K线详情"):
                    lat = df.iloc[-1]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("开盘", f"${lat['open']:.2f}")
                    c2.metric("最高", f"${lat['high']:.2f}")
                    c3.metric("最低", f"${lat['low']:.2f}")
                    c4.metric("收盘", f"${lat['close']:.2f}")
                    c5, c6, c7, c8 = st.columns(4)
                    c5.metric("成交量", f"{lat['volume']:.2f}")
                    c6.metric("成交量状态", lat['volume_status'])
                    c7.metric("MACD柱", f"{lat['macd_hist']:.2f}")
                    c8.metric("K线形态", engine._get_kline_pattern_names() if 'engine' in locals() else "普通")

            with col2:
                st.markdown("#### 🎯 AI交易信号播报")

                # 检查交易时间过滤（简单示例）
                now = datetime.now()
                current_hour_min = (now.hour, now.minute)
                # 此处可添加禁止交易时段判断，暂略

                engine = SignalEngine(df)
                signals = engine.get_all_signals()

                if signals:
                    for sig in signals:
                        if sig["direction"] == "LONG":
                            st.markdown(f"""
                            <div class="signal-box long-signal">
                                <h3 style="color:#28a745;">📈 做多信号 - {sig['type']}</h3>
                                <p><strong>入场价:</strong> ${sig['entry']:.2f}</p>
                                <p><strong>止损价:</strong> ${sig['stop_loss']:.2f} ({- (sig['entry']-sig['stop_loss'])/sig['entry']*100:.2f}%)</p>
                                <p><strong>目标价:</strong> ${sig['target']:.2f} (盈亏比 {MIN_RISK_REWARD_RATIO}:1)</p>
                                <p>📝 {sig['reason']}</p>
                                <div class="mnemonic">📖 口诀：{sig['mnemonic']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        elif sig["direction"] == "SHORT":
                            st.markdown(f"""
                            <div class="signal-box short-signal">
                                <h3 style="color:#dc3545;">📉 做空信号 - {sig['type']}</h3>
                                <p><strong>入场价:</strong> ${sig['entry']:.2f}</p>
                                <p><strong>止损价:</strong> ${sig['stop_loss']:.2f} (+{(sig['stop_loss']-sig['entry'])/sig['entry']*100:.2f}%)</p>
                                <p><strong>目标价:</strong> ${sig['target']:.2f} (盈亏比 {MIN_RISK_REWARD_RATIO}:1)</p>
                                <p>📝 {sig['reason']}</p>
                                <div class="mnemonic">📖 口诀：{sig['mnemonic']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:  # CONFLICT
                            st.markdown(f"""
                            <div class="signal-box conflict-signal">
                                <h3 style="color:#ffc107;">⚠️ 信号冲突</h3>
                                <p>{sig['reason']}</p>
                                <div class="mnemonic">📖 口诀：{sig['mnemonic']}</div>
                            </div>
                            """, unsafe_allow_html=True)

                        # 记录新信号（避免重复）
                        if sig["direction"] in ["LONG", "SHORT"]:
                            now_time = datetime.now()
                            # 简单去重：与上一条信号类型不同或时间超过5分钟
                            if (not st.session_state.last_signal_time or
                                (now_time - st.session_state.last_signal_time).seconds > 300 or
                                (st.session_state.trade_history and
                                 st.session_state.trade_history[-1]["type"] != sig["type"])):
                                st.session_state.trade_history.append({
                                    "time": now_time.strftime("%H:%M"),
                                    "type": sig["type"],
                                    "direction": sig["direction"],
                                    "entry": sig["entry"]
                                })
                                st.session_state.last_signal_time = now_time
                else:
                    st.info("⏳ 暂无明确交易信号，等待市场条件匹配口诀...")

                st.markdown("---")
                st.markdown("#### 💼 仓位计算器")
                if signals and signals[0]["direction"] in ["LONG", "SHORT"]:
                    sig = signals[0]
                    stop_dist = abs(sig["entry"] - sig["stop_loss"])
                    max_loss = total_capital * risk_percent
                    position = max_loss / (stop_dist * point_value) if stop_dist > 0 else 0
                    st.metric("建议仓位 (张)", f"{position:.2f}")
                    st.metric("最大亏损", f"${max_loss:.2f} ({(risk_percent*100):.1f}%)")
                    st.caption(f"止损距离: {stop_dist:.2f} USDT")
                else:
                    st.info("出现信号后自动计算仓位")

                st.markdown("---")
                st.markdown("#### 📡 系统状态")
                st.success(f"✅ 数据更新时间: {datetime.now().strftime('%H:%M:%S')}")
                st.info(f"📊 当前K线数量: {len(df)}")

                # 连续亏损计数（模拟，实际需要用户手动输入）
                st.markdown("#### ⚠️ 风控状态")
                col_a, col_b = st.columns(2)
                col_a.metric("连续亏损", st.session_state.consecutive_losses)
                col_b.metric("当日亏损次数", st.session_state.daily_loss_count)

                # 每日重置
                today = datetime.now().date()
                if today != st.session_state.last_trade_day:
                    st.session_state.daily_loss_count = 0
                    st.session_state.consecutive_losses = 0
                    st.session_state.last_trade_day = today

                # 展示历史信号
                if st.session_state.trade_history:
                    with st.expander("📋 今日信号记录"):
                        for t in st.session_state.trade_history[-10:]:
                            st.text(f"{t['time']} - {t['direction']} - {t['type']} @ {t['entry']:.2f}")

        else:
            st.error("无法获取数据，请检查网络连接或API")

    with refresh_counter:
        st.caption(f"⏱️ 下次刷新: {refresh_rate}秒后...")

    time.sleep(refresh_rate)
    st.cache_data.clear()
    st.rerun()
