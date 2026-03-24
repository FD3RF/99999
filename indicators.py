# indicators.py
import pandas as pd
import numpy as np
from config import *

def calculate_macd(df):
    """计算MACD指标"""
    exp12 = df["close"].ewm(span=MACD_FAST, adjust=False).mean()
    exp26 = df["close"].ewm(span=MACD_SLOW, adjust=False).mean()
    df["dif"] = exp12 - exp26
    df["dea"] = df["dif"].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df["macd_hist"] = df["dif"] - df["dea"]
    df["hist_color"] = np.where(df["macd_hist"] > 0, "red", "green")
    df["above_zero"] = df["dif"] > 0
    df["golden_cross"] = (df["dif"] > df["dea"]) & (df["dif"].shift(1) <= df["dea"].shift(1))
    df["death_cross"] = (df["dif"] < df["dea"]) & (df["dif"].shift(1) >= df["dea"].shift(1))
    return df

def calculate_volume_metrics(df):
    # 成交量指标 - 修复：处理NaN和除以0
    df["volume_ma20"] = df["volume"].rolling(window=VOLUME_MA_PERIOD, min_periods=1).mean()
    # 修复：避免除以0，使用绝对最小值而非相对比例
    min_volume = max(df["volume_ma20"].max() * 0.001, 1e-10)  # 确保最小值不为0
    df["volume_ratio"] = df["volume"] / df["volume_ma20"].clip(lower=min_volume)
    df["volume_ratio"] = df["volume_ratio"].fillna(1.0)  # 填充NaN为1.0
    conditions = [
        df["volume_ratio"] >= VOLUME_RATIO_PANIC,
        df["volume_ratio"] >= VOLUME_RATIO_SIGNIFICANT,
        df["volume_ratio"] >= VOLUME_RATIO_MODERATE,
        df["volume_ratio"] < VOLUME_RATIO_SHRINK_50,
        df["volume_ratio"] < VOLUME_RATIO_SHRINK_60
    ]
    choices = ["巨量", "显著放量", "温和放量", "极度缩量", "一般缩量"]
    df["volume_status"] = np.select(conditions, choices, default="正常")
    return df

def find_swing_points(df, window=SWING_WINDOW):
    """波段高低点检测 - 修复：返回新DataFrame避免修改原始数据"""
    df = df.copy()  # 修复：创建副本避免修改原始DataFrame
    df = df.reset_index(drop=True)  # 重置索引确保位置索引正确
    df["swing_high"] = False
    df["swing_low"] = False
    for i in range(window, len(df) - window):
        if df["high"].iloc[i] == df["high"].iloc[i-window:i+window+1].max():
            df.loc[i, "swing_high"] = True
        if df["low"].iloc[i] == df["low"].iloc[i-window:i+window+1].min():
            df.loc[i, "swing_low"] = True
    return df

def calculate_support_resistance(df, lookback=20):
    """计算支撑位和压力位"""
    recent_highs = df[df["swing_high"]]["high"].tail(3)
    recent_lows = df[df["swing_low"]]["low"].tail(3)
    
    resistance = recent_highs.mean() if len(recent_highs) > 0 else df["high"].tail(lookback).max()
    support = recent_lows.mean() if len(recent_lows) > 0 else df["low"].tail(lookback).min()
    
    return support, resistance

def identify_candlestick_patterns(df):
    """识别K线形态"""
    df["body"] = abs(df["close"] - df["open"])
    df["upper_shadow"] = df["high"] - df[["close", "open"]].max(axis=1)
    df["lower_shadow"] = df[["close", "open"]].min(axis=1) - df["low"]

    # 十字星 - 修复：避免avg_body为0导致全为十字星
    avg_body_nonzero = df["body"].rolling(window=10, min_periods=1).mean().replace(0, np.nan)
    avg_body_nonzero = avg_body_nonzero.fillna(df["body"].abs().mean())  # 填充为全局平均
    df["doji"] = df["body"] <= avg_body_nonzero * DOJI_RATIO
    df["doji"] = df["doji"].fillna(False)
    # 锤子线 - 修复：阳线锤子也有效，修复括号优先级
    df["hammer"] = (
        (df["lower_shadow"] >= df["body"].abs() * LONG_SHADOW_RATIO) &
        (df["upper_shadow"] <= df["body"].abs() * 0.3) &
        (df["lower_shadow"] >= (df["high"] - df[["open", "close"]].max(axis=1)) * 2)  # 修复：括号位置
    )
    df["long_lower_shadow"] = df["lower_shadow"] >= df["body"] * LONG_SHADOW_RATIO
    df["piercing"] = (
        (df["close"] > df["open"]) &
        (df["close"].shift(1) < df["open"].shift(1)) &
        (df["open"] < df["low"].shift(1)) &
        (df["close"] > (df["open"].shift(1) + df["close"].shift(1)) / 2)
    )

    # 见顶反转
    df["shooting_star"] = (
        (df["close"] > df["open"].shift(1)) &
        (df["upper_shadow"] >= df["body"] * LONG_SHADOW_RATIO) &
        (df["lower_shadow"] <= df["body"] * 0.3)
    )
    df["gravestone"] = (df["upper_shadow"] > 0) & (df["body"] == 0) & (df["lower_shadow"] == 0)
    df["long_upper_shadow"] = df["upper_shadow"] >= df["body"] * LONG_SHADOW_RATIO
    df["dark_cloud"] = (
        (df["close"] < df["open"]) &
        (df["close"].shift(1) > df["open"].shift(1)) &
        (df["open"] > df["high"].shift(1)) &
        (df["close"] < (df["open"].shift(1) + df["close"].shift(1)) / 2)
    )

    # 持续形态 - 使用同样的 avg_body_nonzero
    df["big_bull"] = (
        (df["close"] > df["open"]) &
        (df["body"] > avg_body_nonzero * 1.5) &
        (df["upper_shadow"] < df["body"] * 0.1)
    )
    df["big_bear"] = (
        (df["close"] < df["open"]) &
        (df["body"] > avg_body_nonzero * 1.5) &
        (df["lower_shadow"] < df["body"] * 0.1)
    )

    # 吞没形态
    df["bullish_engulfing"] = (
        (df["close"] > df["open"]) &
        (df["close"].shift(1) < df["open"].shift(1)) &
        (df["close"] > df["open"].shift(1)) &
        (df["open"] < df["close"].shift(1))
    )
    df["bearish_engulfing"] = (
        (df["close"] < df["open"]) &
        (df["close"].shift(1) > df["open"].shift(1)) &
        (df["close"] < df["open"].shift(1)) &
        (df["open"] > df["close"].shift(1))
    )
    return df
