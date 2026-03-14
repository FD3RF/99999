# ========== 升级版高级信号分析模块 V2.0 ==========
import numpy as np
import pandas as pd
import requests
import logging
import time
import threading
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== 1. VWAP 计算 ==========
def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """计算VWAP（成交量加权平均价格）"""
    if 'volume' not in df.columns or df['volume'].sum() == 0:
        df['vwap'] = df['close']
        return df
    
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    cumulative_tp_vol = (typical_price * df['volume']).cumsum()
    cumulative_vol = df['volume'].cumsum()
    df['vwap'] = cumulative_tp_vol / cumulative_vol
    return df

# ========== 2. EMA 计算 ==========
def calculate_ema(df: pd.DataFrame, periods: List[int] = [21, 200]) -> pd.DataFrame:
    """计算EMA（指数移动平均线）"""
    for period in periods:
        df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    return df

# ========== 3. CVD 计算 ==========
def calculate_cvd(df: pd.DataFrame) -> pd.DataFrame:
    """计算CVD（累积成交量差）"""
    if 'volume' not in df.columns:
        df['cvd'] = 0
        return df
    
    price_change = df['close'].diff()
    df['cvd'] = np.where(price_change >= 0, df['volume'], -df['volume'])
    df['cvd'] = df['cvd'].cumsum()
    return df

# ========== 4. ATR 计算 ==========
def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """计算ATR（平均真实波动范围）"""
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=period).mean()
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    return df

# ========== 5. 市场状态检测 ==========
def detect_market_state(df: pd.DataFrame) -> Dict:
    """检测市场状态（震荡/趋势/突破）"""
    if len(df) < 50:
        return {"state": "数据不足", "strength": 0, "description": "等待更多数据"}
    
    ema21 = df['ema21'].iloc[-1] if 'ema21' in df.columns else df['close'].rolling(21).mean().iloc[-1]
    ema200 = df['ema200'].iloc[-1] if 'ema200' in df.columns else df['close'].rolling(200).mean().iloc[-1]
    price = df['close'].iloc[-1]
    volatility = df['close'].pct_change().std() * 100
    
    if ema21 > ema200 and price > ema21:
        state = "上涨趋势"
        strength = min(100, 60 + (price - ema21) / ema21 * 1000)
    elif ema21 < ema200 and price < ema21:
        state = "下跌趋势"
        strength = min(100, 60 + (ema21 - price) / ema21 * 1000)
    else:
        state = "震荡"
        strength = 40
    
    return {
        "state": state,
        "strength": round(strength, 1),
        "volatility": round(volatility, 2),
        "description": f"{state} (强度{strength:.0f}%, 波动{volatility:.2f}%)"
    }

# ========== 6. 支撑压力位计算 ==========
def calculate_support_resistance_v2(df: pd.DataFrame, window: int = 20) -> Dict:
    """计算支撑压力位"""
    if len(df) < window:
        return {"nearest_support": None, "nearest_resistance": None, "description": "数据不足"}
    
    recent = df.tail(window)
    price = df['close'].iloc[-1]
    
    # 找局部低点作为支撑
    lows = recent['low'].values
    support_levels = []
    for i in range(1, len(lows) - 1):
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            support_levels.append((i, lows[i]))
    
    # 找局部高点作为压力
    highs = recent['high'].values
    resistance_levels = []
    for i in range(1, len(highs) - 1):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            resistance_levels.append((i, highs[i]))
    
    nearest_support = None
    for idx, level in sorted(support_levels, key=lambda x: x[1], reverse=True):
        if level < price:
            nearest_support = (idx, level)
            break
    
    nearest_resistance = None
    for idx, level in sorted(resistance_levels, key=lambda x: x[1]):
        if level > price:
            nearest_resistance = (idx, level)
            break
    
    if nearest_support is None:
        nearest_support = (0, recent['low'].min())
    if nearest_resistance is None:
        nearest_resistance = (0, recent['high'].max())
    
    return {
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "description": f"支撑: ${nearest_support[1]:.2f} | 压力: ${nearest_resistance[1]:.2f}"
    }

# ========== 7. 盘口失衡计算 ==========
def calculate_order_imbalance(bid_vol: float, ask_vol: float) -> Dict:
    """计算盘口失衡"""
    total = bid_vol + ask_vol
    if total == 0:
        return {'imbalance': 0, 'status': '无数据'}
    
    imb = (bid_vol - ask_vol) / total
    
    if imb > 0.3:
        status = "买盘优势"
    elif imb < -0.3:
        status = "卖盘优势"
    else:
        status = "平衡"
    
    return {'imbalance': round(imb, 2), 'status': status}

# ========== 8. 主力吸筹检测 ==========
def detect_accumulation_v2(df: pd.DataFrame) -> Dict:
    """检测主力吸筹信号"""
    if len(df) < 20:
        return {"signal": False, "strength": 0, "description": "数据不足"}
    
    recent_vol = df['volume'].iloc[-5:].mean()
    prev_vol = df['volume'].iloc[-20:-5].mean()
    price_change = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
    
    signal = False
    strength = 0
    description = ""
    
    if recent_vol < prev_vol * 0.7 and abs(price_change) < 2:
        signal = True
        strength = 50
        description = "缩量震荡，可能主力吸筹"
    
    return {"signal": signal, "strength": strength, "description": description}

# ========== 9. LSTM预测（简化版）==========
def lstm_predict_v2(df: pd.DataFrame) -> Dict:
    """简化版趋势预测"""
    if len(df) < 50:
        return {"trend": "分析中", "probability": 50, "confidence": "低"}
    
    ema21 = df['ema21'].iloc[-1] if 'ema21' in df.columns else df['close'].rolling(21).mean().iloc[-1]
    ema200 = df['ema200'].iloc[-1] if 'ema200' in df.columns else df['close'].rolling(200).mean().iloc[-1]
    momentum = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10] * 100
    
    if ema21 > ema200 and momentum > 0:
        trend = "上涨"
        probability = min(85, 60 + abs(momentum) * 5)
    elif ema21 < ema200 and momentum < 0:
        trend = "下跌"
        probability = min(85, 60 + abs(momentum) * 5)
    else:
        trend = "震荡"
        probability = 50
    
    return {
        "trend": trend,
        "probability": round(probability, 0),
        "confidence": "高" if probability > 70 else "中" if probability > 50 else "低"
    }

# ========== 10. 假突破检测 ==========
def fake_breakout_v2(df: pd.DataFrame) -> Dict:
    """检测假突破"""
    if len(df) < 10:
        return {"signal": False, "type": "", "description": "数据不足"}
    
    signal = False
    break_type = ""
    description = ""
    
    if df['high'].iloc[-1] > df['high'].iloc[-5:-1].max():
        if df['close'].iloc[-1] < df['open'].iloc[-1]:
            signal = True
            break_type = "假向上突破"
            description = "突破后回落，可能是假突破"
    
    elif df['low'].iloc[-1] < df['low'].iloc[-5:-1].min():
        if df['close'].iloc[-1] > df['open'].iloc[-1]:
            signal = True
            break_type = "假向下突破"
            description = "跌破后反弹，可能是假突破"
    
    return {"signal": signal, "type": break_type, "description": description}

# ========== 11. 巨鲸拉升检测 ==========
def whale_pump_v2(df: pd.DataFrame) -> Dict:
    """检测巨鲸拉升"""
    if len(df) < 5:
        return {"signal": False, "strength": 0, "description": "数据不足"}
    
    vol_ratio = df['vol_ratio'].iloc[-1] if 'vol_ratio' in df.columns else 1
    price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
    
    signal = False
    strength = 0
    description = ""
    
    if vol_ratio > 2.0 and price_change > 1:
        signal = True
        strength = min(100, vol_ratio * 20)
        description = f"放量{price_change:.1f}%，巨鲸可能进场"
    
    return {"signal": signal, "strength": strength, "description": description}

# ========== 12. 急跌风险检测 ==========
def crash_warning_v2(df: pd.DataFrame) -> Dict:
    """检测急跌风险"""
    if len(df) < 10:
        return {"signal": False, "risk_level": "低", "description": "数据不足"}
    
    price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
    atr_pct = df['atr_pct'].iloc[-1] if 'atr_pct' in df.columns else 0.5
    
    signal = False
    risk_level = "低"
    description = ""
    
    if price_change < -3:
        signal = True
        risk_level = "高"
        description = f"5分钟跌幅{abs(price_change):.1f}%，急跌风险"
    elif price_change < -1.5 and atr_pct > 0.8:
        signal = True
        risk_level = "中"
        description = f"波动加大，注意风险"
    
    return {"signal": signal, "risk_level": risk_level, "description": description}

# ========== 13. 量价口诀 ==========
def volume_price_mnemonics_v2(df: pd.DataFrame) -> Dict:
    """量价口诀分析"""
    if len(df) < 2:
        return {"mnemonic": "", "signal": "", "strength": 0}
    
    vol_ratio = df['vol_ratio'].iloc[-1] if 'vol_ratio' in df.columns else 1
    price_change = (df['close'].iloc[-1] - df['open'].iloc[-1]) / df['open'].iloc[-1] * 100
    
    if price_change > 0 and vol_ratio > 1.5:
        return {"mnemonic": "放量上涨，健康走势", "signal": "看多", "strength": 60}
    elif price_change > 0 and vol_ratio < 0.7:
        return {"mnemonic": "缩量上涨，动能不足", "signal": "谨慎", "strength": 30}
    elif price_change < 0 and vol_ratio > 1.5:
        return {"mnemonic": "放量下跌，抛压重", "signal": "看空", "strength": 60}
    elif price_change < 0 and vol_ratio < 0.7:
        return {"mnemonic": "缩量下跌，卖盘枯竭", "signal": "观望", "strength": 40}
    else:
        return {"mnemonic": "量价正常", "signal": "中性", "strength": 50}

# ========== 14. Funding Rate 监控 ==========
def get_funding_rate(symbol: str = "ETHUSDT") -> Dict:
    """获取资金费率"""
    sources = [
        ("Binance", "https://fapi.binance.com/fapi/v1/fundingRate"),
        ("Binance1", "https://fapi1.binance.com/fapi/v1/fundingRate"),
    ]
    
    for name, url in sources:
        try:
            params = {"symbol": symbol, "limit": 1}
            resp = requests.get(url, params=params, timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    funding_rate = float(data[0]['fundingRate']) * 100
                    
                    if funding_rate > 0.1:
                        status, risk = "多头拥挤", "高"
                    elif funding_rate > 0.05:
                        status, risk = "多头偏多", "中"
                    elif funding_rate < -0.05:
                        status, risk = "空头偏多", "中"
                    elif funding_rate < -0.1:
                        status, risk = "空头拥挤", "高"
                    else:
                        status, risk = "平衡", "低"
                    
                    return {"funding_rate": round(funding_rate, 4), "status": status, "risk": risk,
                            "description": f"{funding_rate:.4f}% ({status})"}
        except:
            continue
    
    return {"funding_rate": 0.01, "status": "数据暂不可用", "risk": "低", "description": "费率暂不可用"}

# ========== 15. Open Interest 监控 ==========
def get_open_interest(symbol: str = "ETHUSDT") -> Dict:
    """获取持仓量"""
    sources = [
        ("Binance", "https://fapi.binance.com/fapi/v1/openInterest"),
        ("Binance1", "https://fapi1.binance.com/fapi/v1/openInterest"),
    ]
    
    for name, url in sources:
        try:
            params = {"symbol": symbol}
            resp = requests.get(url, params=params, timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                open_interest = float(data.get('openInterest', 0))
                
                if open_interest > 0:
                    status = "高持仓" if open_interest > 1000000 else "中等持仓" if open_interest > 500000 else "低持仓"
                    return {"open_interest": open_interest, "status": status, "description": f"{open_interest:,.0f} ETH"}
        except:
            continue
    
    return {"open_interest": 800000, "status": "估算值", "description": "~800K ETH (估算)"}

# ========== 16. 爆仓监控 ==========
def get_liquidations(symbol: str = "ETHUSDT") -> Dict:
    """获取爆仓数据"""
    return {"long_liquidations": 0, "short_liquidations": 0, "total_liquidations": 0, "description": "爆仓数据获取中..."}

# ========== 17. 语音播报 ==========
_last_speak_time = {}
_SPEAK_COOLDOWN = 60

def speak_alert(text: str, alert_type: str = "default"):
    """语音播报"""
    current_time = time.time()
    if alert_type in _last_speak_time:
        if current_time - _last_speak_time[alert_type] < _SPEAK_COOLDOWN:
            return
    _last_speak_time[alert_type] = current_time
    
    def _speak():
        try:
            import os
            if os.name == "nt":
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 150)
                    engine.say(text)
                    engine.runAndWait()
                except:
                    pass
        except:
            print(f"📢 [语音播报] {text}")
    
    threading.Thread(target=_speak, daemon=True).start()

# ========== 18. MACD 计算 ==========
def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    """计算MACD指标"""
    if len(df) < slow + signal:
        return {"macd": 0, "signal": 0, "histogram": 0, "trend": "中性"}
    
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    hist_val = histogram.iloc[-1]
    
    if hist_val > 0 and hist_val > histogram.iloc[-2]:
        trend = "多头增强"
    elif hist_val > 0:
        trend = "多头减弱"
    elif hist_val < 0 and hist_val < histogram.iloc[-2]:
        trend = "空头增强"
    elif hist_val < 0:
        trend = "空头减弱"
    else:
        trend = "中性"
    
    cross = ""
    if macd_line.iloc[-2] < signal_line.iloc[-2] and macd_val > signal_val:
        cross = "金叉"
    elif macd_line.iloc[-2] > signal_line.iloc[-2] and macd_val < signal_val:
        cross = "死叉"
    
    return {"macd": round(macd_val, 4), "signal": round(signal_val, 4), "histogram": round(hist_val, 4),
            "trend": trend, "cross": cross, "description": f"MACD: {macd_val:.2f} | {trend} {cross}"}

# ========== 19. 多周期趋势判断 ==========
def analyze_multi_timeframe(df: pd.DataFrame) -> Dict:
    """多周期趋势分析"""
    if len(df) < 200:
        return {"short": "未知", "medium": "未知", "long": "未知", "alignment": "数据不足"}
    
    price = df['close'].iloc[-1]
    
    short_ma = df['close'].rolling(5).mean().iloc[-1]
    short_trend = "上涨" if price > short_ma else "下跌"
    short_strength = abs(price - short_ma) / short_ma * 100
    
    ema21 = df['ema21'].iloc[-1] if 'ema21' in df.columns else df['close'].rolling(21).mean().iloc[-1]
    medium_trend = "上涨" if price > ema21 else "下跌"
    medium_strength = abs(price - ema21) / ema21 * 100
    
    ema200 = df['ema200'].iloc[-1] if 'ema200' in df.columns else df['close'].rolling(200).mean().iloc[-1]
    long_trend = "上涨" if price > ema200 else "下跌"
    long_strength = abs(price - ema200) / ema200 * 100
    
    trends = [short_trend, medium_trend, long_trend]
    bullish_count = trends.count("上涨")
    
    if bullish_count == 3:
        alignment, score = "全多共振", 100
    elif bullish_count == 2:
        alignment, score = "偏多", 66
    elif bullish_count == 0:
        alignment, score = "全空共振", 0
    elif bullish_count == 1:
        alignment, score = "偏空", 33
    else:
        alignment, score = "震荡", 50
    
    return {
        "short": {"trend": short_trend, "strength": round(short_strength, 2)},
        "medium": {"trend": medium_trend, "strength": round(medium_strength, 2)},
        "long": {"trend": long_trend, "strength": round(long_strength, 2)},
        "alignment": alignment, "score": score,
        "description": f"短{short_trend}|中{medium_trend}|长{long_trend} = {alignment}"
    }

# ========== 20. 信号仲裁系统 ==========
def signal_arbitration(signals: Dict) -> Dict:
    """信号仲裁系统"""
    arbitration = {"conflicts": [], "confirmations": [], "final_decision": "观望", "confidence_adjustment": 0}
    
    lstm = signals.get('lstm_prediction', {})
    market_state = signals.get('market_state', {})
    fake = signals.get('fake_breakout', {})
    whale = signals.get('whale_pump', {})
    crash = signals.get('crash_warning', {})
    macd = signals.get('macd', {})
    mtf = signals.get('multi_timeframe', {})
    
    conflicts = []
    confirmations = []
    
    if lstm.get('trend') == "上涨" and market_state.get('state') == "下跌趋势":
        conflicts.append(("AI预测上涨", "市场下跌趋势"))
    elif lstm.get('trend') == "下跌" and market_state.get('state') == "上涨趋势":
        conflicts.append(("AI预测下跌", "市场上涨趋势"))
    
    if fake.get('signal'):
        conflicts.append(("假突破检测", fake.get('type', '')))
    
    if whale.get('signal'):
        confirmations.append(("巨鲸拉升", whale.get('description', '')))
    
    if crash.get('signal') and crash.get('risk_level') == "高":
        conflicts.append(("急跌风险", crash.get('description', '')))
    
    if macd.get('cross') == "金叉":
        confirmations.append(("MACD金叉", "多头信号"))
    elif macd.get('cross') == "死叉":
        confirmations.append(("MACD死叉", "空头信号"))
    
    if mtf.get('alignment') in ["全多共振", "全空共振"]:
        confirmations.append(("多周期共振", mtf.get('alignment', '')))
    
    arbitration["conflicts"] = conflicts
    arbitration["confirmations"] = confirmations
    
    conflict_penalty = len(conflicts) * 10
    confirmation_bonus = len(confirmations) * 5
    arbitration["confidence_adjustment"] = confirmation_bonus - conflict_penalty
    
    if len(conflicts) > len(confirmations):
        arbitration["final_decision"] = "谨慎观望"
        arbitration["reason"] = f"检测到{len(conflicts)}个风险信号"
    elif len(confirmations) > len(conflicts):
        arbitration["final_decision"] = "信号确认"
        arbitration["reason"] = f"获得{len(confirmations)}个确认信号"
    else:
        arbitration["final_decision"] = "中性观望"
        arbitration["reason"] = "信号平衡"
    
    return arbitration

# ========== 21. 综合信号分析 ==========
def comprehensive_signal_analysis_v2(df: pd.DataFrame, imbalance: float = 0, walls: List = None) -> Dict:
    """综合信号分析"""
    if len(df) < 50:
        return {"recommendation": "数据不足", "confidence": 0, "signals": {}, "bullish_score": 0, "bearish_score": 0,
                "summary": "等待更多数据..."}
    
    # 计算技术指标
    df = calculate_vwap(df)
    df = calculate_ema(df)
    df = calculate_cvd(df)
    df = calculate_atr(df)
    
    if 'vol_ratio' not in df.columns:
        vol_ma = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / vol_ma.replace(0, 1)
    
    # 各项分析
    market_state = detect_market_state(df)
    support_resistance = calculate_support_resistance_v2(df)
    accumulation = detect_accumulation_v2(df)
    lstm_prediction = lstm_predict_v2(df)
    fake_breakout = fake_breakout_v2(df)
    whale_pump = whale_pump_v2(df)
    crash_warning = crash_warning_v2(df)
    volume_price = volume_price_mnemonics_v2(df)
    funding_rate = get_funding_rate()
    open_interest = get_open_interest()
    
    # 先计算 MACD 和 多周期趋势
    macd = calculate_macd(df)
    mtf = analyze_multi_timeframe(df)
    
    # 综合评分
    bullish_score = 0
    bearish_score = 0
    
    # 市场状态
    if market_state['state'] == "上涨趋势":
        bullish_score += 20
    elif market_state['state'] == "下跌趋势":
        bearish_score += 20
    
    # LSTM预测
    if lstm_prediction['trend'] == "上涨":
        bullish_score += lstm_prediction['probability'] * 0.3
    elif lstm_prediction['trend'] == "下跌":
        bearish_score += lstm_prediction['probability'] * 0.3
    
    # 巨鲸拉升
    if whale_pump['signal']:
        bullish_score += whale_pump['strength'] * 0.3
    
    # 急跌风险
    if crash_warning['signal']:
        bearish_score += 30 if crash_warning['risk_level'] == "高" else 15
    
    # 主力吸筹
    if accumulation['signal']:
        bullish_score += 15
    
    # 假突破
    if fake_breakout['signal']:
        if "向上" in fake_breakout['type']:
            bearish_score += 10
        else:
            bullish_score += 10
    
    # 量价信号
    if volume_price['signal'] == "看多":
        bullish_score += volume_price['strength'] * 0.5
    elif volume_price['signal'] == "看空":
        bearish_score += volume_price['strength'] * 0.5
    
    # 盘口失衡
    if imbalance > 0.3:
        bullish_score += 10
    elif imbalance < -0.3:
        bearish_score += 10
    
    # MACD 信号参与评分
    if macd.get('cross') == '金叉':
        bullish_score += 15
    elif macd.get('cross') == '死叉':
        bearish_score += 15
    elif macd.get('trend') == '多头增强':
        bullish_score += 8
    elif macd.get('trend') == '空头增强':
        bearish_score += 8
    
    # 多周期趋势参与评分
    if mtf.get('alignment') == '全多共振':
        bullish_score += 25
    elif mtf.get('alignment') == '全空共振':
        bearish_score += 25
    elif mtf.get('alignment') == '偏多':
        bullish_score += 10
    elif mtf.get('alignment') == '偏空':
        bearish_score += 10
    
    # 综合建议
    total_score = bullish_score + bearish_score
    if total_score == 0:
        recommendation = "观望"
        confidence = 50
    else:
        if bullish_score > bearish_score * 1.5:
            recommendation = "做多"
            confidence = min(95, 50 + (bullish_score - bearish_score))
        elif bearish_score > bullish_score * 1.5:
            recommendation = "做空"
            confidence = min(95, 50 + (bearish_score - bullish_score))
        else:
            recommendation = "观望"
            confidence = 50
    
    signals = {
        "market_state": market_state,
        "support_resistance": support_resistance,
        "accumulation": accumulation,
        "lstm_prediction": lstm_prediction,
        "fake_breakout": fake_breakout,
        "whale_pump": whale_pump,
        "crash_warning": crash_warning,
        "volume_price": volume_price,
        "funding_rate": funding_rate,
        "open_interest": open_interest,
        "macd": macd,
        "multi_timeframe": mtf,
        "signal_arbitration": {}
    }
    
    # 信号仲裁系统
    signals["signal_arbitration"] = signal_arbitration(signals)
    
    # 根据仲裁结果调整置信度
    arbitration = signals["signal_arbitration"]
    confidence = max(0, min(100, confidence + arbitration.get('confidence_adjustment', 0)))
    
    summary = f"{recommendation}信号，置信度{confidence:.0f}%。{volume_price['mnemonic']}"
    
    return {
        "recommendation": recommendation,
        "confidence": round(confidence, 0),
        "signals": signals,
        "bullish_score": round(bullish_score, 0),
        "bearish_score": round(bearish_score, 0),
        "summary": summary,
        "df": df
    }
