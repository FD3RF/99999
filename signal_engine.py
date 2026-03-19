# signal_engine.py
import pandas as pd
import numpy as np
from datetime import datetime
from config import *

class SignalEngine:
    """
    交易信号识别引擎 - 完全按照终极完美多空口诀实现
    """

    def __init__(self, df):
        self.df = df
        self.latest = df.iloc[-1] if len(df) > 0 else None
        self.prev = df.iloc[-2] if len(df) > 1 else None
        self.signals = []

    # ---------- 辅助函数 ----------
    def _get_recent_swing_low(self, within=5):
        """获取最近的有效波段低点（within根内）"""
        recent_swings = self.df[self.df["swing_low"]].tail(within)
        if len(recent_swings) > 0:
            return recent_swings.iloc[-1]["low"]
        # 降级：取最近within根的最低价
        return self.df["low"].iloc[-within-1:-1].min()

    def _get_recent_swing_high(self, within=5):
        """获取最近的有效波段高点"""
        recent_swings = self.df[self.df["swing_high"]].tail(within)
        if len(recent_swings) > 0:
            return recent_swings.iloc[-1]["high"]
        return self.df["high"].iloc[-within-1:-1].max()

    def _is_volume_shrink(self, periods=3):
        """最近periods根K线是否缩量（均值 < 60%）"""
        vol_ratio = self.df["volume_ratio"].iloc[-periods:].mean()
        return vol_ratio < VOLUME_RATIO_SHRINK_60

    def _is_volume_expanding(self, threshold=VOLUME_RATIO_MODERATE):
        """当前K线是否放量"""
        return self.latest["volume_ratio"] >= threshold

    def _check_trend(self):
        """判断当前趋势（简单版本）"""
        if len(self.df) < 10:
            return "unknown"
        highs = self.df["high"].iloc[-10:].values
        lows = self.df["low"].iloc[-10:].values
        uptrend = all(highs[i] >= highs[i-1] for i in range(1, len(highs))) and \
                  all(lows[i] >= lows[i-1] for i in range(1, len(lows)))
        downtrend = all(highs[i] <= highs[i-1] for i in range(1, len(highs))) and \
                    all(lows[i] <= lows[i-1] for i in range(1, len(lows)))
        if uptrend:
            return "uptrend"
        elif downtrend:
            return "downtrend"
        return "ranging"

    def _get_kline_pattern_names(self):
        """获取当前K线形态名称列表"""
        names = []
        if self.latest.get("hammer"): names.append("锤子线")
        if self.latest.get("shooting_star"): names.append("流星线")
        if self.latest.get("doji"): names.append("十字星")
        if self.latest.get("long_lower_shadow"): names.append("长下影线")
        if self.latest.get("long_upper_shadow"): names.append("长上影线")
        if self.latest.get("gravestone"): names.append("墓碑线")
        if self.latest.get("piercing"): names.append("刺透形态")
        if self.latest.get("dark_cloud"): names.append("乌云盖顶")
        if self.latest.get("bullish_engulfing"): names.append("阳包阴")
        if self.latest.get("bearish_engulfing"): names.append("阴包阳")
        if self.latest.get("big_bull"): names.append("大阳线")
        if self.latest.get("big_bear"): names.append("大阴线")
        return ", ".join(names) if names else "普通K线"

    # ---------- 做多场景 ----------

    def check_trend_callback_long(self):
        """
        趋势回调做多
        口诀：缩量回踩底不破，底背离/金叉等放量；放量起涨破前高，红柱放大直接多。
        """
        if len(self.df) < 10:
            return None
        if self._check_trend() != "uptrend":
            return None

        # 1. 缩量回踩
        if not self._is_volume_shrink(3):
            return None

        # 2. 前低不破（用最近波段低点）
        recent_low = self._get_recent_swing_low(5)
        if self.latest["low"] < recent_low * (1 - STOP_BUFFER):
            return None

        # 3. MACD底背离或零上金叉
        # 底背离检测（简化：最近5根低点新低但DIF未新低）
        recent_lows = self.df["low"].iloc[-6:-1]
        recent_difs = self.df["dif"].iloc[-6:-1]
        if self.latest["low"] < recent_lows.min() and self.latest["dif"] > recent_difs.min():
            macd_ok = True
        elif self.latest["dif"] > 0 and self.latest["golden_cross"]:
            macd_ok = True
        else:
            macd_ok = False
        if not macd_ok:
            return None

        # 4. K线见底信号
        kline_ok = self.latest["hammer"] or self.latest["doji"] or self.latest["long_lower_shadow"]
        if not kline_ok:
            return None

        # 5. 放量起涨破前高（当前K线为阳线突破）
        if not (self.latest["close"] > self.latest["open"] and
                self._is_volume_expanding(VOLUME_RATIO_MODERATE) and
                self.latest["close"] > self.df["high"].iloc[-2]):  # 突破前一根高点
            return None

        # 6. 红柱放大
        if not (self.latest["macd_hist"] > 0 and
                self.latest["macd_hist"] > self.df["macd_hist"].iloc[-2]):
            return None

        # 计算止损目标
        entry = self.latest["close"]
        stop_loss = recent_low * (1 - STOP_BUFFER)
        stop_distance = entry - stop_loss
        target = entry + MIN_RISK_REWARD_RATIO * stop_distance

        return {
            "direction": "LONG",
            "type": "趋势回调做多",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"上升趋势缩量回踩前低{recent_low:.2f}不破，出现{self._get_kline_pattern_names()} + MACD信号，放量阳线突破",
            "mnemonic": "缩量回踩底不破，底背离/金叉等放量；放量起涨破前高，红柱放大直接多。"
        }

    def check_trap_long(self):
        """
        陷阱诱空做多
        口诀：放量急跌底不破，底背离现长脚线；恐慌释放即机会，企稳收阳反手多。
        """
        if len(self.df) < 5:
            return None

        # 1. 关键支撑附近（最近波段低点）
        recent_low = self._get_recent_swing_low(5)
        if abs(self.latest["low"] - recent_low) / recent_low > 0.01:
            return None

        # 2. 前一根（或几根）放量急跌
        prev = self.df.iloc[-2] if len(self.df) >= 2 else None
        if prev is None or not (prev["volume_ratio"] >= VOLUME_RATIO_PANIC and
                                prev["close"] < prev["open"]):
            return None

        # 3. 低点不破
        if prev["low"] < recent_low * (1 - STOP_BUFFER):
            return None

        # 4. MACD底背离
        # 简单检测：价格创新低但DIF未创新低（与更早比较）
        earlier_lows = self.df["low"].iloc[-10:-5]
        earlier_difs = self.df["dif"].iloc[-10:-5]
        if not (prev["low"] < earlier_lows.min() and prev["dif"] > earlier_difs.min()):
            return None

        # 5. K线长脚线（前一根长下影或锤子）
        if not (prev["long_lower_shadow"] or prev["hammer"]):
            return None

        # 6. 恐慌后企稳收阳确认（当前K线）
        if not (self.latest["close"] > self.latest["open"] and
                self.latest["close"] > (prev["close"] + prev["open"])/2):
            return None

        entry = self.latest["close"]
        stop_loss = recent_low * (1 - STOP_BUFFER)
        stop_distance = entry - stop_loss
        target = entry + MIN_RISK_REWARD_RATIO * stop_distance

        return {
            "direction": "LONG",
            "type": "陷阱诱空做多",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"关键支撑{recent_low:.2f}附近放量急跌不破，出现底背离+长脚线，收阳确认",
            "mnemonic": "放量急跌底不破，底背离现长脚线；恐慌释放即机会，企稳收阳反手多。"
        }

    def check_breakout_long(self):
        """
        横盘突破做多
        口诀：缩量横盘低点托，MACD粘合小K线；谁先放量向上突，突破区间立即多。
        """
        if len(self.df) < RANGE_BAR_COUNT + 5:
            return None

        # 取最近RANGE_BAR_COUNT根K线（不包含当前）作为横盘区间
        range_df = self.df.iloc[-RANGE_BAR_COUNT-1:-1]
        range_high = range_df["high"].max()
        range_low = range_df["low"].min()
        range_height = range_high - range_low
        avg_price = (range_high + range_low) / 2

        # 1. 低位横盘（当前位置在低位）
        if self.latest["close"] > avg_price * 1.1:  # 太高则不是低位
            return None

        # 2. 区间高度小于阈值
        if range_height / avg_price > RANGE_HEIGHT_RATIO:
            return None

        # 3. 缩量横盘
        vol_ratio_mean = range_df["volume_ratio"].mean()
        if vol_ratio_mean > VOLUME_RATIO_SHRINK_50:
            return None

        # 4. MACD粘合
        dif_mean = range_df["dif"].mean()
        dea_mean = range_df["dea"].mean()
        if abs(dif_mean - dea_mean) / avg_price > MACD_CLOSE_RATIO:
            return None

        # 5. 小K线
        body_mean = range_df["body"].mean()
        if body_mean > self.df["body"].iloc[-20:-10].mean():
            return None

        # 6. 突破信号（当前K线）
        if not (self.latest["close"] > range_high and
                self._is_volume_expanding(VOLUME_RATIO_SIGNIFICANT) and
                self.latest["macd_hist"] > 0 and
                self.latest["macd_hist"] > self.df["macd_hist"].iloc[-2]):
            return None

        entry = self.latest["close"]
        stop_loss = range_low * (1 - STOP_BUFFER)
        stop_distance = entry - stop_loss
        target = entry + MIN_RISK_REWARD_RATIO * stop_distance

        return {
            "direction": "LONG",
            "type": "横盘突破做多",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"低位缩量横盘（区间{range_low:.2f}-{range_high:.2f}），放量突破上沿，MACD红柱放大",
            "mnemonic": "缩量横盘低点托，MACD粘合小K线；谁先放量向上突，突破区间立即多。"
        }

    def check_trend_continuation_long(self):
        """
        趋势延续做多（追涨）
        口诀：强势上涨中，放量阳线创新高，MACD红柱持续放大，K线饱满无影线，下一根开盘追多。
        """
        if len(self.df) < 3:
            return None
        if self._check_trend() != "uptrend":
            return None

        # 当前K线
        if not (self.latest["close"] > self.latest["open"] and
                self.latest["high"] > self.df["high"].iloc[-3:-1].max() and
                self._is_volume_expanding(VOLUME_RATIO_SIGNIFICANT) and
                self.latest["big_bull"]):
            return None

        # MACD红柱持续放大
        hist = self.df["macd_hist"].iloc[-3:].values
        if not (hist[0] > 0 and hist[1] > 0 and hist[2] > 0 and
                hist[1] > hist[0] and hist[2] > hist[1]):
            return None

        # 下一根开盘追多（这里给出预警，入场价设为当前收盘，实际应在下一根开盘）
        entry = self.latest["close"]
        stop_loss = self.latest["low"] * (1 - STOP_BUFFER)
        stop_distance = entry - stop_loss
        target = entry + MIN_RISK_REWARD_RATIO * stop_distance

        return {
            "direction": "LONG",
            "type": "趋势延续做多（追涨预警）",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": "强势上涨中放量阳线创新高，MACD红柱持续放大，K线饱满，下一根开盘追多",
            "mnemonic": "强势上涨中，放量阳线创新高，MACD红柱持续放大，K线饱满无影线，下一根开盘追多。"
        }

    # ---------- 做空场景 ----------

    def check_trend_callback_short(self):
        """
        趋势反弹做空
        口诀：缩量反弹顶不过，顶背离/死叉等放量；放量下跌破前低，绿柱放大直接空。
        """
        if len(self.df) < 10:
            return None
        if self._check_trend() != "downtrend":
            return None

        # 1. 缩量反弹
        if not self._is_volume_shrink(3):
            return None

        # 2. 前高不过
        recent_high = self._get_recent_swing_high(5)
        if self.latest["high"] > recent_high * (1 + STOP_BUFFER):
            return None

        # 3. MACD顶背离或零下死叉
        recent_highs = self.df["high"].iloc[-6:-1]
        recent_difs = self.df["dif"].iloc[-6:-1]
        if self.latest["high"] > recent_highs.max() and self.latest["dif"] < recent_difs.max():
            macd_ok = True
        elif self.latest["dif"] < 0 and self.latest["death_cross"]:
            macd_ok = True
        else:
            macd_ok = False
        if not macd_ok:
            return None

        # 4. K线见顶信号
        kline_ok = self.latest["shooting_star"] or self.latest["long_upper_shadow"] or self.latest["gravestone"]
        if not kline_ok:
            return None

        # 5. 放量跌破前低（当前K线阴线跌破）
        if not (self.latest["close"] < self.latest["open"] and
                self._is_volume_expanding(VOLUME_RATIO_MODERATE) and
                self.latest["close"] < self.df["low"].iloc[-2]):
            return None

        # 6. 绿柱放大
        if not (self.latest["macd_hist"] < 0 and
                abs(self.latest["macd_hist"]) > abs(self.df["macd_hist"].iloc[-2])):
            return None

        entry = self.latest["close"]
        stop_loss = recent_high * (1 + STOP_BUFFER)
        stop_distance = stop_loss - entry
        target = entry - MIN_RISK_REWARD_RATIO * stop_distance

        return {
            "direction": "SHORT",
            "type": "趋势反弹做空",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"下降趋势缩量反弹前高{recent_high:.2f}不过，出现{self._get_kline_pattern_names()} + MACD信号，放量阴线跌破",
            "mnemonic": "缩量反弹顶不过，顶背离/死叉等放量；放量下跌破前低，绿柱放大直接空。"
        }

    def check_trap_short(self):
        """
        陷阱诱多做空
        口诀：放量急涨顶不破，顶背离现长上影；多头陷阱莫追高，回落收阴反手空。
        """
        if len(self.df) < 5:
            return None

        recent_high = self._get_recent_swing_high(5)
        if abs(self.latest["high"] - recent_high) / recent_high > 0.01:
            return None

        prev = self.df.iloc[-2]
        if not (prev["volume_ratio"] >= VOLUME_RATIO_PANIC and
                prev["close"] > prev["open"]):
            return None

        if prev["high"] > recent_high * (1 + STOP_BUFFER):
            return None

        earlier_highs = self.df["high"].iloc[-10:-5]
        earlier_difs = self.df["dif"].iloc[-10:-5]
        if not (prev["high"] > earlier_highs.max() and prev["dif"] < earlier_difs.max()):
            return None

        if not (prev["long_upper_shadow"] or prev["shooting_star"]):
            return None

        if not (self.latest["close"] < self.latest["open"] and
                self.latest["close"] < (prev["close"] + prev["open"])/2):
            return None

        entry = self.latest["close"]
        stop_loss = recent_high * (1 + STOP_BUFFER)
        stop_distance = stop_loss - entry
        target = entry - MIN_RISK_REWARD_RATIO * stop_distance

        return {
            "direction": "SHORT",
            "type": "陷阱诱多做空",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"关键阻力{recent_high:.2f}附近放量急涨不破，出现顶背离+长上影，收阴确认",
            "mnemonic": "放量急涨顶不破，顶背离现长上影；多头陷阱莫追高，回落收阴反手空。"
        }

    def check_breakout_short(self):
        """
        横盘突破做空
        口诀：缩量横盘高点压，MACD粘合小K线；谁先放量向下破，跌破区间立即空。
        """
        if len(self.df) < RANGE_BAR_COUNT + 5:
            return None

        range_df = self.df.iloc[-RANGE_BAR_COUNT-1:-1]
        range_high = range_df["high"].max()
        range_low = range_df["low"].min()
        range_height = range_high - range_low
        avg_price = (range_high + range_low) / 2

        # 高位横盘
        if self.latest["close"] < avg_price * 0.9:
            return None

        if range_height / avg_price > RANGE_HEIGHT_RATIO:
            return None

        vol_ratio_mean = range_df["volume_ratio"].mean()
        if vol_ratio_mean > VOLUME_RATIO_SHRINK_50:
            return None

        dif_mean = range_df["dif"].mean()
        dea_mean = range_df["dea"].mean()
        if abs(dif_mean - dea_mean) / avg_price > MACD_CLOSE_RATIO:
            return None

        body_mean = range_df["body"].mean()
        if body_mean > self.df["body"].iloc[-20:-10].mean():
            return None

        if not (self.latest["close"] < range_low and
                self._is_volume_expanding(VOLUME_RATIO_SIGNIFICANT) and
                self.latest["macd_hist"] < 0 and
                abs(self.latest["macd_hist"]) > abs(self.df["macd_hist"].iloc[-2])):
            return None

        entry = self.latest["close"]
        stop_loss = range_high * (1 + STOP_BUFFER)
        stop_distance = stop_loss - entry
        target = entry - MIN_RISK_REWARD_RATIO * stop_distance

        return {
            "direction": "SHORT",
            "type": "横盘突破做空",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"高位缩量横盘（区间{range_low:.2f}-{range_high:.2f}），放量跌破下沿，MACD绿柱放大",
            "mnemonic": "缩量横盘高点压，MACD粘合小K线；谁先放量向下破，跌破区间立即空。"
        }

    def check_trend_continuation_short(self):
        """
        趋势延续做空（追跌）
        口诀：强势下跌中，放量阴线创新低，MACD绿柱持续放大，K线饱满无影线，下一根开盘追空。
        """
        if len(self.df) < 3:
            return None
        if self._check_trend() != "downtrend":
            return None

        if not (self.latest["close"] < self.latest["open"] and
                self.latest["low"] < self.df["low"].iloc[-3:-1].min() and
                self._is_volume_expanding(VOLUME_RATIO_SIGNIFICANT) and
                self.latest["big_bear"]):
            return None

        hist = self.df["macd_hist"].iloc[-3:].values
        if not (hist[0] < 0 and hist[1] < 0 and hist[2] < 0 and
                abs(hist[1]) > abs(hist[0]) and abs(hist[2]) > abs(hist[1])):
            return None

        entry = self.latest["close"]
        stop_loss = self.latest["high"] * (1 + STOP_BUFFER)
        stop_distance = stop_loss - entry
        target = entry - MIN_RISK_REWARD_RATIO * stop_distance

        return {
            "direction": "SHORT",
            "type": "趋势延续做空（追跌预警）",
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "reason": "强势下跌中放量阴线创新低，MACD绿柱持续放大，K线饱满，下一根开盘追空",
            "mnemonic": "强势下跌中，放量阴线创新低，MACD绿柱持续放大，K线饱满无影线，下一根开盘追空。"
        }

    # ---------- 主入口 ----------
    def get_all_signals(self):
        """获取所有信号，并处理冲突"""
        long_funcs = [
            self.check_trend_callback_long,
            self.check_trap_long,
            self.check_breakout_long,
            self.check_trend_continuation_long
        ]
        short_funcs = [
            self.check_trend_callback_short,
            self.check_trap_short,
            self.check_breakout_short,
            self.check_trend_continuation_short
        ]

        long_signals = [f() for f in long_funcs if f() is not None]
        short_signals = [f() for f in short_funcs if f() is not None]

        # 信号冲突：多空同时出现 -> 严禁交易
        if long_signals and short_signals:
            return [{
                "direction": "CONFLICT",
                "type": "信号冲突",
                "reason": f"同时出现{len(long_signals)}个做多信号和{len(short_signals)}个做空信号，市场极度纠结，严禁交易。",
                "mnemonic": "信号冲突则观望，连续止损即休息。"
            }]
        # 返回所有信号（通常只有一个方向）
        return long_signals + short_signals
