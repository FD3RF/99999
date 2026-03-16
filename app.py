import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union

# -------------------- 页面配置 --------------------
st.set_page_config(
    page_title="以太坊5分钟多空信号系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- 数据加载与预处理 --------------------
@st.cache_data(ttl=3600)
def load_data(uploaded_file=None) -> Optional[pd.DataFrame]:
    """
    从上传文件或默认路径加载数据，并预处理
    """
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"文件读取失败: {e}")
            return None
    else:
        # 默认文件路径（可修改）
        default_path = "ETHUSDT_5m_1y_okx.csv"
        try:
            df = pd.read_csv(default_path)
        except FileNotFoundError:
            st.warning("未找到默认数据文件，请上传CSV文件")
            return None
        except Exception as e:
            st.error(f"默认文件读取失败: {e}")
            return None

    # 解析时间戳
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
    elif 'timestamp' in df.columns:
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
    else:
        st.error("数据文件中缺少时间列（datetime 或 timestamp）")
        return None

    # 确保数据类型正确
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        if col not in df.columns:
            st.error(f"数据文件缺少必要列: {col}")
            return None
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.dropna(subset=numeric_cols, inplace=True)
    df.sort_index(inplace=True)
    return df

# -------------------- 技术指标计算 --------------------
def add_moving_average(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """简单移动平均"""
    return df[column].rolling(window=period).mean()


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """相对强弱指标 RSI"""
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    # 避免除零
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD 指标"""
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """布林带"""
    sma = df['close'].rolling(window=period).mean()
    std_dev = df['close'].rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, sma, lower_band


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """平均真实范围 ATR (修复版)"""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    # 正确计算 true_range 的最大值
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr


# -------------------- 信号生成策略基类 --------------------
class SignalStrategy:
    """信号策略基类"""

    def __init__(self, params: Dict[str, Any]):
        self.params = params

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """返回信号序列：1=买入，-1=卖出，0=无信号"""
        raise NotImplementedError

    def get_name(self) -> str:
        return self.__class__.__name__


# -------------------- 具体策略实现 --------------------
class MovingAverageCross(SignalStrategy):
    """双均线交叉策略"""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = self.params.get('fast_period', 5)
        slow = self.params.get('slow_period', 20)
        ma_fast = add_moving_average(df, fast)
        ma_slow = add_moving_average(df, slow)
        signals = pd.Series(0, index=df.index)
        # 金叉买入
        condition_buy = (ma_fast > ma_slow) & (ma_fast.shift() <= ma_slow.shift())
        signals[condition_buy] = 1
        # 死叉卖出
        condition_sell = (ma_fast < ma_slow) & (ma_fast.shift() >= ma_slow.shift())
        signals[condition_sell] = -1
        return signals


class RsiStrategy(SignalStrategy):
    """RSI超买超卖策略"""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get('rsi_period', 14)
        oversold = self.params.get('oversold', 30)
        overbought = self.params.get('overbought', 70)
        rsi = add_rsi(df, period)
        signals = pd.Series(0, index=df.index)
        # 从超卖区域向上突破买入
        condition_buy = (rsi < oversold) & (rsi.shift() >= oversold)
        signals[condition_buy] = 1
        # 从超买区域向下突破卖出
        condition_sell = (rsi > overbought) & (rsi.shift() <= overbought)
        signals[condition_sell] = -1
        return signals


class MacdStrategy(SignalStrategy):
    """MACD金叉死叉策略"""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = self.params.get('fast', 12)
        slow = self.params.get('slow', 26)
        signal = self.params.get('signal', 9)
        macd, signal_line, _ = add_macd(df, fast, slow, signal)
        signals = pd.Series(0, index=df.index)
        condition_buy = (macd > signal_line) & (macd.shift() <= signal_line.shift())
        signals[condition_buy] = 1
        condition_sell = (macd < signal_line) & (macd.shift() >= signal_line.shift())
        signals[condition_sell] = -1
        return signals


class BollingerBandsStrategy(SignalStrategy):
    """布林带突破策略"""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get('bb_period', 20)
        std = self.params.get('bb_std', 2)
        upper, _, lower = add_bollinger_bands(df, period, std)
        signals = pd.Series(0, index=df.index)
        # 价格跌破下轨买入
        condition_buy = (df['low'] <= lower) & (df['low'].shift() > lower.shift())
        signals[condition_buy] = 1
        # 价格突破上轨卖出
        condition_sell = (df['high'] >= upper) & (df['high'].shift() < upper.shift())
        signals[condition_sell] = -1
        return signals


class CombinedStrategy(SignalStrategy):
    """
    组合策略：要求所有子策略在同一时刻发出相同方向的信号
    子策略列表通过 params['strategies'] 传入
    """

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.strategies = params.get('strategies', [])

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if not self.strategies:
            return pd.Series(0, index=df.index)
        # 获取所有子策略的信号
        signal_list = [s.generate_signals(df) for s in self.strategies]
        # 向量化组合
        signal_df = pd.DataFrame(signal_list).T
        buy_signals = (signal_df == 1).all(axis=1)
        sell_signals = (signal_df == -1).all(axis=1)
        signals = pd.Series(0, index=df.index)
        signals[buy_signals] = 1
        signals[sell_signals] = -1
        return signals


# -------------------- 策略工厂 --------------------
def get_available_strategies() -> Dict[str, type]:
    return {
        "双均线交叉": MovingAverageCross,
        "RSI超买超卖": RsiStrategy,
        "MACD金叉死叉": MacdStrategy,
        "布林带突破": BollingerBandsStrategy,
    }


def create_strategy(strategy_name: str, params: Dict[str, Any]) -> SignalStrategy:
    """根据策略名称和参数创建策略实例"""
    strategies = get_available_strategies()
    if strategy_name in strategies:
        return strategies[strategy_name](params)
    if strategy_name == "自定义组合":
        # 自定义组合需要预先在 params 中提供子策略列表
        return CombinedStrategy(params)
    raise ValueError(f"未知策略: {strategy_name}")


# -------------------- 回测评估 --------------------
def backtest(
    df: pd.DataFrame,
    signals: pd.Series,
    initial_capital: float = 10000,
    slippage: float = 0.0001,
    commission: float = 0.0005,
) -> Dict[str, Any]:
    """
    回测函数
    :param df: 包含价格的数据框
    :param signals: 信号序列 (-1,0,1)
    :param initial_capital: 初始资金
    :param slippage: 滑点（百分比，双向）
    :param commission: 手续费率（百分比，双向）
    :return: 回测结果字典
    """
    # 确保信号只有 -1,0,1
    sig = signals.clip(-1, 1).copy()

    trades = []
    position = 0  # 当前持仓：1 多头，-1 空头，0 空仓
    entry_price = 0.0
    entry_time = None
    capital = initial_capital
    equity_curve = [capital]

    for i in range(1, len(sig)):
        current_signal = sig.iloc[i]
        prev_signal = sig.iloc[i - 1]
        current_price = df['close'].iloc[i]
        current_time = df.index[i]

        # 信号变化时进行交易
        if current_signal != prev_signal:
            # 先平仓（如有持仓）
            if position == 1:  # 平多
                pnl = (current_price - entry_price) * (capital / entry_price)
                # 扣除滑点+手续费（双向）
                capital = capital + pnl - (slippage + commission) * capital
                trades.append(
                    {
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'type': 'long',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                    }
                )
                position = 0
            elif position == -1:  # 平空
                pnl = (entry_price - current_price) * (capital / entry_price)
                capital = capital + pnl - (slippage + commission) * capital
                trades.append(
                    {
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'type': 'short',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                    }
                )
                position = 0

            # 开新仓
            if current_signal == 1:
                position = 1
                entry_price = current_price
                entry_time = current_time
                # 开仓扣除滑点+手续费（简化：从资金中扣减）
                capital -= capital * (slippage + commission)
            elif current_signal == -1:
                position = -1
                entry_price = current_price
                entry_time = current_time
                capital -= capital * (slippage + commission)

        equity_curve.append(capital)

    # 回测结束，平掉剩余持仓
    if position != 0:
        final_price = df['close'].iloc[-1]
        if position == 1:
            pnl = (final_price - entry_price) * (capital / entry_price)
        else:
            pnl = (entry_price - final_price) * (capital / entry_price)
        capital += pnl
        capital -= capital * (slippage + commission)  # 最后平仓也扣除成本
        trades.append(
            {
                'entry_time': entry_time,
                'exit_time': df.index[-1],
                'type': 'long' if position == 1 else 'short',
                'entry_price': entry_price,
                'exit_price': final_price,
                'pnl': pnl,
            }
        )
        equity_curve.append(capital)

    # 统计指标
    total_trades = len(trades)
    if total_trades == 0:
        win_rate = 0.0
        total_pnl = 0.0
        avg_pnl = 0.0
        max_drawdown = 0.0
    else:
        pnls = [t['pnl'] for t in trades]
        winning = [p for p in pnls if p > 0]
        win_rate = len(winning) / total_trades * 100
        total_pnl = capital - initial_capital
        avg_pnl = total_pnl / total_trades

        # 最大回撤
        equity = pd.Series(equity_curve)
        peak = equity.expanding().max()
        drawdown = (peak - equity) / peak
        max_drawdown = drawdown.max() * 100

    return {
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_return': (capital - initial_capital) / initial_capital * 100,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_pnl': avg_pnl,
        'max_drawdown': max_drawdown,
        'trades': trades,
        'equity_curve': equity_curve,
    }


# -------------------- Streamlit 界面 --------------------
def main():
    st.title("📊 以太坊5分钟多空信号系统")
    st.markdown("基于真实历史数据回测，提供高胜率交易信号（非自动下单）")

    # 侧边栏：数据上传
    st.sidebar.header("数据源")
    uploaded_file = st.sidebar.file_uploader("上传CSV文件", type=['csv'])

    # 加载数据
    df = load_data(uploaded_file)
    if df is None:
        st.stop()

    # 显示数据概览
    with st.expander("数据概览"):
        st.write(f"数据时间范围: {df.index.min()} 至 {df.index.max()}")
        st.write(f"总数据量: {len(df)} 条")
        st.dataframe(df.head())

    # 侧边栏策略配置
    st.sidebar.header("策略配置")

    # 策略选择模式：单一策略 或 自定义组合
    mode = st.sidebar.radio("选择模式", ["单一策略", "自定义组合"])

    strategy_instances = []

    if mode == "单一策略":
        strategy_options = list(get_available_strategies().keys())
        selected = st.sidebar.selectbox("选择策略", strategy_options)
        params = {}

        # 动态参数输入
        if selected == "双均线交叉":
            col1, col2 = st.sidebar.columns(2)
            params['fast_period'] = col1.number_input("快线周期", min_value=1, max_value=100, value=5)
            params['slow_period'] = col2.number_input("慢线周期", min_value=2, max_value=200, value=20)
        elif selected == "RSI超买超卖":
            params['rsi_period'] = st.sidebar.number_input("RSI周期", min_value=2, max_value=50, value=14)
            col1, col2 = st.sidebar.columns(2)
            params['oversold'] = col1.number_input("超卖阈值", min_value=1, max_value=50, value=30)
            params['overbought'] = col2.number_input("超买阈值", min_value=50, max_value=99, value=70)
        elif selected == "MACD金叉死叉":
            col1, col2, col3 = st.sidebar.columns(3)
            params['fast'] = col1.number_input("快线", min_value=1, max_value=50, value=12)
            params['slow'] = col2.number_input("慢线", min_value=2, max_value=100, value=26)
            params['signal'] = col3.number_input("信号线", min_value=1, max_value=30, value=9)
        elif selected == "布林带突破":
            col1, col2 = st.sidebar.columns(2)
            params['bb_period'] = col1.number_input("周期", min_value=5, max_value=100, value=20)
            params['bb_std'] = col2.number_input("标准差倍数", min_value=1, max_value=5, value=2)

        strategy_instances.append(create_strategy(selected, params))

    else:  # 自定义组合模式
        st.sidebar.subheader("选择要组合的策略")
        all_strategies = list(get_available_strategies().keys())
        selected_strategies = st.sidebar.multiselect("至少选择两个策略", all_strategies)

        if len(selected_strategies) < 2:
            st.sidebar.warning("组合模式需要至少选择两个策略")
        else:
            # 为每个选中的策略收集参数
            for strat_name in selected_strategies:
                with st.sidebar.expander(f"{strat_name} 参数"):
                    params = {}
                    if strat_name == "双均线交叉":
                        col1, col2 = st.columns(2)
                        params['fast_period'] = col1.number_input(
                            f"{strat_name} 快线周期",
                            min_value=1,
                            max_value=100,
                            value=5,
                            key=f"{strat_name}_fast",
                        )
                        params['slow_period'] = col2.number_input(
                            f"{strat_name} 慢线周期",
                            min_value=2,
                            max_value=200,
                            value=20,
                            key=f"{strat_name}_slow",
                        )
                    elif strat_name == "RSI超买超卖":
                        params['rsi_period'] = st.number_input(
                            f"{strat_name} RSI周期",
                            min_value=2,
                            max_value=50,
                            value=14,
                            key=f"{strat_name}_rsi",
                        )
                        col1, col2 = st.columns(2)
                        params['oversold'] = col1.number_input(
                            f"{strat_name} 超卖阈值",
                            min_value=1,
                            max_value=50,
                            value=30,
                            key=f"{strat_name}_os",
                        )
                        params['overbought'] = col2.number_input(
                            f"{strat_name} 超买阈值",
                            min_value=50,
                            max_value=99,
                            value=70,
                            key=f"{strat_name}_ob",
                        )
                    elif strat_name == "MACD金叉死叉":
                        col1, col2, col3 = st.columns(3)
                        params['fast'] = col1.number_input(
                            f"{strat_name} 快线",
                            min_value=1,
                            max_value=50,
                            value=12,
                            key=f"{strat_name}_fast",
                        )
                        params['slow'] = col2.number_input(
                            f"{strat_name} 慢线",
                            min_value=2,
                            max_value=100,
                            value=26,
                            key=f"{strat_name}_slow",
                        )
                        params['signal'] = col3.number_input(
                            f"{strat_name} 信号线",
                            min_value=1,
                            max_value=30,
                            value=9,
                            key=f"{strat_name}_sig",
                        )
                    elif strat_name == "布林带突破":
                        col1, col2 = st.columns(2)
                        params['bb_period'] = col1.number_input(
                            f"{strat_name} 周期",
                            min_value=5,
                            max_value=100,
                            value=20,
                            key=f"{strat_name}_period",
                        )
                        params['bb_std'] = col2.number_input(
                            f"{strat_name} 标准差倍数",
                            min_value=1,
                            max_value=5,
                            value=2,
                            key=f"{strat_name}_std",
                        )

                    strategy_instances.append(create_strategy(strat_name, params))

    # 回测参数
    st.sidebar.header("回测设置")
    initial_capital = st.sidebar.number_input("初始资金 (USDT)", min_value=1000, value=10000, step=1000)
    slippage = st.sidebar.number_input("滑点 (基点)", min_value=0, max_value=100, value=10, step=1) / 10000  # 1基点=0.01%
    commission = st.sidebar.number_input("手续费 (基点)", min_value=0, max_value=100, value=5, step=1) / 10000

    run_btn = st.sidebar.button("🚀 运行回测", type="primary")

    # 主区域显示
    if run_btn:
        if mode == "自定义组合" and len(strategy_instances) == 0:
            st.error("请至少选择两个策略进行组合")
            st.stop()

        with st.spinner("回测进行中..."):
            # 生成信号
            if mode == "自定义组合":
                # 使用组合策略包装所有子策略
                combo_params = {'strategies': strategy_instances}
                combo = CombinedStrategy(combo_params)
                signals = combo.generate_signals(df)
            else:
                signals = strategy_instances[0].generate_signals(df)

            # 执行回测
            results = backtest(df, signals, initial_capital, slippage, commission)

            # 显示绩效指标
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("总收益率", f"{results['total_return']:.2f}%")
            col2.metric("交易次数", results['total_trades'])
            col3.metric("胜率", f"{results['win_rate']:.2f}%")
            col4.metric("平均盈亏", f"{results['avg_pnl']:.2f} USDT")
            col5.metric("最大回撤", f"{results['max_drawdown']:.2f}%")

            # 绘制K线图与信号
            fig = make_subplots(
                rows=3,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.02,
                row_heights=[0.6, 0.2, 0.2],
                subplot_titles=("价格与信号", "成交量", "权益曲线"),
            )

            # K线图
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name="K线",
                ),
                row=1,
                col=1,
            )

            # 买入信号
            buy_idx = signals[signals == 1].index
            if len(buy_idx) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=buy_idx,
                        y=df.loc[buy_idx, 'low'] * 0.995,
                        mode='markers',
                        marker=dict(symbol='triangle-up', size=10, color='green'),
                        name="买入信号",
                    ),
                    row=1,
                    col=1,
                )

            # 卖出信号
            sell_idx = signals[signals == -1].index
            if len(sell_idx) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=sell_idx,
                        y=df.loc[sell_idx, 'high'] * 1.005,
                        mode='markers',
                        marker=dict(symbol='triangle-down', size=10, color='red'),
                        name="卖出信号",
                    ),
                    row=1,
                    col=1,
                )

            # 成交量
            colors = ['red' if df['close'].iloc[i] < df['open'].iloc[i] else 'green' for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=colors, name="成交量"), row=2, col=1)

            # 权益曲线
            equity_series = pd.Series(results['equity_curve'], index=df.index[: len(results['equity_curve'])])
            fig.add_trace(
                go.Scatter(x=equity_series.index, y=equity_series, mode='lines', name="权益", line=dict(color='blue')),
                row=3,
                col=1,
            )

            fig.update_layout(height=900, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # 显示交易明细
            if results['trades']:
                trades_df = pd.DataFrame(results['trades'])
                trades_df['entry_time'] = trades_df['entry_time'].dt.strftime('%Y-%m-%d %H:%M')
                trades_df['exit_time'] = trades_df['exit_time'].dt.strftime('%Y-%m-%d %H:%M')
                trades_df['pnl'] = trades_df['pnl'].round(2)
                trades_df = trades_df[['entry_time', 'exit_time', 'type', 'entry_price', 'exit_price', 'pnl']]
                st.subheader("交易明细")
                st.dataframe(trades_df, use_container_width=True)
            else:
                st.info("没有产生任何交易信号")
    else:
        # 默认显示最近500根K线
        st.subheader("数据预览")
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df.index[-500:],
                    open=df['open'][-500:],
                    high=df['high'][-500:],
                    low=df['low'][-500:],
                    close=df['close'][-500:],
                    name="K线",
                )
            ]
        )
        fig.update_layout(height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            """
        ### 使用说明
        - 在左侧上传CSV文件或使用默认数据。
        - 选择策略模式并调整参数。
        - 点击“运行回测”查看历史表现。
        - K线图上绿色三角为买入信号，红色三角为卖出信号。
        - 回测结果包括收益率、交易次数、胜率、最大回撤等。
        - **重要提示**：本系统仅提供历史回测信号，不构成投资建议。
        """
        )


if __name__ == "__main__":
    main()
