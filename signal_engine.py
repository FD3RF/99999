# signal_engine.py
import pandas as pd
import numpy as np
from config import *

# 本地覆盖：趋势判断参数（避免config中缺失）
TREND_CHECK_WINDOW = 10
TREND_MATCH_RATIO = 0.7

class SignalEngine:
    """交易信号识别引擎 - 无冲突版本"""

    def __init__(self, df, support=None, resistance=None):
        self.df = df
        self.support = support
        self.resistance = resistance
        self.latest = df.iloc[-1] if len(df) > 0 else None
        self.prev = df.iloc[-2] if len(df) > 1 else None

    def _get_recent_swing_low(self, within=5):
        recent_swings = self.df[self.df["swing_low"]].tail(within)
        if len(recent_swings) > 0:
            return recent_swings.iloc[-1]["low"]
        return self.df["low"].iloc[-within-1:-1].min()

    def _get_recent_swing_high(self, within=5):
        recent_swings = self.df[self.df["swing_high"]].tail(within)
        if len(recent_swings) > 0:
            return recent_swings.iloc[-1]["high"]
        return self.df["high"].iloc[-within-1:-1].max()

    def _is_volume_shrink(self, periods=3):
        vol_ratio = self.df["volume_ratio"].iloc[-periods:].mean()
        return vol_ratio < VOLUME_RATIO_SHRINK_60

    def _is_volume_expanding(self, threshold=VOLUME_RATIO_MODERATE):
        return self.latest["volume_ratio"] >= threshold

    def _check_trend(self):
        """检查趋势 - 修复：放宽完美趋势要求，允许70%K线满足趋势"""
        if len(self.df) < TREND_CHECK_WINDOW:
            return "unknown"
        highs = self.df["high"].iloc[-TREND_CHECK_WINDOW:].values
        lows = self.df["low"].iloc[-TREND_CHECK_WINDOW:].values
        
        # 计算上升趋势匹配数（高点和低点都在抬高）
        up_matches = sum(1 for i in range(1, len(highs)) if highs[i] >= highs[i-1] and lows[i] >= lows[i-1])
        # 计算下降趋势匹配数
        down_matches = sum(1 for i in range(1, len(highs)) if highs[i] <= highs[i-1] and lows[i] <= lows[i-1])
        
        threshold = int((TREND_CHECK_WINDOW - 1) * TREND_MATCH_RATIO)
        
        if up_matches >= threshold:
            return "uptrend"
        elif down_matches >= threshold:
            return "downtrend"
        return "ranging"

    def _get_kline_pattern_names(self):
        names = []
        if self.latest.get("hammer"): names.append("锤子线")
        if self.latest.get("shooting_star"): names.append("流星线")
        if self.latest.get("doji"): names.append("十字星")
        if self.latest.get("long_lower_shadow"): names.append("长下影线")
        if self.latest.get("long_upper_shadow"): names.append("长上影线")
        if self.latest.get("bullish_engulfing"): names.append("阳包阴")
        if self.latest.get("bearish_engulfing"): names.append("阴包阳")
        if self.latest.get("big_bull"): names.append("大阳线")
        if self.latest.get("big_bear"): names.append("大阴线")
        return ", ".join(names) if names else "普通K线"

    def _calculate_signal_strength(self, direction):
        """计算信号强度分数"""
        score = 0
        
        # 趋势匹配
        if direction == "LONG" and self._check_trend() == "uptrend":
            score += 2
        elif direction == "SHORT" and self._check_trend() == "downtrend":
            score += 2
        
        # MACD方向
        if direction == "LONG" and self.latest["macd_hist"] > 0:
            score += 2
        elif direction == "SHORT" and self.latest["macd_hist"] < 0:
            score += 2
        
        # 成交量配合
        if self._is_volume_expanding(VOLUME_RATIO_MODERATE):
            score += 1
        
        # K线形态
        if direction == "LONG" and (self.latest.get("hammer") or self.latest.get("long_lower_shadow") or self.latest.get("bullish_engulfing")):
            score += 2
        elif direction == "SHORT" and (self.latest.get("shooting_star") or self.latest.get("long_upper_shadow") or self.latest.get("bearish_engulfing")):
            score += 2
        
        return score

    def check_trend_callback_long(self):
        """趋势回调做多 - 修复：放宽条件，允许灵活匹配"""
        if len(self.df) < 10 or self._check_trend() != "uptrend":
            return None
        if not self._is_volume_shrink(3):
            return None
        recent_low = self._get_recent_swing_low(5)
        if self.latest["low"] < recent_low * (1 - STOP_BUFFER):
            return None
        
        # MACD条件放宽：DIF>0 或 金叉（原为必须同时满足）
        macd_ok = self.latest["dif"] > 0 or self.latest["golden_cross"]
        if not macd_ok:
            return None
            
        # K线形态放宽：增加更多形态识别（原仅锤子/十字星/长下影）
        kline_ok = (self.latest.get("hammer") or 
                    self.latest.get("doji") or 
                    self.latest.get("long_lower_shadow") or
                    self.latest.get("piercing") or
                    self.latest.get("bullish_engulfing"))
        if not kline_ok:
            return None
            
        # 价格行为放宽：阳线 且 (放量 或 破前高)（原必须同时满足）
        price_ok = (self.latest["close"] > self.latest["open"] and 
                    (self._is_volume_expanding(VOLUME_RATIO_MODERATE) or 
                     self.latest["close"] > self.df["high"].iloc[-2]))
        if not price_ok:
            return None
            
        # MACD柱放宽：>0 即可（原要求比前一根放大）
        if not (self.latest["macd_hist"] > 0):
            return None
        
        entry = self.latest["close"]
        stop_loss = recent_low * (1 - STOP_BUFFER)
        target = entry + MIN_RISK_REWARD_RATIO * (entry - stop_loss)
        
        return {
            "direction": "LONG",
            "type": "趋势回调做多",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"上升趋势缩量回踩，MACD金叉/DIF>0，{self._get_kline_pattern_names()}，放量/破高",
            "mnemonic": "缩量回踩底不破，底背离/金叉等放量；放量起涨破前高，红柱出现直接多。"
        }

    def check_trap_long(self):
        """陷阱诱空做多 - 修复：放宽条件"""
        if len(self.df) < 5:
            return None
        recent_low = self._get_recent_swing_low(5)
        if abs(self.latest["low"] - recent_low) / recent_low > 0.015:  # 放宽到1.5%，原1%
            return None
        prev = self.df.iloc[-2]
        # 放量下跌条件放宽：成交量>2倍 或 恐慌量（原必须>3倍）
        if not (prev.get("volume_ratio", 0) >= VOLUME_RATIO_SIGNIFICANT and prev["close"] < prev["open"]):
            return None
        if prev["low"] < recent_low * (1 - STOP_BUFFER):
            return None
        # K线形态放宽：增加更多见底形态
        if not (prev.get("long_lower_shadow") or prev.get("hammer") or prev.get("doji") or prev.get("piercing")):
            return None
        # 当前K线确认放宽：阳线 或 收复前阴一半（原必须同时满足）
        if not (self.latest["close"] > self.latest["open"] or 
                self.latest["close"] > (prev["close"] + prev["open"]) / 2):
            return None
        
        entry = self.latest["close"]
        stop_loss = recent_low * (1 - STOP_BUFFER)
        target = entry + MIN_RISK_REWARD_RATIO * (entry - stop_loss)
        
        return {
            "direction": "LONG",
            "type": "陷阱诱空做多",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"关键支撑{recent_low:.2f}放量急跌不破，恐慌释放后收阳确认",
            "mnemonic": "放量急跌底不破，底背离现长脚线；恐慌释放即机会，企稳收阳反手多。"
        }

    def check_breakout_long(self):
        """横盘突破做多 - 修复：放宽横盘条件和突破条件"""
        if len(self.df) < RANGE_BAR_COUNT + 5:
            return None
        range_df = self.df.iloc[-RANGE_BAR_COUNT-1:-1]
        range_high = range_df["high"].max()
        range_low = range_df["low"].min()
        avg_price = (range_high + range_low) / 2
        
        # 修复：移除不合理的1.1倍限制（原逻辑自相矛盾）
        # 横盘区间高度检查
        if (range_high - range_low) / avg_price > RANGE_HEIGHT_RATIO:
            return None
        # 缩量检查放宽：均量<90%（已改配置）
        if range_df["volume_ratio"].mean() > VOLUME_RATIO_SHRINK_60:
            return None
        # MACD粘合检查
        if abs(range_df["dif"].mean() - range_df["dea"].mean()) / avg_price > MACD_CLOSE_RATIO:
            return None
        # 突破条件：收盘破高 且 (放量显著 或 MACD红柱)（放宽）
        if not (self.latest["close"] > range_high and 
                (self._is_volume_expanding(VOLUME_RATIO_SIGNIFICANT) or self.latest["macd_hist"] > 0)):
            return None
        
        entry = self.latest["close"]
        stop_loss = range_low * (1 - STOP_BUFFER)
        target = entry + MIN_RISK_REWARD_RATIO * (entry - stop_loss)
        
        return {
            "direction": "LONG",
            "type": "横盘突破做多",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"低位缩量横盘，放量突破{range_low:.2f}-{range_high:.2f}区间",
            "mnemonic": "缩量横盘低点托，MACD粘合小K线；谁先放量向上突，突破区间立即多。"
        }

    def check_trend_callback_short(self):
        """趋势反弹做空 - 修复：放宽条件，与做多对称"""
        if len(self.df) < 10 or self._check_trend() != "downtrend":
            return None
        if not self._is_volume_shrink(3):
            return None
        recent_high = self._get_recent_swing_high(5)
        if self.latest["high"] > recent_high * (1 + STOP_BUFFER):
            return None
        
        # MACD条件放宽：DIF<0 或 死叉（原为必须同时满足）
        macd_ok = self.latest["dif"] < 0 or self.latest["death_cross"]
        if not macd_ok:
            return None
            
        # K线形态放宽：增加更多见顶形态
        kline_ok = (self.latest.get("shooting_star") or 
                    self.latest.get("long_upper_shadow") or 
                    self.latest.get("gravestone") or
                    self.latest.get("dark_cloud") or
                    self.latest.get("bearish_engulfing"))
        if not kline_ok:
            return None
            
        # 价格行为放宽：阴线 且 (放量 或 破前低)（原必须同时满足）
        price_ok = (self.latest["close"] < self.latest["open"] and 
                    (self._is_volume_expanding(VOLUME_RATIO_MODERATE) or 
                     self.latest["close"] < self.df["low"].iloc[-2]))
        if not price_ok:
            return None
            
        # MACD柱放宽：<0 即可（原要求比前一根放大）
        if not (self.latest["macd_hist"] < 0):
            return None
        
        entry = self.latest["close"]
        stop_loss = recent_high * (1 + STOP_BUFFER)
        target = entry - MIN_RISK_REWARD_RATIO * (stop_loss - entry)
        
        return {
            "direction": "SHORT",
            "type": "趋势反弹做空",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"下降趋势缩量反弹不过前高，MACD死叉/DIF<0，{self._get_kline_pattern_names()}，放量/破低",
            "mnemonic": "缩量反弹顶不过，顶背离/死叉等放量；放量下跌破前低，绿柱出现直接空。"
        }

    def check_trap_short(self):
        """陷阱诱多做空 - 修复：放宽条件"""
        if len(self.df) < 5:
            return None
        recent_high = self._get_recent_swing_high(5)
        if abs(self.latest["high"] - recent_high) / recent_high > 0.015:  # 放宽到1.5%，原1%
            return None
        prev = self.df.iloc[-2]
        # 放量上涨条件放宽：成交量>2倍（原必须>3倍）
        if not (prev.get("volume_ratio", 0) >= VOLUME_RATIO_SIGNIFICANT and prev["close"] > prev["open"]):
            return None
        if prev["high"] > recent_high * (1 + STOP_BUFFER):
            return None
        # K线形态放宽：增加更多见顶形态
        if not (prev.get("long_upper_shadow") or prev.get("shooting_star") or prev.get("doji") or prev.get("dark_cloud")):
            return None
        # 当前K线确认放宽：阴线 或 跌破前阳一半（原必须同时满足）
        if not (self.latest["close"] < self.latest["open"] or 
                self.latest["close"] < (prev["close"] + prev["open"]) / 2):
            return None
        
        entry = self.latest["close"]
        stop_loss = recent_high * (1 + STOP_BUFFER)
        target = entry - MIN_RISK_REWARD_RATIO * (stop_loss - entry)
        
        return {
            "direction": "SHORT",
            "type": "陷阱诱多做空",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"关键阻力{recent_high:.2f}放量急涨不破，收阴确认",
            "mnemonic": "放量急涨顶不破，顶背离现长上影；多头陷阱莫追高，回落收阴反手空。"
        }

    def check_breakout_short(self):
        """横盘突破做空 - 修复：放宽条件"""
        if len(self.df) < RANGE_BAR_COUNT + 5:
            return None
        range_df = self.df.iloc[-RANGE_BAR_COUNT-1:-1]
        range_high = range_df["high"].max()
        range_low = range_df["low"].min()
        avg_price = (range_high + range_low) / 2

        # 修复：移除不合理的0.9倍限制
        # 横盘区间高度检查
        if (range_high - range_low) / avg_price > RANGE_HEIGHT_RATIO:
            return None
        # 缩量检查放宽
        if range_df["volume_ratio"].mean() > VOLUME_RATIO_SHRINK_60:
            return None
        # 突破条件：收盘破低 且 (放量显著 或 MACD绿柱)（放宽）
        if not (self.latest["close"] < range_low and 
                (self._is_volume_expanding(VOLUME_RATIO_SIGNIFICANT) or self.latest["macd_hist"] < 0)):
            return None

        entry = self.latest["close"]
        stop_loss = range_high * (1 + STOP_BUFFER)
        target = entry - MIN_RISK_REWARD_RATIO * (stop_loss - entry)

        return {
            "direction": "SHORT",
            "type": "横盘突破做空",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"高位缩量横盘，放量跌破{range_low:.2f}-{range_high:.2f}区间",
            "mnemonic": "缩量横盘高点压，MACD粘合小K线；谁先放量向下破，跌破区间立即空。"
        }

    def check_morning_star(self):
        """启明星形态：修复BUG，简化条件"""
        if len(self.df) < 3:
            return None
        k1 = self.df.iloc[-3]
        k2 = self.df.iloc[-2]
        k3 = self.latest
        
        # 修复：原条件恒为False，改为实体小于前10根平均实体的30%
        avg_body = self.df["body"].iloc[-10:].mean() if len(self.df) >= 10 else k1["body"]
        k2_body_small = k2["body"] < avg_body * 0.3
        
        # 条件：第一根阴线，第二根星线（实体小），第三根阳线收复
        if (k1["close"] < k1["open"] and  # 第一根阴线
            k2_body_small and  # 第二根星线实体小
            k3["close"] > k3["open"] and  # 第三根阳线
            k3["close"] > (k1["open"] + k1["close"]) / 2 and  # 收复第一根实体一半以上
            k3["volume_ratio"] >= 1.0):  # 第三根放量（放宽，原1.2）
            entry = k3["close"]
            stop_loss = min(k1["low"], k2["low"], k3["low"]) * (1 - STOP_BUFFER)
            target = entry + MIN_RISK_REWARD_RATIO * (entry - stop_loss)
            return {
                "direction": "LONG",
                "type": "启明星抄底",
                "entry": entry,
                "stop_loss": stop_loss,
                "target": target,
                "reason": "三K线形成启明星形态，放量确认，尝试抄底",
                "mnemonic": "下跌阴线后星线，再收阳线过一半，放量跟进抄底单"
            }
        return None

    def check_bullish_engulfing(self):
        """看涨吞没：放宽成交量条件"""
        if len(self.df) < 2:
            return None
        k1 = self.df.iloc[-2]
        k2 = self.latest
        if (k1["close"] < k1["open"] and  # 前一根阴线
            k2["close"] > k2["open"] and  # 当前阳线
            k2["open"] < k1["close"] and  # 阳线开盘低于前阴收盘
            k2["close"] > k1["open"] and  # 阳线收盘高于前阴开盘
            k2["volume_ratio"] >= 1.0):  # 放量放宽到1倍（原1.3）
            entry = k2["close"]
            stop_loss = min(k1["low"], k2["low"]) * (1 - STOP_BUFFER)
            target = entry + MIN_RISK_REWARD_RATIO * (entry - stop_loss)
            return {
                "direction": "LONG",
                "type": "看涨吞没",
                "entry": entry,
                "stop_loss": stop_loss,
                "target": target,
                "reason": "阳线完全覆盖前阴线，放量反转",
                "mnemonic": "阴线之后阳吞没，放量跟进做多单"
            }
        return None

    def check_evening_star(self):
        """黄昏星形态：修复BUG，简化条件"""
        if len(self.df) < 3:
            return None
        k1 = self.df.iloc[-3]
        k2 = self.df.iloc[-2]
        k3 = self.latest
        
        # 修复：原条件恒为False，改为实体小于前10根平均实体的30%
        avg_body = self.df["body"].iloc[-10:].mean() if len(self.df) >= 10 else k1["body"]
        k2_body_small = k2["body"] < avg_body * 0.3
        
        if (k1["close"] > k1["open"] and  # 第一根阳线
            k2_body_small and  # 第二根星线
            k3["close"] < k3["open"] and  # 第三根阴线
            k3["close"] < (k1["open"] + k1["close"]) / 2 and  # 跌破第一根实体一半
            k3["volume_ratio"] >= 1.0):  # 放宽，原1.2
            entry = k3["close"]
            stop_loss = max(k1["high"], k2["high"], k3["high"]) * (1 + STOP_BUFFER)
            target = entry - MIN_RISK_REWARD_RATIO * (stop_loss - entry)
            return {
                "direction": "SHORT",
                "type": "黄昏星做空",
                "entry": entry,
                "stop_loss": stop_loss,
                "target": target,
                "reason": "三K线形成黄昏星形态，放量确认",
                "mnemonic": "上涨阳线后星线，再收阴线破一半，放量跟进做空单"
            }
        return None

    def check_bearish_engulfing_new(self):
        """看跌吞没：放宽成交量条件"""
        if len(self.df) < 2:
            return None
        k1 = self.df.iloc[-2]
        k2 = self.latest
        if (k1["close"] > k1["open"] and  # 前一根阳线
            k2["close"] < k2["open"] and  # 当前阴线
            k2["open"] > k1["close"] and  # 阴线开盘高于前阳收盘
            k2["close"] < k1["open"] and  # 阴线收盘低于前阳开盘
            k2["volume_ratio"] >= 1.0):  # 放量放宽到1倍（原1.3）
            entry = k2["close"]
            stop_loss = max(k1["high"], k2["high"]) * (1 + STOP_BUFFER)
            target = entry - MIN_RISK_REWARD_RATIO * (stop_loss - entry)
            return {
                "direction": "SHORT",
                "type": "看跌吞没",
                "entry": entry,
                "stop_loss": stop_loss,
                "target": target,
                "reason": "阴线完全覆盖前阳线，放量反转",
                "mnemonic": "阳线之后阴吞没，放量跟进做空单"
            }
        return None

    def get_all_signals(self):
        """获取唯一信号 - 解决冲突"""
        long_funcs = [
            self.check_trend_callback_long,
            self.check_trap_long,
            self.check_breakout_long,
            # 新增形态信号
            self.check_morning_star,
            self.check_bullish_engulfing,
        ]
        short_funcs = [
            self.check_trend_callback_short,
            self.check_trap_short,
            self.check_breakout_short,
            # 新增形态信号
            self.check_evening_star,
            self.check_bearish_engulfing_new,
        ]
        
        long_signals = [f() for f in long_funcs if f() is not None]
        short_signals = [f() for f in short_funcs if f() is not None]
        
        # 计算各方向信号强度
        long_strength = sum(self._calculate_signal_strength("LONG") for _ in long_signals)
        short_strength = sum(self._calculate_signal_strength("SHORT") for _ in short_signals)
        
        # 信号冲突检测 - 选择更强的信号
        if long_signals and short_signals:
            if long_strength > short_strength:
                return long_signals[:1]  # 只返回一个做多信号
            elif short_strength > long_strength:
                return short_signals[:1]  # 只返回一个做空信号
            else:
                # 强度相同，返回冲突警告
                return [{
                    "direction": "CONFLICT",
                    "type": "信号冲突",
                    "reason": "多空信号强度相当，建议观望",
                    "mnemonic": "信号冲突则观望"
                }]
        
        # 无冲突，返回所有有效信号（通常只有一个）
        return long_signals + short_signals
