"""
ETHUSDT 高级信号指标模块
包含：主力吸筹、巨鲸拉升、急跌风险、多周期共振、口诀策略、AI审计、LSTM预测等
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# ========== 1. 主力吸筹检测 ==========
def detect_accumulation(df: pd.DataFrame, lookback: int = 50) -> Dict:
    """
    检测主力吸筹信号
    特征：
    1. 价格横盘或小幅下跌，但成交量逐渐萎缩
    2. 买盘力量增强（订单簿失衡）
    3. 价格在支撑位附近反复测试
    4. RSI背离
    """
    if len(df) < lookback:
        return {"signal": False, "strength": 0, "description": "数据不足"}
    
    signals = []
    strength = 0
    
    # 1. 价格波动率降低
    recent_close = df['close'].tail(lookback)
    price_std = recent_close.std() / recent_close.mean()
    if price_std < 0.02:  # 波动率小于2%
        signals.append("价格横盘整理")
        strength += 20
    
    # 2. 成交量萎缩
    recent_vol = df['volume'].tail(lookback)
    vol_ma = df['volume'].rolling(20).mean().iloc[-1]
    current_vol = recent_vol.iloc[-1]
    if current_vol < vol_ma * 0.7:  # 成交量低于均量70%
        signals.append("成交量萎缩")
        strength += 15
    
    # 3. 价格在低位
    price_rank = (recent_close.rank().iloc[-1] / lookback)
    if price_rank < 0.3:  # 价格在30%分位以下
        signals.append("价格处于低位")
        strength += 20
    
    # 4. 下影线增多（主力护盘）
    if 'low' in df.columns and 'close' in df.columns:
        lower_wicks = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.0001)
        recent_wicks = lower_wicks.tail(10).mean()
        if recent_wicks > 0.6:  # 下影线占比超过60%
            signals.append("下影线增多")
            strength += 25
    
    # 5. MA20走平
    ma20_slope = (df['ma20'].iloc[-1] - df['ma20'].iloc[-5]) / df['ma20'].iloc[-5] if 'ma20' in df.columns else 0
    if abs(ma20_slope) < 0.005:  # MA20斜率小于0.5%
        signals.append("均线走平")
        strength += 20
    
    return {
        "signal": strength >= 50,
        "strength": min(strength, 100),
        "signals": signals,
        "description": " | ".join(signals) if signals else "无明显吸筹迹象"
    }


# ========== 2. 巨鲸拉升检测 ==========
def whale_pump(df: pd.DataFrame, order_imbalance: float = 0) -> Dict:
    """
    检测巨鲸拉升信号
    特征：
    1. 成交量突然放大（3倍以上）
    2. 价格快速上涨突破阻力位
    3. 大单买入明显
    4. 连续阳线
    """
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
    if current_price >= recent_high * 0.99:  # 接近或突破近期高点
        signals.append("突破阻力位")
        strength += 25
    
    # 3. 连续阳线
    last_5_candles = df['close'].iloc[-5:] > df['open'].iloc[-5:]
    bullish_count = last_5_candles.sum()
    if bullish_count >= 4:
        signals.append(f"连续{bullish_count}根阳线")
        strength += 20
    
    # 4. 订单簿失衡
    if order_imbalance > 0.5:
        signals.append(f"买盘压倒({order_imbalance:.2f})")
        strength += 25
    elif order_imbalance > 0.3:
        signals.append(f"买盘优势({order_imbalance:.2f})")
        strength += 15
    
    # 5. 价格快速上涨
    price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
    if price_change > 3:
        signals.append(f"快速拉升({price_change:.1f}%)")
        strength += 25
    
    return {
        "signal": strength >= 60,
        "strength": min(strength, 100),
        "signals": signals,
        "description": " | ".join(signals) if signals else "无明显拉升迹象"
    }


# ========== 3. 急跌风险检测 ==========
def crash_warning(df: pd.DataFrame, order_imbalance: float = 0) -> Dict:
    """
    检测急跌风险信号
    特征：
    1. 成交量放大+价格下跌
    2. 连续阴线
    3. 跌破关键支撑
    4. 卖盘压倒
    """
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
    if order_imbalance < -0.5:
        signals.append(f"卖盘压倒({abs(order_imbalance):.2f})")
        strength += 30
    elif order_imbalance < -0.3:
        signals.append(f"卖盘优势({abs(order_imbalance):.2f})")
        strength += 20
    
    # 5. 跌破MA20
    if 'ma20' in df.columns:
        if df['close'].iloc[-1] < df['ma20'].iloc[-1]:
            signals.append("跌破MA20")
            strength += 20
    
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


# ========== 4. 多周期共振 ==========
def multi_tf_resonance(df_dict: Dict[str, pd.DataFrame]) -> Dict:
    """
    多周期趋势共振检测（1m/5m/15m）
    当多个周期趋势一致时，信号更可靠
    """
    if not df_dict or len(df_dict) < 2:
        return {"signal": False, "resonance": "数据不足", "strength": 0}
    
    trends = {}
    for tf, df in df_dict.items():
        if len(df) < 20:
            continue
        
        # 计算趋势
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else ma20
        price = df['close'].iloc[-1]
        
        # 趋势判断
        if price > ma20 > ma50:
            trends[tf] = "上涨"
        elif price < ma20 < ma50:
            trends[tf] = "下跌"
        else:
            trends[tf] = "震荡"
    
    if not trends:
        return {"signal": False, "resonance": "数据不足", "strength": 0}
    
    # 统计趋势一致性
    trend_counts = {}
    for tf, trend in trends.items():
        trend_counts[trend] = trend_counts.get(trend, 0) + 1
    
    # 找出主要趋势
    main_trend = max(trend_counts.items(), key=lambda x: x[1])
    resonance_count = main_trend[1]
    total_count = len(trends)
    
    # 计算强度
    strength = (resonance_count / total_count) * 100
    
    # 构建描述
    trend_str = " | ".join([f"{tf}:{trend}" for tf, trend in trends.items()])
    
    return {
        "signal": resonance_count >= 2 and main_trend[0] != "震荡",
        "resonance": f"{resonance_count}/{total_count}周期{main_trend[0]}共振",
        "main_trend": main_trend[0],
        "strength": strength,
        "details": trend_str,
        "trends": trends
    }


# ========== 5. 口诀策略信号 ==========
def volume_price_mnemonics(df: pd.DataFrame) -> Dict:
    """
    量价口诀策略信号
    做多信号：
    - 缩量回踩 / 放量突破 / 放量急跌（抄底） / 缩量横盘
    
    做空信号：
    - 缩量反弹 / 放量下跌 / 放量急涨（诱多） / 缩量横盘
    """
    if len(df) < 20:
        return {"signal": "观望", "direction": None, "strength": 0, "description": "数据不足"}
    
    signals = []
    direction = None
    strength = 0
    
    # 计算量比
    vol_ma = df['volume'].rolling(20).mean().iloc[-1]
    current_vol = df['volume'].iloc[-1]
    vol_ratio = current_vol / vol_ma if vol_ma > 0 else 1
    
    # 价格变化
    price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100 if len(df) > 1 else 0
    
    # 价格位置
    price_rank = df['close'].tail(50).rank().iloc[-1] / 50 if len(df) >= 50 else 0.5
    
    # 1. 缩量回踩（做多）
    if vol_ratio < 0.7 and price_change < 0 and price_rank > 0.5:
        signals.append("缩量回踩 ✅做多")
        direction = "做多"
        strength += 30
    
    # 2. 放量突破（做多）
    if vol_ratio > 1.5 and price_change > 0:
        recent_high = df['high'].tail(20).max()
        if df['close'].iloc[-1] >= recent_high * 0.99:
            signals.append("放量突破 ✅做多")
            direction = "做多"
            strength += 35
    
    # 3. 放量急跌（抄底做多）
    if vol_ratio > 2.0 and price_change < -2:
        signals.append("放量急跌 ⚠️抄底机会")
        direction = "抄底"
        strength += 25
    
    # 4. 缩量横盘（关注突破）
    if vol_ratio < 0.6 and abs(price_change) < 0.5:
        signals.append("缩量横盘 🔍关注突破")
        strength += 20
    
    # 5. 缩量反弹（做空）
    if vol_ratio < 0.7 and price_change > 0 and price_rank < 0.5:
        signals.append("缩量反弹 ❌做空")
        direction = "做空"
        strength += 30
    
    # 6. 放量下跌（做空）
    if vol_ratio > 1.5 and price_change < -1:
        signals.append("放量下跌 ❌做空")
        direction = "做空"
        strength += 35
    
    # 7. 放量急涨（诱多）
    if vol_ratio > 2.5 and price_change > 3 and price_rank > 0.8:
        signals.append("放量急涨 ⚠️诱多陷阱")
        direction = "观望"
        strength += 25
    
    return {
        "signal": " | ".join(signals) if signals else "无明显信号",
        "direction": direction,
        "strength": min(strength, 100),
        "vol_ratio": vol_ratio,
        "description": " | ".join(signals) if signals else "观望"
    }


# ========== 6. 市场结构分析 ==========
def market_structure(df: pd.DataFrame) -> Dict:
    """
    分析市场结构：突破/破位/震荡
    """
    if len(df) < 50:
        return {"structure": "数据不足", "signal": None, "strength": 0}
    
    # 计算关键价位
    recent_high = df['high'].tail(50).max()
    recent_low = df['low'].tail(50).min()
    current_price = df['close'].iloc[-1]
    
    # 波动范围
    price_range = recent_high - recent_low
    mid_price = (recent_high + recent_low) / 2
    
    # 判断结构
    structure = "震荡"
    signal = None
    strength = 0
    
    # 突破
    if current_price > recent_high * 0.995:
        structure = "突破"
        signal = "向上突破"
        strength = 80
    # 破位
    elif current_price < recent_low * 1.005:
        structure = "破位"
        signal = "向下破位"
        strength = 80
    # 震荡区间
    else:
        # 判断价格位置
        position = (current_price - recent_low) / price_range
        if position > 0.7:
            structure = "震荡上沿"
            signal = "接近阻力"
            strength = 50
        elif position < 0.3:
            structure = "震荡下沿"
            signal = "接近支撑"
            strength = 50
        else:
            structure = "震荡中枢"
            signal = "区间震荡"
            strength = 30
    
    return {
        "structure": structure,
        "signal": signal,
        "strength": strength,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "position": (current_price - recent_low) / price_range if price_range > 0 else 0.5,
        "description": f"{structure} - {signal}"
    }


# ========== 7. 假突破检测 ==========
def fake_breakout(df: pd.DataFrame, lookback: int = 20) -> Dict:
    """
    检测假突破信号
    特征：快速突破后迅速回落
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
                signals.append(f"第{abs(i)}根K线假突破阻力")
                is_fake = True
                fake_type = "假向上突破"
        
        # 假向下突破
        low_threshold = prev_candles['low'].min()
        if candle['low'] < low_threshold:
            # 检查是否回升
            if candle['close'] > low_threshold:
                signals.append(f"第{abs(i)}根K线假破支撑")
                is_fake = True
                fake_type = "假向下突破"
    
    return {
        "signal": is_fake,
        "type": fake_type,
        "signals": signals,
        "description": " | ".join(signals) if signals else "无假突破信号"
    }


# ========== 8. LSTM 趋势预测 ==========
def lstm_predict(df: pd.DataFrame, window_size: int = 10) -> Dict:
    """
    简化版LSTM趋势预测（基于移动平均和动量）
    注：这是简化版本，完整LSTM需要训练模型
    """
    if len(df) < window_size + 10:
        return {"trend": "数据不足", "probability": 0, "confidence": 0}
    
    # 使用移动平均和动量作为简化预测
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
    
    # 计算概率
    total_score = bullish_score + bearish_score
    if total_score > 0:
        bullish_prob = bullish_score / total_score * 100
        bearish_prob = bearish_score / total_score * 100
    else:
        bullish_prob = 50
        bearish_prob = 50
    
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
    
    confidence = min(abs(bullish_prob - bearish_prob), 100)
    
    return {
        "trend": trend,
        "probability": probability,
        "confidence": confidence,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "description": f"预测趋势: {trend} (概率{probability:.0f}%, 置信度{confidence:.0f}%)"
    }


# ========== 9. 支撑压力计算 ==========
def calculate_support_resistance(df: pd.DataFrame, lookback: int = 50) -> Dict:
    """
    计算支撑位和压力位
    使用多种方法：波段高低点、均线、大单墙
    """
    if len(df) < lookback:
        return {"support": [], "resistance": [], "description": "数据不足"}
    
    supports = []
    resistances = []
    
    # 1. 波段高低点
    recent_high = df['high'].tail(lookback).max()
    recent_low = df['low'].tail(lookback).min()
    resistances.append(("波段高点", recent_high))
    supports.append(("波段低点", recent_low))
    
    # 2. 均线支撑压力
    if 'ma20' in df.columns:
        ma20 = df['ma20'].iloc[-1]
        if df['close'].iloc[-1] > ma20:
            supports.append(("MA20支撑", ma20))
        else:
            resistances.append(("MA20压力", ma20))
    
    if 'ma50' in df.columns:
        ma50 = df['ma50'].iloc[-1]
        if df['close'].iloc[-1] > ma50:
            supports.append(("MA50支撑", ma50))
        else:
            resistances.append(("MA50压力", ma50))
    
    # 3. 斐波那契回调位
    price_range = recent_high - recent_low
    fib_levels = {
        "Fib 23.6%": recent_low + price_range * 0.236,
        "Fib 38.2%": recent_low + price_range * 0.382,
        "Fib 50%": recent_low + price_range * 0.5,
        "Fib 61.8%": recent_low + price_range * 0.618,
    }
    
    current_price = df['close'].iloc[-1]
    for level_name, level_price in fib_levels.items():
        if level_price < current_price:
            supports.append((level_name, level_price))
        else:
            resistances.append((level_name, level_price))
    
    # 排序
    supports.sort(key=lambda x: x[1], reverse=True)
    resistances.sort(key=lambda x: x[1])
    
    return {
        "supports": supports,
        "resistances": resistances,
        "nearest_support": supports[0] if supports else None,
        "nearest_resistance": resistances[0] if resistances else None,
        "description": f"支撑: {supports[0][1]:.2f} | 压力: {resistances[0][1]:.2f}" if supports and resistances else "计算中"
    }


# ========== 10. AI 审计信号 ==========
def ai_audit_ollama(df: pd.DataFrame, order_imbalance: float = 0) -> str:
    """
    生成AI审计提示词（Ollama本地模型）
    """
    if len(df) < 20:
        return "数据不足，无法分析"
    
    last = df.iloc[-1]
    price = last['close']
    
    # 计算各项指标
    accumulation = detect_accumulation(df)
    whale = whale_pump(df, order_imbalance)
    crash = crash_warning(df, order_imbalance)
    vp_signal = volume_price_mnemonics(df)
    structure = market_structure(df)
    lstm = lstm_predict(df)
    sr = calculate_support_resistance(df)
    
    prompt = f"""
作为量化交易AI分析师，分析ETHUSDT当前市场状态：

【价格数据】
当前价格: {price:.2f}
MA20: {last.get('ma20', price):.2f}
MA50: {last.get('ma50', price):.2f}
量比: {last.get('vol_ratio', 1):.2f}
盘口失衡: {order_imbalance:.2f}

【信号分析】
1. 主力吸筹: {accumulation['description']} (强度{accumulation['strength']})
2. 巨鲸拉升: {whale['description']} (强度{whale['strength']})
3. 急跌风险: {crash['description']} (风险{crash.get('risk_level', '低')})
4. 量价口诀: {vp_signal['signal']}
5. 市场结构: {structure['description']}
6. LSTM预测: {lstm['description']}

【支撑压力】
{sr['description']}

请给出：
1. 市场结构判断（吸筹/派发/震荡/突破）
2. 操作建议（入场点、止损位、止盈位）
3. 风险等级（高/中/低）
4. 关键关注点
"""
    return prompt


def get_deepseek_audit(df: pd.DataFrame, api_key: str, order_imbalance: float = 0) -> str:
    """
    使用DeepSeek API进行AI审计
    """
    try:
        import requests
        
        prompt = ai_audit_ollama(df, order_imbalance)
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是专业的量化交易分析师，擅长技术分析和风险控制。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"DeepSeek API错误: {response.status_code}"
    
    except Exception as e:
        return f"AI审计失败: {str(e)}"


# ========== 综合信号分析 ==========
def comprehensive_signal_analysis(df: pd.DataFrame, order_imbalance: float = 0, walls: Dict = {}) -> Dict:
    """
    综合所有信号分析
    """
    if len(df) < 20:
        return {"error": "数据不足"}
    
    # 执行所有分析
    accumulation = detect_accumulation(df)
    whale = whale_pump(df, order_imbalance)
    crash = crash_warning(df, order_imbalance)
    vp_signal = volume_price_mnemonics(df)
    structure = market_structure(df)
    fake = fake_breakout(df)
    lstm = lstm_predict(df)
    sr = calculate_support_resistance(df)
    
    # 综合评分
    bullish_score = 0
    bearish_score = 0
    
    # 主力吸筹
    if accumulation['signal']:
        bullish_score += accumulation['strength'] * 0.5
    
    # 巨鲸拉升
    if whale['signal']:
        bullish_score += whale['strength'] * 0.8
    
    # 急跌风险
    if crash['signal']:
        bearish_score += crash['strength'] * 0.8
    
    # 量价口诀
    if vp_signal['direction'] == "做多":
        bullish_score += vp_signal['strength']
    elif vp_signal['direction'] == "做空":
        bearish_score += vp_signal['strength']
    
    # LSTM预测
    if lstm['trend'] == "上涨":
        bullish_score += lstm['confidence'] * 0.5
    elif lstm['trend'] == "下跌":
        bearish_score += lstm['confidence'] * 0.5
    
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
        "confidence": confidence,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "signals": {
            "accumulation": accumulation,
            "whale_pump": whale,
            "crash_warning": crash,
            "volume_price": vp_signal,
            "market_structure": structure,
            "fake_breakout": fake,
            "lstm_prediction": lstm,
            "support_resistance": sr
        },
        "summary": f"综合建议: {recommendation} (置信度{confidence:.0f}%)\n做多得分: {bullish_score:.0f} | 做空得分: {bearish_score:.0f}"
    }


# ========== 语音播报 ==========
def speak_alert(text: str):
    """
    本地语音播报（Windows）
    """
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
    'detect_accumulation',
    'whale_pump',
    'crash_warning',
    'multi_tf_resonance',
    'volume_price_mnemonics',
    'market_structure',
    'fake_breakout',
    'lstm_predict',
    'calculate_support_resistance',
    'ai_audit_ollama',
    'get_deepseek_audit',
    'comprehensive_signal_analysis',
    'speak_alert'
]
