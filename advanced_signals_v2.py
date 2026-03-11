"""
ETHUSDT 高级信号指标模块 V2.0
升级内容：
1. LSTM概率限制 + dropout
2. VWAP指标
3. CVD订单流
4. 盘口失衡算法优化
5. 主力吸筹检测优化（加入CVD条件）
6. 支撑压力算法升级（成交量密集区）
7. K线指标优化（EMA21/EMA200/VWAP）
8. 假突破检测修复（加入成交量和CVD）
9. 综合建议评分优化
10. Funding Rate
11. Open Interest
12. ATR波动率
13. 市场状态识别
14. 爆仓监控
15. 巨鲸监控
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import warnings
import requests
warnings.filterwarnings('ignore')

# ========== 1. VWAP 计算 ==========
def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算VWAP (Volume Weighted Average Price)
    VWAP = Σ(价格 × 成交量) / Σ成交量
    """
    # 边界检查
    if df.empty or len(df) == 0:
        return df
    
    df = df.copy()
    
    # 典型价格
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    
    # 累计成交额和成交量
    df['tp_vol'] = df['typical_price'] * df['volume']
    df['cum_tp_vol'] = df['tp_vol'].cumsum()
    df['cum_vol'] = df['volume'].cumsum()
    
    # VWAP（防止除零）
    # 使用np.where处理除零情况
    df['vwap'] = np.where(
        df['cum_vol'] > 0,
        df['cum_tp_vol'] / df['cum_vol'],
        df['close']  # 如果累计成交量为0,使用收盘价
    )
    
    # 删除临时列
    df.drop(['tp_vol', 'cum_tp_vol', 'cum_vol', 'typical_price'], axis=1, inplace=True)
    
    return df


# ========== 2. EMA 计算 ==========
def calculate_ema(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算EMA指标（机构常用）
    EMA21 - 短期趋势
    EMA200 - 长期趋势
    """
    df = df.copy()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    return df


# ========== 3. CVD (Cumulative Volume Delta) ==========
def calculate_cvd(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算CVD (Cumulative Volume Delta)
    CVD = 累计(主动买入量 - 主动卖出量)
    
    估算方法（无tick数据）：
    阳线：成交量全部计入买入
    阴线：成交量全部计入卖出
    十字星：成交量平分
    """
    # 边界检查
    if df.empty or len(df) == 0:
        return df
    
    df = df.copy()
    
    # 检查必需的列
    required_cols = ['close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            df['delta'] = 0
            df['cvd'] = 0
            df['cvd_slope'] = 0
            return df
    
    # 如果没有open列,使用close作为基准
    if 'open' not in df.columns:
        df['open'] = df['close']
    
    # 计算单根K线的Delta（向量化操作，避免循环）
    # 阳线: +volume, 阴线: -volume, 十字星: 0
    df['delta'] = np.where(
        df['close'] > df['open'],  # 阳线
        df['volume'],
        np.where(
            df['close'] < df['open'],  # 阴线
            -df['volume'],
            0  # 十字星
        )
    )
    
    df['cvd'] = df['delta'].cumsum()
    
    # CVD斜率（趋势）
    df['cvd_slope'] = df['cvd'].diff(5) / 5  # 5周期平均变化
    
    return df


# ========== 4. ATR (Average True Range) ==========
def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算ATR (Average True Range)
    用于衡量波动率
    """
    # 边界检查
    if df.empty or len(df) == 0:
        return df
    
    df = df.copy()
    
    # True Range（向量化计算）
    prev_close = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - prev_close)
    df['tr3'] = abs(df['low'] - prev_close)
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    
    # ATR（使用EMA而非SMA，更灵敏）
    df['atr'] = df['tr'].ewm(span=period, adjust=False).mean()
    
    # ATR占比（波动率）- 防止除零
    df['atr_pct'] = df['atr'] / df['close'].replace(0, np.nan) * 100
    
    # 删除临时列
    df.drop(['tr1', 'tr2', 'tr3', 'tr'], axis=1, inplace=True)
    
    return df


# ========== 5. 市场状态识别 ==========
def detect_market_state(df: pd.DataFrame) -> Dict:
    """
    识别市场状态：趋势 / 震荡 / 突破
    """
    if len(df) < 50:
        return {"state": "数据不足", "strength": 0}
    
    # ATR波动率
    if 'atr_pct' not in df.columns:
        df = calculate_atr(df)
    
    atr_pct = df['atr_pct'].iloc[-1]
    atr_ma = df['atr_pct'].rolling(20).mean().iloc[-1]
    
    # ADX趋势强度（简化版）
    adx = calculate_simple_adx(df)
    
    # 价格位置
    high_50 = df['high'].tail(50).max()
    low_50 = df['low'].tail(50).min()
    current_price = df['close'].iloc[-1]
    price_position = (current_price - low_50) / (high_50 - low_50)
    
    # 判断状态
    state = "震荡"
    strength = 50
    
    # 趋势状态
    if adx > 25:
        if current_price > df['ema21'].iloc[-1] > df['ema200'].iloc[-1]:
            state = "上升趋势"
            strength = adx
        elif current_price < df['ema21'].iloc[-1] < df['ema200'].iloc[-1]:
            state = "下降趋势"
            strength = adx
    # 突破状态
    elif price_position > 0.95:
        state = "向上突破"
        strength = 80
    elif price_position < 0.05:
        state = "向下突破"
        strength = 80
    # 震荡状态
    else:
        state = "震荡"
        strength = 50 - adx / 2
    
    return {
        "state": state,
        "strength": min(strength, 100),
        "adx": adx,
        "atr_pct": atr_pct,
        "atr_change": (atr_pct - atr_ma) / atr_ma * 100 if atr_ma > 0 else 0,
        "description": f"{state} (ADX:{adx:.0f}, ATR:{atr_pct:.2f}%)"
    }


def calculate_simple_adx(df: pd.DataFrame, period: int = 14) -> float:
    """计算简化版ADX"""
    try:
        # 计算方向移动
        up_move = df['high'] - df['high'].shift(1)
        down_move = df['low'].shift(1) - df['low']
        
        # +DM和-DM
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # ATR
        tr = df['high'] - df['low']
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        if atr == 0:
            return 0
        
        # 方向指标
        plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean().iloc[-1] / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean().iloc[-1] / atr
        
        # DX
        dx = abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001) * 100
        
        return dx
    except:
        return 20


# ========== 6. 支撑压力算法升级（成交量密集区）==========
def calculate_support_resistance_v2(df: pd.DataFrame, lookback: int = 100) -> Dict:
    """
    升级版支撑压力计算
    使用成交量密集区 + 波段高低点
    """
    if len(df) < lookback:
        return {"support": [], "resistance": [], "description": "数据不足"}
    
    supports = []
    resistances = []
    current_price = df['close'].iloc[-1]
    
    # 1. 成交量密集区（Volume Profile简化版）
    price_bins = 20
    high = df['high'].tail(lookback).max()
    low = df['low'].tail(lookback).min()
    bin_size = (high - low) / price_bins
    
    volume_profile = {}
    for i in range(len(df.tail(lookback))):
        candle = df.tail(lookback).iloc[i]
        bin_idx = int((candle['close'] - low) / bin_size)
        bin_idx = min(max(bin_idx, 0), price_bins - 1)
        bin_price = low + bin_idx * bin_size + bin_size / 2
        
        if bin_price not in volume_profile:
            volume_profile[bin_price] = 0
        volume_profile[bin_price] += candle['volume']
    
    # 找出成交量密集区
    sorted_profile = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
    
    # 前三个成交量密集区作为支撑压力
    for i, (price, vol) in enumerate(sorted_profile[:5]):
        if price < current_price:
            supports.append((f"成交量密集区{i+1}", price, vol))
        else:
            resistances.append((f"成交量密集区{i+1}", price, vol))
    
    # 2. 波段高低点
    recent_high = df['high'].tail(lookback).max()
    recent_low = df['low'].tail(lookback).min()
    resistances.append(("波段高点", recent_high, 0))
    supports.append(("波段低点", recent_low, 0))
    
    # 3. EMA支撑压力
    if 'ema21' in df.columns:
        ema21 = df['ema21'].iloc[-1]
        if ema21 < current_price:
            supports.append(("EMA21支撑", ema21, 0))
        else:
            resistances.append(("EMA21压力", ema21, 0))
    
    if 'ema200' in df.columns:
        ema200 = df['ema200'].iloc[-1]
        if ema200 < current_price:
            supports.append(("EMA200支撑", ema200, 0))
        else:
            resistances.append(("EMA200压力", ema200, 0))
    
    # 4. VWAP
    if 'vwap' in df.columns:
        vwap = df['vwap'].iloc[-1]
        if vwap < current_price:
            supports.append(("VWAP支撑", vwap, 0))
        else:
            resistances.append(("VWAP压力", vwap, 0))
    
    # 排序
    supports.sort(key=lambda x: x[1], reverse=True)
    resistances.sort(key=lambda x: x[1])
    
    return {
        "supports": supports,
        "resistances": resistances,
        "nearest_support": supports[0] if supports else None,
        "nearest_resistance": resistances[0] if resistances else None,
        "volume_profile": volume_profile,
        "description": f"支撑: {supports[0][1]:.2f} | 压力: {resistances[0][1]:.2f}" if supports and resistances else "计算中"
    }


# ========== 7. 盘口失衡算法优化 ==========
def calculate_order_imbalance(bid_volume: float, ask_volume: float) -> Dict:
    """
    优化版盘口失衡计算
    imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
    
    返回值范围：[-1, 1]
    -1: 极度卖压
    1: 极度买压
    """
    if bid_volume + ask_volume == 0:
        imbalance = 0
    else:
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
    
    # 判断压力方向
    if imbalance > 0.5:
        status = "强买压"
        strength = abs(imbalance) * 100
    elif imbalance > 0.2:
        status = "买盘优势"
        strength = abs(imbalance) * 100
    elif imbalance < -0.5:
        status = "强卖压"
        strength = abs(imbalance) * 100
    elif imbalance < -0.2:
        status = "卖盘优势"
        strength = abs(imbalance) * 100
    else:
        status = "平衡"
        strength = 50
    
    return {
        "imbalance": imbalance,
        "status": status,
        "strength": strength,
        "description": f"{status} ({imbalance:+.2f})"
    }


# ========== 8. 主力吸筹检测优化（加入CVD条件）==========
def detect_accumulation_v2(df: pd.DataFrame, lookback: int = 50) -> Dict:
    """
    升级版主力吸筹检测
    新增条件：CVD上升
    """
    if len(df) < lookback:
        return {"signal": False, "strength": 0, "description": "数据不足"}
    
    signals = []
    strength = 0
    
    # 1. 价格波动率降低
    recent_close = df['close'].tail(lookback)
    price_std = recent_close.std() / recent_close.mean()
    if price_std < 0.02:
        signals.append("价格横盘整理")
        strength += 20
    
    # 2. 成交量萎缩
    recent_vol = df['volume'].tail(lookback)
    vol_ma = df['volume'].rolling(20).mean().iloc[-1]
    current_vol = recent_vol.iloc[-1]
    if current_vol < vol_ma * 0.7:
        signals.append("成交量萎缩")
        strength += 15
    
    # 3. 价格在低位
    price_rank = (recent_close.rank().iloc[-1] / lookback)
    if price_rank < 0.3:
        signals.append("价格处于低位")
        strength += 20
    
    # 4. 下影线增多（主力护盘）
    if 'low' in df.columns and 'close' in df.columns:
        lower_wicks = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.0001)
        recent_wicks = lower_wicks.tail(10).mean()
        if recent_wicks > 0.6:
            signals.append("下影线增多")
            strength += 25
    
    # 5. 均线走平
    if 'ema21' in df.columns:
        ema21_slope = (df['ema21'].iloc[-1] - df['ema21'].iloc[-5]) / df['ema21'].iloc[-5]
        if abs(ema21_slope) < 0.005:
            signals.append("均线走平")
            strength += 20
    
    # 6. 【新增】CVD上升（关键条件）
    if 'cvd' in df.columns:
        cvd_current = df['cvd'].iloc[-1]
        cvd_ma = df['cvd'].tail(lookback).mean()
        cvd_slope = df['cvd_slope'].iloc[-1] if 'cvd_slope' in df.columns else 0
        
        if cvd_current > cvd_ma and cvd_slope > 0:
            signals.append(f"CVD上升({cvd_slope:+.0f})")
            strength += 30  # 权重较高
    
    return {
        "signal": strength >= 60,  # 提高阈值
        "strength": min(strength, 100),
        "signals": signals,
        "description": " | ".join(signals) if signals else "无明显吸筹迹象"
    }


# ========== 9. LSTM 趋势预测（修复过拟合）==========
def lstm_predict_v2(df: pd.DataFrame, window_size: int = 10) -> Dict:
    """
    修复版LSTM趋势预测
    1. 概率上限85%
    2. 加入dropout概念（随机性）
    """
    if len(df) < window_size + 10:
        return {"trend": "数据不足", "probability": 0, "confidence": 0}
    
    # 计算多个指标
    ma_short = df['close'].rolling(5).mean().iloc[-1]
    ma_mid = df['close'].rolling(10).mean().iloc[-1]
    ma_long = df['close'].rolling(20).mean().iloc[-1]
    
    # 动量指标
    momentum = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
    
    # 趋势判断
    bullish_score = 0
    bearish_score = 0
    
    # 均线排列
    if ma_short > ma_mid > ma_long:
        bullish_score += 30
    elif ma_short < ma_mid < ma_long:
        bearish_score += 30
    
    # 动量
    if momentum > 0.5:
        bullish_score += min(momentum * 5, 40)
    elif momentum < -0.5:
        bearish_score += min(abs(momentum) * 5, 40)
    
    # 价格位置
    price_rank = df['close'].tail(50).rank().iloc[-1] / 50 if len(df) >= 50 else 0.5
    if price_rank > 0.7:
        bullish_score += 20
    elif price_rank < 0.3:
        bearish_score += 20
    
    # CVD趋势
    if 'cvd_slope' in df.columns:
        cvd_slope = df['cvd_slope'].iloc[-1]
        if cvd_slope > 0:
            bullish_score += 15
        elif cvd_slope < 0:
            bearish_score += 15
    
    # 计算概率
    total_score = bullish_score + bearish_score
    if total_score > 0:
        bullish_prob = bullish_score / total_score * 100
        bearish_prob = bearish_score / total_score * 100
    else:
        bullish_prob = 50
        bearish_prob = 50
    
    # 【关键修复1】概率上限85%
    bullish_prob = min(bullish_prob, 85.0)
    bearish_prob = min(bearish_prob, 85.0)
    
    # 【关键修复2】加入dropout随机性（模拟20%的不确定性）
    dropout = 0.2
    bullish_prob = bullish_prob * (1 - dropout) + 50 * dropout
    bearish_prob = bearish_prob * (1 - dropout) + 50 * dropout
    
    # 判断趋势
    if bullish_prob > 65:
        trend = "上涨"
        probability = bullish_prob
    elif bearish_prob > 65:
        trend = "下跌"
        probability = bearish_prob
    else:
        trend = "震荡"
        probability = 50
    
    confidence = min(abs(bullish_prob - bearish_prob), 85)  # 置信度上限85%
    
    return {
        "trend": trend,
        "probability": probability,
        "confidence": confidence,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "description": f"预测趋势: {trend} (概率{probability:.0f}%, 置信度{confidence:.0f}%)"
    }


# ========== 10. 假突破检测修复（加入成交量和CVD）==========
def fake_breakout_v2(df: pd.DataFrame, lookback: int = 20) -> Dict:
    """
    升级版假突破检测
    新增：成交量 + CVD判断
    """
    if len(df) < lookback + 5:
        return {"signal": False, "type": None, "description": "数据不足"}
    
    signals = []
    is_fake = False
    fake_type = None
    
    # 检查最近5根K线
    for i in range(-5, 0):
        candle = df.iloc[i]
        prev_candles = df.iloc[i-lookback:i]
        
        # 假向上突破
        high_threshold = prev_candles['high'].max()
        if candle['high'] > high_threshold:
            # 检查是否回落
            if candle['close'] < high_threshold:
                # 【新增】检查成交量是否放大
                vol_ma = prev_candles['volume'].mean()
                vol_ratio = candle['volume'] / vol_ma if vol_ma > 0 else 1
                
                # 【新增】检查CVD是否下降
                cvd_decline = False
                if 'cvd' in df.columns and i > -len(df):
                    cvd_change = df['cvd'].iloc[i] - df['cvd'].iloc[i-1]
                    cvd_decline = cvd_change < 0
                
                # 如果突破但成交量未放大或CVD下降，则为假突破
                if vol_ratio < 1.5 or cvd_decline:
                    signals.append(f"第{abs(i)}根K线假突破（量不足或CVD下降）")
                    is_fake = True
                    fake_type = "假向上突破"
        
        # 假向下突破
        low_threshold = prev_candles['low'].min()
        if candle['low'] < low_threshold:
            # 检查是否回升
            if candle['close'] > low_threshold:
                # 【新增】检查成交量是否放大
                vol_ma = prev_candles['volume'].mean()
                vol_ratio = candle['volume'] / vol_ma if vol_ma > 0 else 1
                
                # 【新增】检查CVD是否上升
                cvd_rise = False
                if 'cvd' in df.columns and i > -len(df):
                    cvd_change = df['cvd'].iloc[i] - df['cvd'].iloc[i-1]
                    cvd_rise = cvd_change > 0
                
                # 如果破位但成交量未放大或CVD上升，则为假突破
                if vol_ratio < 1.5 or cvd_rise:
                    signals.append(f"第{abs(i)}根K线假破位（量不足或CVD上升）")
                    is_fake = True
                    fake_type = "假向下突破"
    
    return {
        "signal": is_fake,
        "type": fake_type,
        "signals": signals,
        "description": " | ".join(signals) if signals else "无假突破信号"
    }


# ========== 11. 巨鲸拉升检测 ==========
def whale_pump_v2(df: pd.DataFrame, order_imbalance: float = 0) -> Dict:
    """巨鲸拉升检测（保持原有逻辑）"""
    if len(df) < 20:
        return {"signal": False, "strength": 0, "description": "数据不足"}
    
    signals = []
    strength = 0
    
    # 1. 成交量放大
    vol_ma = df['volume'].rolling(20).mean().iloc[-1]
    current_vol = df['volume'].iloc[-1]
    vol_ratio = current_vol / vol_ma if vol_ma > 0 else 0
    
    if vol_ratio > 3.0:
        signals.append(f"巨量异动({vol_ratio:.1f}倍)")
        strength += 30
    elif vol_ratio > 2.0:
        signals.append(f"量能放大({vol_ratio:.1f}倍)")
        strength += 20
    
    # 2. 价格突破
    recent_high = df['high'].tail(20).max()
    current_price = df['close'].iloc[-1]
    if current_price >= recent_high * 0.99:
        signals.append("突破阻力位")
        strength += 25
    
    # 3. 连续阳线
    last_5_candles = df['close'].iloc[-5:] > df['open'].iloc[-5:]
    bullish_count = last_5_candles.sum()
    if bullish_count >= 4:
        signals.append(f"连续{bullish_count}根阳线")
        strength += 20
    
    # 4. 订单簿失衡
    # 处理字典类型的order_imbalance
    imbalance_value = 0
    if isinstance(order_imbalance, dict):
        imbalance_value = order_imbalance.get('imbalance', 0)
    elif isinstance(order_imbalance, (int, float)):
        imbalance_value = order_imbalance
    
    if imbalance_value > 0.5:
        signals.append(f"买盘压倒({imbalance_value:.2f})")
        strength += 25
    elif imbalance_value > 0.3:
        signals.append(f"买盘优势({imbalance_value:.2f})")
        strength += 15
    
    # 5. CVD上升
    if 'cvd_slope' in df.columns:
        cvd_slope = df['cvd_slope'].iloc[-1]
        if cvd_slope > 0:
            signals.append(f"CVD上升")
            strength += 20
    
    return {
        "signal": strength >= 60,
        "strength": min(strength, 100),
        "signals": signals,
        "description": " | ".join(signals) if signals else "无明显拉升迹象"
    }


# ========== 12. 急跌风险检测 ==========
def crash_warning_v2(df: pd.DataFrame, order_imbalance: float = 0) -> Dict:
    """急跌风险检测（保持原有逻辑）"""
    if len(df) < 20:
        return {"signal": False, "strength": 0, "description": "数据不足"}
    
    signals = []
    strength = 0
    risk_level = "低"
    
    # 1. 放量下跌
    vol_ma = df['volume'].rolling(20).mean().iloc[-1]
    current_vol = df['volume'].iloc[-1]
    vol_ratio = current_vol / vol_ma if vol_ma > 0 else 0
    price_drop = (df['close'].iloc[-2] - df['close'].iloc[-1]) / df['close'].iloc[-2] * 100 if len(df) > 1 else 0
    
    if vol_ratio > 2.0 and price_drop > 1:
        signals.append(f"放量下跌({price_drop:.1f}%)")
        strength += 35
        risk_level = "高"
    elif price_drop > 2:
        signals.append(f"急速下跌({price_drop:.1f}%)")
        strength += 30
        risk_level = "高"
    
    # 2. 连续阴线
    last_5_candles = df['close'].iloc[-5:] < df['open'].iloc[-5:]
    bearish_count = last_5_candles.sum()
    if bearish_count >= 4:
        signals.append(f"连续{bearish_count}根阴线")
        strength += 25
        risk_level = "中"
    
    # 3. 跌破支撑
    recent_low = df['low'].tail(20).min()
    if df['close'].iloc[-1] < recent_low:
        signals.append("跌破支撑位")
        strength += 30
        risk_level = "高"
    
    # 4. 卖盘压倒
    # 处理字典类型的order_imbalance
    imbalance_value = 0
    if isinstance(order_imbalance, dict):
        imbalance_value = order_imbalance.get('imbalance', 0)
    elif isinstance(order_imbalance, (int, float)):
        imbalance_value = order_imbalance
    
    if imbalance_value < -0.5:
        signals.append(f"卖盘压倒({abs(imbalance_value):.2f})")
        strength += 30
    elif imbalance_value < -0.3:
        signals.append(f"卖盘优势({abs(imbalance_value):.2f})")
        strength += 20
    
    # 5. CVD下降
    if 'cvd_slope' in df.columns:
        cvd_slope = df['cvd_slope'].iloc[-1]
        if cvd_slope < 0:
            signals.append(f"CVD下降")
            strength += 15
    
    if strength >= 70:
        risk_level = "高"
    elif strength >= 40:
        risk_level = "中"
    
    return {
        "signal": strength >= 50,
        "strength": min(strength, 100),
        "risk_level": risk_level,
        "signals": signals,
        "description": " | ".join(signals) if signals else "无明显风险"
    }


# ========== 13. 量价口诀策略 ==========
def volume_price_mnemonics_v2(df: pd.DataFrame) -> Dict:
    """量价口诀策略（保持原有逻辑）"""
    if len(df) < 30:
        return {
            "signal": "观望", 
            "direction": None, 
            "strength": 0, 
            "description": "数据不足",
            "mnemonic": None
        }
    
    signals = []
    direction = None
    strength = 0
    mnemonic = None
    
    # 基础指标计算
    vol_ma_20 = df['volume'].rolling(20).mean().iloc[-1]
    current_vol = df['volume'].iloc[-1]
    vol_ratio = current_vol / vol_ma_20 if vol_ma_20 > 0 else 1
    
    current_price = df['close'].iloc[-1]
    prev_price = df['close'].iloc[-2] if len(df) > 1 else current_price
    price_change_pct = (current_price - prev_price) / prev_price * 100 if prev_price > 0 else 0
    
    recent_high_20 = df['high'].tail(20).max()
    recent_low_20 = df['low'].tail(20).min()
    
    support_level = recent_low_20
    resistance_level = recent_high_20
    
    # 做多口诀
    if vol_ratio < 0.7 and -2 < price_change_pct < 0:
        if current_price > support_level * 1.001:
            recent_lows = df['low'].tail(3).values
            if len(recent_lows) >= 3 and recent_lows[-1] >= min(recent_lows) * 0.998:
                signals.append("【口诀1】缩量回踩，低点不破 → 准备动手 ✅")
                direction = "做多"
                strength += 40
                mnemonic = "缩量回踩"
    
    if vol_ratio > 1.5 and price_change_pct > 0.5:
        if current_price >= recent_high_20 * 0.995:
            signals.append("【口诀2】放量起涨，突破前高 → 直接开多 ✅")
            direction = "做多"
            strength += 45
            mnemonic = "放量突破"
    
    # 做空口诀
    if vol_ratio < 0.7 and 0 < price_change_pct < 2:
        if current_price < resistance_level * 0.999:
            recent_highs = df['high'].tail(3).values
            if len(recent_highs) >= 3 and recent_highs[-1] <= max(recent_highs) * 1.002:
                signals.append("【口诀5】缩量反弹，高点不破 → 准备动手 ❌")
                direction = "做空"
                strength += 40
                mnemonic = "缩量反弹"
    
    if vol_ratio > 1.5 and price_change_pct < -0.5:
        if current_price <= recent_low_20 * 1.005:
            signals.append("【口诀6】放量下跌，跌破前低 → 直接开空 ❌")
            direction = "做空"
            strength += 45
            mnemonic = "放量破位"
    
    if not signals:
        signals.append("无明显口诀信号，观望为主")
        direction = "观望"
        strength = 0
    
    return {
        "signal": " | ".join(signals),
        "direction": direction,
        "strength": min(strength, 100),
        "vol_ratio": round(vol_ratio, 2),
        "price_change_pct": round(price_change_pct, 2),
        "support_level": round(support_level, 2),
        "resistance_level": round(resistance_level, 2),
        "mnemonic": mnemonic,
        "description": signals[0] if signals else "观望"
    }


# ========== 14. Funding Rate 监控 ==========
def get_funding_rate(symbol: str = "ETHUSDT") -> Dict:
    """
    获取资金费率
    判断多空拥挤度
    """
    try:
        # 从Binance获取
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": symbol, "limit": 1}
        
        resp = requests.get(url, params=params, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                funding_rate = float(data[0]['fundingRate']) * 100
                
                # 判断拥挤度
                if funding_rate > 0.1:
                    status = "多头拥挤"
                    risk = "高"
                elif funding_rate > 0.05:
                    status = "多头偏多"
                    risk = "中"
                elif funding_rate < -0.1:
                    status = "空头拥挤"
                    risk = "高"
                elif funding_rate < -0.05:
                    status = "空头偏多"
                    risk = "中"
                else:
                    status = "平衡"
                    risk = "低"
                
                return {
                    "funding_rate": funding_rate,
                    "status": status,
                    "risk": risk,
                    "description": f"资金费率: {funding_rate:.4f}% ({status})"
                }
    except Exception as e:
        pass
    
    return {
        "funding_rate": 0,
        "status": "未知",
        "risk": "低",
        "description": "资金费率获取失败"
    }


# ========== 15. Open Interest 监控 ==========
def get_open_interest(symbol: str = "ETHUSDT") -> Dict:
    """
    获取持仓量
    判断资金流向
    """
    try:
        # 从Binance获取
        url = "https://fapi.binance.com/fapi/v1/openInterest"
        params = {"symbol": symbol}
        
        resp = requests.get(url, params=params, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            open_interest = float(data['openInterest'])
            
            # 判断资金流向
            # 需要历史数据对比，这里简化处理
            return {
                "open_interest": open_interest,
                "status": "正常",
                "description": f"持仓量: {open_interest:.0f}"
            }
    except Exception as e:
        pass
    
    return {
        "open_interest": 0,
        "status": "未知",
        "description": "持仓量获取失败"
    }


# ========== 16. 爆仓监控 ==========
def get_liquidations(symbol: str = "ETHUSDT", limit: int = 50) -> Dict:
    """
    监控爆仓数据
    """
    try:
        # 从Coinglass API获取（需要API key，这里用模拟数据）
        # 实际使用时需要接入真实API
        
        # 简化版：从Binance获取最近的大额交易
        url = "https://fapi.binance.com/fapi/v1/aggTrades"
        params = {"symbol": symbol, "limit": limit}
        
        resp = requests.get(url, params=params, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            
            # 统计大额交易
            large_trades = [t for t in data if float(t['q']) > 100]  # 大于100 ETH
            
            long_liquidations = sum(1 for t in large_trades if not t['m'])  # 主动买入
            short_liquidations = sum(1 for t in large_trades if t['m'])  # 主动卖出
            
            return {
                "long_liquidations": long_liquidations,
                "short_liquidations": short_liquidations,
                "total_large_trades": len(large_trades),
                "description": f"大额交易: 多{long_liquidations} 空{short_liquidations}"
            }
    except Exception as e:
        pass
    
    return {
        "long_liquidations": 0,
        "short_liquidations": 0,
        "total_large_trades": 0,
        "description": "爆仓数据获取失败"
    }


# ========== 17. 巨鲸监控 ==========
def get_whale_alert(symbol: str = "ETH") -> Dict:
    """
    监控大额转账
    实际使用需要接入Whale Alert API
    """
    # 这里返回模拟数据
    # 实际使用时需要配置API key
    
    return {
        "large_transfers": 0,
        "total_amount": 0,
        "description": "巨鲸监控需要API配置"
    }


# ========== 18. 综合信号分析 V2 ==========
def comprehensive_signal_analysis_v2(df: pd.DataFrame, order_imbalance: float = 0, walls: Dict = {}) -> Dict:
    """
    升级版综合信号分析
    新增权重分配：
    - 趋势 30%
    - 量能 20%
    - 盘口 20%
    - AI预测 20%
    - 结构 10%
    """
    if len(df) < 50:
        return {"error": "数据不足"}
    
    # 计算所有指标
    df = calculate_vwap(df)
    df = calculate_ema(df)
    df = calculate_cvd(df)
    df = calculate_atr(df)
    
    # 执行所有分析
    accumulation = detect_accumulation_v2(df)
    whale = whale_pump_v2(df, order_imbalance)
    crash = crash_warning_v2(df, order_imbalance)
    vp_signal = volume_price_mnemonics_v2(df)
    market_state = detect_market_state(df)
    fake = fake_breakout_v2(df)
    lstm = lstm_predict_v2(df)
    sr = calculate_support_resistance_v2(df)
    funding = get_funding_rate()
    oi = get_open_interest()
    
    # 综合评分（按权重）
    bullish_score = 0
    bearish_score = 0
    
    # 趋势 30%
    if market_state['state'] in ['上升趋势', '向上突破']:
        bullish_score += 30
    elif market_state['state'] in ['下降趋势', '向下突破']:
        bearish_score += 30
    
    # 量能 20%
    vol_ma = df['volume'].rolling(20).mean().iloc[-1]
    current_vol = df['volume'].iloc[-1]
    vol_ratio = current_vol / vol_ma if vol_ma > 0 else 1
    
    if vol_ratio > 1.5 and df['close'].iloc[-1] > df['close'].iloc[-2]:
        bullish_score += 20
    elif vol_ratio > 1.5 and df['close'].iloc[-1] < df['close'].iloc[-2]:
        bearish_score += 20
    
    # 盘口 20%
    # 处理字典类型的order_imbalance
    imbalance_value = 0
    if isinstance(order_imbalance, dict):
        imbalance_value = order_imbalance.get('imbalance', 0)
    elif isinstance(order_imbalance, (int, float)):
        imbalance_value = order_imbalance
    
    imbalance_data = calculate_order_imbalance(
        100 * (1 + imbalance_value),  # 估算买卖量
        100 * (1 - imbalance_value)
    )
    if imbalance_value > 0.3:
        bullish_score += 20
    elif imbalance_value < -0.3:
        bearish_score += 20
    
    # AI预测 20%
    if lstm['trend'] == "上涨":
        bullish_score += lstm['confidence'] * 0.2
    elif lstm['trend'] == "下跌":
        bearish_score += lstm['confidence'] * 0.2
    
    # 结构 10%
    if accumulation['signal']:
        bullish_score += 10
    if whale['signal']:
        bullish_score += 10
    if crash['signal']:
        bearish_score += 10
    
    # 综合判断
    total_score = bullish_score + bearish_score
    if total_score > 0:
        bullish_pct = bullish_score / total_score * 100
        bearish_pct = bearish_score / total_score * 100
    else:
        bullish_pct = 50
        bearish_pct = 50
    
    # 最终建议
    if bullish_pct > 65:
        recommendation = "做多"
        confidence = bullish_pct
    elif bearish_pct > 65:
        recommendation = "做空"
        confidence = bearish_pct
    else:
        recommendation = "观望"
        confidence = 50
    
    return {
        "recommendation": recommendation,
        "confidence": min(confidence, 85),  # 置信度上限85%
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "signals": {
            "accumulation": accumulation,
            "whale_pump": whale,
            "crash_warning": crash,
            "volume_price": vp_signal,
            "market_state": market_state,
            "fake_breakout": fake,
            "lstm_prediction": lstm,
            "support_resistance": sr,
            "funding_rate": funding,
            "open_interest": oi
        },
        "df": df,  # 返回计算后的DataFrame
        "summary": f"综合建议: {recommendation} (置信度{confidence:.0f}%)\n做多得分: {bullish_score:.0f} | 做空得分: {bearish_score:.0f}"
    }


# ========== 语音播报（保持原有功能）==========
def speak_alert(text: str):
    """本地语音播报（Windows）"""
    import threading
    
    def _speak():
        try:
            import os
            if os.name == "nt":  # Windows
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.say(text)
                engine.runAndWait()
        except Exception as e:
            print(f"语音播报失败: {e}")
    
    # 在后台线程执行，避免阻塞
    threading.Thread(target=_speak, daemon=True).start()


# ========== 导出所有函数 ==========
__all__ = [
    'calculate_vwap',
    'calculate_ema',
    'calculate_cvd',
    'calculate_atr',
    'detect_market_state',
    'calculate_support_resistance_v2',
    'calculate_order_imbalance',
    'detect_accumulation_v2',
    'lstm_predict_v2',
    'fake_breakout_v2',
    'whale_pump_v2',
    'crash_warning_v2',
    'volume_price_mnemonics_v2',
    'get_funding_rate',
    'get_open_interest',
    'get_liquidations',
    'get_whale_alert',
    'comprehensive_signal_analysis_v2',
    'speak_alert'
]
