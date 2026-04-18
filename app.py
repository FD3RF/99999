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
    # 避免除零：当无下跌时 RSI 应趋近 100，而不是 NaN
    rs = avg_gain / avg_loss.replace(0, np.finfo(float).eps)
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
        condition_buy = (rsi > oversold) & (rsi.shift() <= oversold)
        signals[condition_buy] = 1
        # 从超买区域向下突破卖出
        condition_sell = (rsi < overbought) & (rsi.shift() >= overbought)
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


class ProTraderEntryStrategy(SignalStrategy):
    """顶级交易员多因子进场策略：趋势 + 回踩 + 动能 + 成交量 + 波动率过滤"""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        ema_fast_period = self.params.get('ema_fast', 21)
        ema_slow_period = self.params.get('ema_slow', 55)
        rsi_period = self.params.get('rsi_period', 14)
        rsi_mid = self.params.get('rsi_mid', 50)
        pullback_bps = self.params.get('pullback_bps', 20)  # 20bp = 0.2%
        vol_period = self.params.get('vol_period', 20)
        vol_multiplier = self.params.get('vol_multiplier', 1.2)
        atr_period = self.params.get('atr_period', 14)
        atr_min_pct = self.params.get('atr_min_pct', 0.10) / 100

        ema_fast = df['close'].ewm(span=ema_fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=ema_slow_period, adjust=False).mean()
        rsi = add_rsi(df, rsi_period)
        vol_ma = df['volume'].rolling(vol_period).mean()
        atr = add_atr(df, atr_period)
        atr_pct = atr / df['close']

        pullback_ratio = pullback_bps / 10000
        trend_up = ema_fast > ema_slow
        trend_down = ema_fast < ema_slow
        pullback_long = (df['low'] <= ema_fast * (1 + pullback_ratio)) & (df['close'] >= ema_slow)
        pullback_short = (df['high'] >= ema_fast * (1 - pullback_ratio)) & (df['close'] <= ema_slow)
        momentum_long = rsi > rsi_mid
        momentum_short = rsi < rsi_mid
        volume_confirm = df['volume'] >= vol_ma * vol_multiplier
        volatility_ok = atr_pct >= atr_min_pct

        signals = pd.Series(0, index=df.index)
        long_entry = trend_up & pullback_long & momentum_long & volume_confirm & volatility_ok
        short_entry = trend_down & pullback_short & momentum_short & volume_confirm & volatility_ok
        signals[long_entry] = 1
        signals[short_entry] = -1
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
        "顶级交易员多因子进场": ProTraderEntryStrategy,
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


def build_entry_plan(strategy_name: str, params: Dict[str, Any]) -> List[str]:
    """返回策略进场逻辑说明，便于用户理解交易计划。"""
    if strategy_name == "顶级交易员多因子进场":
        return [
            f"趋势过滤：EMA{params.get('ema_fast', 21)} 与 EMA{params.get('ema_slow', 55)} 判定多空方向（快线在慢线上方只做多，下方只做空）。",
            f"回踩确认：价格回踩到快线附近（容差 {params.get('pullback_bps', 20)}bp）后才允许进场，避免追涨杀跌。",
            f"动能触发：RSI({params.get('rsi_period', 14)}) 上穿/下穿 {params.get('rsi_mid', 50)} 作为真正触发。",
            f"成交量确认：当前成交量需高于 {params.get('vol_period', 20)} 周期均量的 {params.get('vol_multiplier', 1.2):.2f} 倍。",
            f"波动率过滤：ATR({params.get('atr_period', 14)})/Close 需高于 {params.get('atr_min_pct', 0.10):.2f}% 以过滤无效震荡。",
        ]

    return [
        "该策略为事件触发型信号：出现 1/-1 代表新进场信号，0 表示无新信号。",
        "回测引擎会持仓到反向信号出现，不会因 1->0 或 -1->0 提前平仓。",
    ]


def run_module_diagnostics(df: pd.DataFrame, signals: pd.Series, results: Dict[str, Any]) -> Dict[str, Any]:
    """按模块输出测试排查信息：数据、信号、回测、绘图一致性。"""
    price_cols = ['open', 'high', 'low', 'close', 'volume']
    null_counts = df[price_cols].isna().sum().to_dict()
    invalid_ohlc = ((df['high'] < df[['open', 'close']].max(axis=1)) | (df['low'] > df[['open', 'close']].min(axis=1))).sum()
    duplicated_index = int(df.index.duplicated().sum())

    signal_counts = {
        'buy': int((signals == 1).sum()),
        'sell': int((signals == -1).sum()),
        'neutral': int((signals == 0).sum()),
    }
    flips = int((((signals == 1) & (signals.shift(1) == -1)) | ((signals == -1) & (signals.shift(1) == 1))).sum())

    equity_len = len(results.get('equity_curve', []))
    df_len = len(df)
    trades_len = len(results.get('trades', []))
    equity_match = equity_len == df_len

    return {
        'data_quality': {
            'rows': df_len,
            'time_start': df.index.min(),
            'time_end': df.index.max(),
            'null_counts': null_counts,
            'invalid_ohlc_rows': int(invalid_ohlc),
            'duplicated_timestamps': duplicated_index,
        },
        'signal_quality': {
            'counts': signal_counts,
            'direct_flip_events': flips,
            'signal_coverage_pct': round((signal_counts['buy'] + signal_counts['sell']) / max(df_len, 1) * 100, 2),
        },
        'backtest_consistency': {
            'trades': trades_len,
            'equity_points': equity_len,
            'equity_matches_price_rows': equity_match,
            'final_capital': float(results.get('final_capital', 0.0)),
            'total_return_pct': float(results.get('total_return', 0.0)),
        },
    }


def calc_support_resistance(df: pd.DataFrame, window: int = 48) -> Tuple[float, float]:
    recent = df.tail(window)
    support = float(recent['low'].min())
    resistance = float(recent['high'].max())
    return support, resistance


def get_signal_text(latest_signal: float) -> str:
    if latest_signal == 1:
        return "🟢 多头信号触发：可按计划等待回踩确认后执行。"
    if latest_signal == -1:
        return "🔴 空头信号触发：可按计划等待反弹确认后执行。"
    return "⏳ 暂无信号，等待市场条件..."


def normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """统一字段定义：open, high, low, close, volume, timestamp。"""
    out = df.copy()
    if 'timestamp' not in out.columns:
        out['timestamp'] = out.index
    return out[['open', 'high', 'low', 'close', 'volume', 'timestamp']].copy()


def add_candle_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['body'] = (out['close'] - out['open']).abs()
    out['upper'] = out['high'] - out[['open', 'close']].max(axis=1)
    out['lower_len'] = (out[['open', 'close']].min(axis=1) - out['low']).abs()
    out['range'] = (out['high'] - out['low']).replace(0, np.finfo(float).eps)
    return out


def build_key_levels(df: pd.DataFrame, lookback: int = 100) -> List[float]:
    recent = df.tail(lookback)
    if recent.empty:
        return []
    levels = [
        float(recent['low'].min()),
        float(recent['high'].max()),
        float(recent['close'].quantile(0.25)),
        float(recent['close'].quantile(0.50)),
        float(recent['close'].quantile(0.75)),
    ]
    return sorted(set(round(x, 4) for x in levels))


def is_near_key_level(price: float, key_levels: List[float], tol_pct: float = 0.003) -> Tuple[bool, Optional[float]]:
    if not key_levels:
        return False, None
    best = min(key_levels, key=lambda x: abs(price - x) / max(x, np.finfo(float).eps))
    dist = abs(price - best) / max(best, np.finfo(float).eps)
    return dist <= tol_pct, best


def volume_ratio(series: pd.Series, idx: int, window: int = 5) -> float:
    if idx <= 0:
        return 0.0
    start = max(0, idx - window)
    hist = series.iloc[start:idx]
    if hist.empty or hist.mean() <= 0:
        return 0.0
    return float(series.iloc[idx] / hist.mean())


def is_btc_volume_selloff(btc_1h: Optional[pd.DataFrame]) -> bool:
    if btc_1h is None or len(btc_1h) < 6:
        return False
    b = btc_1h.copy()
    last = b.iloc[-1]
    avg_vol = b['volume'].iloc[-6:-1].mean()
    bearish = last['close'] < last['open']
    drop_big = last['close'] <= last['open'] * (1 - 0.01)
    vol_big = avg_vol > 0 and last['volume'] >= 1.5 * avg_vol
    return bool(bearish and drop_big and vol_big)


def detect_latest_pattern_signal(
    eth_15m: pd.DataFrame,
    rsi_period: int = 14,
    key_level_tol: float = 0.003,
    level_lookback: int = 100,
    btc_1h: Optional[pd.DataFrame] = None,
) -> Optional[Dict[str, Any]]:
    """
    在最新一根K线上识别形态信号，返回统一推送格式。
    """
    if len(eth_15m) < 6:
        return None

    df = add_candle_features(normalize_ohlcv_columns(eth_15m))
    df['rsi'] = add_rsi(df, rsi_period)
    key_levels = build_key_levels(df, lookback=level_lookback)
    i = len(df) - 1
    c0 = df.iloc[i]
    c1 = df.iloc[i - 1]
    c2 = df.iloc[i - 2]
    c3 = df.iloc[i - 3]
    vol_ratio_now = volume_ratio(df['volume'], i, window=5)
    vol_ok = vol_ratio_now >= 1.2
    btc_filter_on = is_btc_volume_selloff(btc_1h)
    near_key, key = is_near_key_level(float(c0['close']), key_levels, tol_pct=key_level_tol)

    def pack(title: str, pattern: str, side: str, sl: float, note: str, rsi_th: Optional[float] = None) -> Dict[str, Any]:
        filtered = btc_filter_on and side == 'long'
        return {
            'title': title,
            'time': str(c0['timestamp']),
            'pattern': pattern,
            'side': side,
            'key_level': key,
            'close': float(c0['close']),
            'rsi14': float(c0['rsi']) if pd.notna(c0['rsi']) else None,
            'volume_ratio': vol_ratio_now,
            'sl': float(sl),
            'btc_filter': "放量杀跌(已过滤多头)" if filtered else "正常",
            'filtered': filtered,
            'note': note,
            'rsi_rule': rsi_th,
        }

    # 1) 看涨吞没
    bullish_engulfing = (
        c1['close'] < c1['open']
        and c0['close'] > c0['open']
        and c0['open'] <= c1['close']
        and c0['close'] >= c1['open']
        and pd.notna(c0['rsi'])
        and c0['rsi'] < 30
        and vol_ok
        and near_key
    )
    if bullish_engulfing:
        return pack("[ETH 15m] 看涨吞没（关键位附近）", "Bullish Engulfing", "long", min(c1['low'], c0['low']), "阳包阴 + RSI低位 + 放量确认。", 30)

    # 2) 锤子线
    downtrend = c1['close'] < c2['close'] < c3['close']
    hammer = (
        c0['body'] > 0
        and c0['lower_len'] / c0['body'] >= 2
        and c0['upper'] <= 0.25 * c0['body']
        and downtrend
        and near_key
        and vol_ok
    )
    if hammer:
        return pack("[ETH 15m] 锤子线反转（关键位附近）", "Hammer", "long", c0['low'], "下影长于实体且处于下跌后，存在反转概率。")

    # 3) 早晨之星
    b2, b1, b0 = c2['body'], c1['body'], c0['body']
    avg_body = df['body'].iloc[max(0, i - 20):i].mean()
    morning_star = (
        c2['close'] < c2['open']
        and b2 > 1.2 * avg_body
        and b1 <= 0.5 * min(b2, max(b0, np.finfo(float).eps))
        and c0['close'] > c0['open']
        and c0['close'] >= (c2['open'] + c2['close']) / 2
        and pd.notna(c0['rsi'])
        and c0['rsi'] <= 35
        and vol_ok
        and near_key
    )
    if morning_star:
        return pack("[ETH 15m] 早晨之星（关键位附近）", "Morning Star", "long", min(c2['low'], c1['low'], c0['low']), "三K反转结构完整，第三根放量回收。", 35)

    # 3.1) 白三兵
    c_2, c_1, c_0 = c2, c1, c0
    avg_body_mid = df['body'].iloc[max(0, i - 30):i].mean()
    three_white_soldiers = (
        c_2['close'] > c_2['open']
        and c_1['close'] > c_1['open']
        and c_0['close'] > c_0['open']
        and c_2['close'] < c_1['close'] < c_0['close']
        and c_1['open'] <= c_2['close']
        and c_0['open'] <= c_1['close']
        and c_2['body'] <= 2 * avg_body_mid
        and c_1['body'] <= 2 * avg_body_mid
        and c_0['body'] <= 2 * avg_body_mid
        and pd.notna(c0['rsi'])
        and c0['rsi'] < 60
        and near_key
        and vol_ok
    )
    if three_white_soldiers:
        return pack("[ETH 15m] 白三兵（关键位附近）", "Three White Soldiers", "long", c_2['low'], "三连阳抬高且量能确认。", 60)

    # 3.2) 上升三法（-4,-3,-2,-1,0）
    if i >= 4:
        k4 = df.iloc[i - 4]
        k3 = df.iloc[i - 3]
        k2 = df.iloc[i - 2]
        k1 = df.iloc[i - 1]
        avg_body_long = df['body'].iloc[max(0, i - 40):i].mean()
        rising_three_methods = (
            k4['close'] > k4['open']
            and k4['body'] > avg_body_long
            and c0['close'] > c0['open']
            and c0['close'] > k4['high']
            and max(k3['high'], k2['high'], k1['high']) <= k4['high']
            and min(k3['low'], k2['low'], k1['low']) >= k4['low']
            and volume_ratio(df['volume'], i - 4, 5) >= 1.2
            and vol_ok
            and near_key
        )
        if rising_three_methods:
            return pack("[ETH 15m] 上升三法（中继）", "Rising Three Methods", "long", k4['low'], "大阳-整理-再突破结构成立。")

    # 4) 看跌吞没
    bearish_engulfing = (
        c1['close'] > c1['open']
        and c0['close'] < c0['open']
        and c0['open'] >= c1['close']
        and c0['close'] <= c1['open']
        and pd.notna(c0['rsi'])
        and c0['rsi'] > 70
        and vol_ok
        and near_key
    )
    if bearish_engulfing:
        return pack("[ETH 15m] 看跌吞没（关键位附近）", "Bearish Engulfing", "short", max(c1['high'], c0['high']), "阴包阳 + RSI高位 + 放量确认。", 70)

    # 4.1) 黄昏之星
    evening_star = (
        c2['close'] > c2['open']
        and b2 > 1.2 * avg_body
        and b1 <= 0.5 * min(b2, max(b0, np.finfo(float).eps))
        and c0['close'] < c0['open']
        and c0['close'] <= (c2['open'] + c2['close']) / 2
        and pd.notna(c0['rsi'])
        and c0['rsi'] >= 60
        and vol_ok
        and near_key
    )
    if evening_star:
        return pack("[ETH 15m] 黄昏之星（关键位附近）", "Evening Star", "short", max(c2['high'], c1['high'], c0['high']), "三K顶部反转结构完整。", 60)

    # 5) 流星线
    uptrend = c1['close'] > c2['close'] > c3['close']
    shooting_star = (
        c0['body'] > 0
        and c0['upper'] / c0['body'] >= 2
        and c0['lower_len'] <= 0.25 * c0['body']
        and uptrend
        and pd.notna(c0['rsi'])
        and c0['rsi'] >= 60
        and near_key
    )
    if shooting_star:
        return pack("[ETH 15m] 流星线（关键位附近）", "Shooting Star", "short", c0['high'], "高位上影过长，潜在顶部反转。", 60)

    # 5.1) 三只乌鸦
    in_body_1 = min(c2['open'], c2['close']) <= c1['open'] <= max(c2['open'], c2['close'])
    in_body_0 = min(c1['open'], c1['close']) <= c0['open'] <= max(c1['open'], c1['close'])
    three_black_crows = (
        c2['close'] < c2['open']
        and c1['close'] < c1['open']
        and c0['close'] < c0['open']
        and c2['close'] > c1['close'] > c0['close']
        and in_body_1
        and in_body_0
        and vol_ok
        and near_key
    )
    if three_black_crows:
        return pack("[ETH 15m] 三只乌鸦（关键位附近）", "Three Black Crows", "short", max(c2['high'], c1['high'], c0['high']), "三连阴下行且开盘落在前实体内。")

    # 6) 十字星预警（不下单）
    doji = c0['body'] <= 0.1 * c0['range'] and near_key
    if doji:
        return pack(
            "[ETH 15m] 十字星预警（关键位附近）",
            "Doji Warning",
            "alert",
            c0['low'],
            "仅预警：关键位附近可能变盘，等待下一根确认。",
        )

    return None

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
    # 数据保护
    if df.empty:
        return {
            'initial_capital': initial_capital,
            'final_capital': initial_capital,
            'total_return': 0.0,
            'total_trades': 0,
            'win_rate': 0.0,
            'avg_pnl': 0.0,
            'max_drawdown': 0.0,
            'trades': [],
            'equity_curve': [],
        }

    # 对齐信号索引并确保信号只有 -1,0,1
    sig = signals.reindex(df.index).fillna(0).clip(-1, 1).copy()

    trades = []
    position = 0  # 当前持仓：1 多头，-1 空头，0 空仓
    entry_price = 0.0
    entry_time = None
    capital = initial_capital
    equity_curve = [capital]

    for i in range(1, len(sig)):
        current_signal = sig.iloc[i]
        current_price = df['close'].iloc[i]
        current_time = df.index[i]

        # 仅在出现反向信号时平仓，避免 1 -> 0 或 -1 -> 0 的事件信号导致提前平仓
        close_position = (position == 1 and current_signal == -1) or (position == -1 and current_signal == 1)
        if close_position:
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

        # 空仓时，仅在明确的开仓信号（1 / -1）出现时开仓
        if position == 0:
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
        # 保持权益曲线长度与K线数量一致，便于对齐绘图索引
        equity_curve[-1] = capital

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
    st.title("📊 以太坊5分钟合约 · AI智能交易系统")
    st.markdown("基于历史K线回测 + 交易计划 + 模块排查（仅供研究，不构成投资建议）")

    # 侧边栏：数据上传
    st.sidebar.header("数据源")
    uploaded_file = st.sidebar.file_uploader("上传CSV文件", type=['csv'])

    # 加载数据
    df = load_data(uploaded_file)
    if df is None:
        st.stop()
    btc_file = st.sidebar.file_uploader("上传BTC 1h CSV(可选,用于联动过滤)", type=['csv'])
    btc_df = load_data(btc_file) if btc_file is not None else None

    # 显示数据概览
    with st.expander("数据概览"):
        st.write(f"数据时间范围: {df.index.min()} 至 {df.index.max()}")
        st.write(f"总数据量: {len(df)} 条")
        st.dataframe(df.head())

    # 系统配置
    st.sidebar.header("⚙️ 系统配置")
    refresh_sec = st.sidebar.slider("刷新频率(秒)", min_value=10, max_value=120, value=10, step=5)
    point_value = st.sidebar.number_input("合约点值(U/点)", min_value=1, max_value=1000, value=10, step=1)
    total_capital_cfg = st.sidebar.number_input("总资金(U)", min_value=1000, max_value=10000000, value=10000, step=1000)
    risk_pct_cfg = st.sidebar.slider("单笔风险(%)", min_value=0.50, max_value=5.00, value=1.00, step=0.25)
    st.sidebar.markdown("**监控定义**")
    monitor_symbol = st.sidebar.text_input("标的", value="ETH/USDT")
    monitor_tf = st.sidebar.selectbox("监控周期", ["15m"], index=0)
    btc_filter_tf = st.sidebar.selectbox("BTC联动周期", ["1h"], index=0)
    key_tol = st.sidebar.slider("关键位接近阈值(%)", min_value=0.10, max_value=1.00, value=0.30, step=0.05) / 100

    st.sidebar.header("🔊 语音播报设置")
    voice_enabled = st.sidebar.checkbox("开启语音播报", value=False)
    voice_style = st.sidebar.selectbox("播报风格", ["简洁", "标准", "激进"])

    st.sidebar.header("📜 交易口诀")
    long_mantra = st.sidebar.text_input("做多口诀", value="顺势而为，回踩确认，放量再进。")
    short_mantra = st.sidebar.text_input("做空口诀", value="逆势不空，反弹承压，放量再空。")

    # 侧边栏策略配置
    st.sidebar.header("策略配置")

    # 策略选择模式：单一策略 或 自定义组合
    mode = st.sidebar.radio("选择模式", ["单一策略", "自定义组合"])

    strategy_instances = []
    strategy_plan_context: List[Tuple[str, Dict[str, Any]]] = []

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
        elif selected == "顶级交易员多因子进场":
            col1, col2 = st.sidebar.columns(2)
            params['ema_fast'] = col1.number_input("EMA快线", min_value=2, max_value=80, value=21)
            params['ema_slow'] = col2.number_input("EMA慢线", min_value=10, max_value=200, value=55)
            col3, col4 = st.sidebar.columns(2)
            params['rsi_period'] = col3.number_input("RSI周期", min_value=2, max_value=50, value=14)
            params['rsi_mid'] = col4.number_input("RSI中轴", min_value=40, max_value=60, value=50)
            col5, col6 = st.sidebar.columns(2)
            params['pullback_bps'] = col5.number_input("回踩容差(bps)", min_value=0, max_value=100, value=20)
            params['vol_period'] = col6.number_input("成交量均线周期", min_value=5, max_value=100, value=20)
            col7, col8 = st.sidebar.columns(2)
            params['vol_multiplier'] = col7.number_input("放量倍数", min_value=0.5, max_value=5.0, value=1.2, step=0.1)
            params['atr_period'] = col8.number_input("ATR周期", min_value=2, max_value=50, value=14)
            params['atr_min_pct'] = st.sidebar.number_input("最小ATR占比(%)", min_value=0.01, max_value=2.0, value=0.10, step=0.01)

        strategy_instances.append(create_strategy(selected, params))
        strategy_plan_context.append((selected, params.copy()))

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
                    elif strat_name == "顶级交易员多因子进场":
                        col1, col2 = st.columns(2)
                        params['ema_fast'] = col1.number_input(
                            f"{strat_name} EMA快线",
                            min_value=2,
                            max_value=80,
                            value=21,
                            key=f"{strat_name}_ema_fast",
                        )
                        params['ema_slow'] = col2.number_input(
                            f"{strat_name} EMA慢线",
                            min_value=10,
                            max_value=200,
                            value=55,
                            key=f"{strat_name}_ema_slow",
                        )
                        col3, col4 = st.columns(2)
                        params['rsi_period'] = col3.number_input(
                            f"{strat_name} RSI周期",
                            min_value=2,
                            max_value=50,
                            value=14,
                            key=f"{strat_name}_rsi_period",
                        )
                        params['rsi_mid'] = col4.number_input(
                            f"{strat_name} RSI中轴",
                            min_value=40,
                            max_value=60,
                            value=50,
                            key=f"{strat_name}_rsi_mid",
                        )
                        col5, col6 = st.columns(2)
                        params['pullback_bps'] = col5.number_input(
                            f"{strat_name} 回踩容差(bps)",
                            min_value=0,
                            max_value=100,
                            value=20,
                            key=f"{strat_name}_pullback_bps",
                        )
                        params['vol_period'] = col6.number_input(
                            f"{strat_name} 成交量均线周期",
                            min_value=5,
                            max_value=100,
                            value=20,
                            key=f"{strat_name}_vol_period",
                        )
                        col7, col8 = st.columns(2)
                        params['vol_multiplier'] = col7.number_input(
                            f"{strat_name} 放量倍数",
                            min_value=0.5,
                            max_value=5.0,
                            value=1.2,
                            step=0.1,
                            key=f"{strat_name}_vol_multiplier",
                        )
                        params['atr_period'] = col8.number_input(
                            f"{strat_name} ATR周期",
                            min_value=2,
                            max_value=50,
                            value=14,
                            key=f"{strat_name}_atr_period",
                        )
                        params['atr_min_pct'] = st.number_input(
                            f"{strat_name} 最小ATR占比(%)",
                            min_value=0.01,
                            max_value=2.0,
                            value=0.10,
                            step=0.01,
                            key=f"{strat_name}_atr_min_pct",
                        )

                    strategy_instances.append(create_strategy(strat_name, params))
                    strategy_plan_context.append((strat_name, params.copy()))

    # 回测参数
    st.sidebar.header("回测设置")
    initial_capital = st.sidebar.number_input("初始资金 (USDT)", min_value=1000, value=int(total_capital_cfg), step=1000)
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
            diagnostics = run_module_diagnostics(df, signals, results)

            # 显示绩效指标
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("总收益率", f"{results['total_return']:.2f}%")
            col2.metric("交易次数", results['total_trades'])
            col3.metric("胜率", f"{results['win_rate']:.2f}%")
            col4.metric("平均盈亏", f"{results['avg_pnl']:.2f} USDT")
            col5.metric("最大回撤", f"{results['max_drawdown']:.2f}%")

            latest_close = float(df['close'].iloc[-1])
            prev_close = float(df['close'].iloc[-2]) if len(df) > 1 else latest_close
            px_chg = latest_close - prev_close
            px_chg_pct = (px_chg / prev_close * 100) if prev_close != 0 else 0.0
            support, resistance = calc_support_resistance(df)
            latest_signal = float(signals.iloc[-1])
            signal_text = get_signal_text(latest_signal)
            pattern_signal = detect_latest_pattern_signal(
                eth_15m=df,
                rsi_period=14,
                key_level_tol=key_tol,
                level_lookback=100,
                btc_1h=btc_df,
            )

            st.markdown(
                f"**{monitor_symbol}：{latest_close:.2f} 美元（{px_chg:+.2f} / {px_chg_pct:+.2f}%）**  \n"
                f"🔵 支撑位: ${support:.2f}  \n"
                f"🔴 压力位: ${resistance:.2f}"
            )

            system_col1, system_col2, system_col3 = st.columns(3)
            system_col1.info(f"🎯 AI交易信号\n\n{signal_text}")
            if latest_signal == 1:
                pos_text = f"建议关注多头仓位 | 单笔风险 {risk_pct_cfg:.2f}%"
            elif latest_signal == -1:
                pos_text = f"建议关注空头仓位 | 单笔风险 {risk_pct_cfg:.2f}%"
            else:
                pos_text = "等待信号..."
            system_col2.info(f"💼 仓位\n\n{pos_text}")
            system_col3.info(
                "📡 系统\n\n"
                f"更新: {datetime.utcnow().strftime('%H:%M:%S')}  \n"
                f"K线: {len(df)}  \n"
                f"监控: {monitor_tf} / BTC {btc_filter_tf}  \n"
                f"刷新: {refresh_sec}s  \n"
                f"点值: {point_value} U/点"
            )

            st.subheader("📨 形态推送（统一格式）")
            if pattern_signal is None:
                st.info("当前未触发满足关键位 + RSI + 量能 + 大盘过滤的形态信号。")
            else:
                st.markdown(f"**标题：{pattern_signal['title']}**")
                st.markdown(
                    f"- 触发时间：{pattern_signal['time']}\n"
                    f"- 形态类型：{pattern_signal['pattern']}\n"
                    f"- 当前收盘价：{pattern_signal['close']:.2f}\n"
                    f"- 关键位：{pattern_signal['key_level']}\n"
                    f"- RSI(14)：{pattern_signal['rsi14']}\n"
                    f"- 量能倍数：{pattern_signal['volume_ratio']:.2f}x\n"
                    f"- 止损价：**{pattern_signal['sl']:.2f}**\n"
                    f"- 大盘过滤结果：{pattern_signal['btc_filter']}\n"
                    f"- 备注：{pattern_signal['note']}"
                )
                if pattern_signal['filtered']:
                    st.warning("该多头信号已被 BTC 1h 放量杀跌过滤，建议观望。")

            tab_dashboard, tab_diagnostics, tab_trades = st.tabs(["📈 回测看板", "🧪 模块排查", "📒 交易明细"])

            with tab_dashboard:
                st.caption(f"🔊 语音播报：{'开启' if voice_enabled else '关闭'}（{voice_style}）")
                st.subheader("进场交易计划")
                if strategy_plan_context:
                    for idx, (plan_name, plan_params) in enumerate(strategy_plan_context, start=1):
                        st.markdown(f"**{idx}. {plan_name}**")
                        for rule in build_entry_plan(plan_name, plan_params):
                            st.markdown(f"- {rule}")
                st.markdown(f"**做多口诀：** {long_mantra}")
                st.markdown(f"**做空口诀：** {short_mantra}")

                st.markdown("#### K线图优化设置")
                chart_cols = st.columns(3)
                slider_max = min(len(df), 5000)
                slider_min = 1 if slider_max < 200 else 200
                slider_step = 1 if slider_max < 200 else 100
                max_bars_default = min(slider_max, 1200)
                max_bars = chart_cols[0].slider(
                    "显示最近K线数量",
                    min_value=slider_min,
                    max_value=slider_max,
                    value=max_bars_default,
                    step=slider_step,
                )
                show_ema = chart_cols[1].checkbox("叠加EMA21/EMA55", value=True)
                marker_size = chart_cols[2].slider("信号标记大小", min_value=6, max_value=16, value=10)

                plot_df = df.tail(max_bars).copy()
                plot_signals = signals.reindex(plot_df.index).fillna(0)

                # 绘制K线图与信号
                fig = make_subplots(
                rows=3,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.02,
                row_heights=[0.6, 0.2, 0.2],
                subplot_titles=("价格与信号", "成交量", "权益曲线"),
                )
                fig.add_trace(
                    go.Candlestick(
                        x=plot_df.index,
                        open=plot_df['open'],
                        high=plot_df['high'],
                        low=plot_df['low'],
                        close=plot_df['close'],
                        name="K线",
                        increasing_line_color="#00C853",
                        decreasing_line_color="#FF5252",
                    ),
                    row=1,
                    col=1,
                )

                if show_ema:
                    ema21 = plot_df['close'].ewm(span=21, adjust=False).mean()
                    ema55 = plot_df['close'].ewm(span=55, adjust=False).mean()
                    fig.add_trace(go.Scatter(x=plot_df.index, y=ema21, mode='lines', name="EMA21", line=dict(color="#4FC3F7", width=1.4)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=plot_df.index, y=ema55, mode='lines', name="EMA55", line=dict(color="#AB47BC", width=1.4)), row=1, col=1)

                # 买入信号
                buy_idx = plot_signals[plot_signals == 1].index
                if len(buy_idx) > 0:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_idx,
                            y=plot_df.loc[buy_idx, 'low'] * 0.995,
                            mode='markers',
                            marker=dict(symbol='triangle-up', size=marker_size, color='green'),
                            name="买入信号",
                        ),
                        row=1,
                        col=1,
                    )

                # 卖出信号
                sell_idx = plot_signals[plot_signals == -1].index
                if len(sell_idx) > 0:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_idx,
                            y=plot_df.loc[sell_idx, 'high'] * 1.005,
                            mode='markers',
                            marker=dict(symbol='triangle-down', size=marker_size, color='red'),
                            name="卖出信号",
                        ),
                        row=1,
                        col=1,
                    )

                # 成交量
                colors = ['#FF5252' if plot_df['close'].iloc[i] < plot_df['open'].iloc[i] else '#00C853' for i in range(len(plot_df))]
                fig.add_trace(go.Bar(x=plot_df.index, y=plot_df['volume'], marker_color=colors, name="成交量"), row=2, col=1)

                # 权益曲线（长度保护，避免索引与数值长度不一致）
                curve_values = results['equity_curve']
                if len(curve_values) <= len(df.index):
                    curve_index = df.index[: len(curve_values)]
                else:
                    extra_points = len(curve_values) - len(df.index)
                    curve_index = df.index.append(pd.DatetimeIndex([df.index[-1]] * extra_points))

                equity_series = pd.Series(curve_values, index=curve_index).reindex(plot_df.index).ffill().bfill()
                fig.add_trace(
                    go.Scatter(x=equity_series.index, y=equity_series, mode='lines', name="权益", line=dict(color='#1E88E5', width=2)),
                    row=3,
                    col=1,
                )

                fig.update_layout(
                    height=920,
                    xaxis_rangeslider_visible=False,
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                )
                fig.update_xaxes(showgrid=True, gridcolor="rgba(120,120,120,0.15)")
                fig.update_yaxes(showgrid=True, gridcolor="rgba(120,120,120,0.15)")
                st.plotly_chart(fig, use_container_width=True)

            with tab_diagnostics:
                st.subheader("模块化测试排查报告")
                data_q = diagnostics['data_quality']
                signal_q = diagnostics['signal_quality']
                bt_q = diagnostics['backtest_consistency']
                st.markdown("#### 1) 数据模块")
                st.json(data_q)
                st.markdown("#### 2) 信号模块")
                st.json(signal_q)
                st.markdown("#### 3) 回测模块")
                st.json(bt_q)
                if bt_q['equity_matches_price_rows']:
                    st.success("权益曲线点数与价格K线行数一致，绘图索引安全。")
                else:
                    st.error("权益曲线与价格数据长度不一致，请检查回测输出。")

            with tab_trades:
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
