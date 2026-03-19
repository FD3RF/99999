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
    """计算成交量指标"""
    df["volume_ma20"] = df["volume"].rolling(window=VOLUME_MA_PERIOD).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma20"]
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
    """识别波段高低点"""
    df["swing_high"] = False
    df["swing_low"] = False
    for i in range(window, len(df) - window):
        if df["high"].iloc[i] == max(df["high"].iloc[i-window:i+window+1]):
            df.loc[df.index[i], "swing_high"] = True
        if df["low"].iloc[i] == min(df["low"].iloc[i-window:i+window+1]):
            df.loc[df.index[i], "swing_low"] = True
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

    avg_body = df["body"].rolling(10).mean()

    # 见底反转
    df["hammer"] = (
        (df["close"] < df["open"].shift(1)) &
        (df["lower_shadow"] >= df["body"] * LONG_SHADOW_RATIO) &
        (df["upper_shadow"] <= df["body"] * 0.3)
    )
    df["doji"] = df["body"] < avg_body * 0.1
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

    # 持续形态
    df["big_bull"] = (
        (df["close"] > df["open"]) &
        (df["body"] > avg_body * 1.5) &
        (df["upper_shadow"] < df["body"] * 0.1)
    )
    df["big_bear"] = (
        (df["close"] < df["open"]) &
        (df["body"] > avg_body * 1.5) &
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
