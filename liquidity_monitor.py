import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import pandas as pd
import requests

SYMBOL = "ETHUSDT"
INTERVAL = "15m"
LOOKBACK = 20
SCAN_BUFFER_SECONDS = 3
COOLDOWN_HOURS = 4
PANIC_VOL_RATIO = 1.8
REQUEST_TIMEOUT = 10

BINANCE_FUTURES_KLINES = "https://fapi.binance.com/fapi/v1/klines"


def fetch_futures_klines(symbol: str = SYMBOL, interval: str = INTERVAL, limit: int = 120) -> pd.DataFrame:
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(BINANCE_FUTURES_KLINES, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    raw = resp.json()

    df = pd.DataFrame(
        raw,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "num_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ],
    )

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    return df


def calculate_rsi(series: pd.Series, period: int = 6) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calculate_parabolic_sar(
    highs: pd.Series,
    lows: pd.Series,
    step: float = 0.02,
    max_step: float = 0.2,
) -> pd.DataFrame:
    n = len(highs)
    if n < 3:
        return pd.DataFrame({"sar": [None] * n, "trend_up": [None] * n, "flip": [False] * n})

    sar = [None] * n
    trend_up = [True] * n
    flip = [False] * n

    if highs.iloc[1] >= highs.iloc[0]:
        trend = True
        ep = highs.iloc[1]
        sar_val = lows.iloc[0]
    else:
        trend = False
        ep = lows.iloc[1]
        sar_val = highs.iloc[0]

    af = step
    sar[0] = sar_val
    trend_up[0] = trend

    for i in range(1, n):
        prev_sar = sar_val
        sar_val = prev_sar + af * (ep - prev_sar)

        if trend:
            sar_val = min(sar_val, lows.iloc[i - 1], lows.iloc[i - 2] if i > 1 else lows.iloc[i - 1])
            if lows.iloc[i] < sar_val:
                trend = False
                flip[i] = True
                sar_val = ep
                ep = lows.iloc[i]
                af = step
            else:
                if highs.iloc[i] > ep:
                    ep = highs.iloc[i]
                    af = min(af + step, max_step)
        else:
            sar_val = max(sar_val, highs.iloc[i - 1], highs.iloc[i - 2] if i > 1 else highs.iloc[i - 1])
            if highs.iloc[i] > sar_val:
                trend = True
                flip[i] = True
                sar_val = ep
                ep = highs.iloc[i]
                af = step
            else:
                if lows.iloc[i] < ep:
                    ep = lows.iloc[i]
                    af = min(af + step, max_step)

        sar[i] = sar_val
        trend_up[i] = trend

    return pd.DataFrame({"sar": sar, "trend_up": trend_up, "flip": flip})


def liquidity_signal(df: pd.DataFrame) -> Dict[str, Optional[dict]]:
    if len(df) < LOOKBACK + 5:
        return {"log": "NO LIQUIDITY EVENT", "signal": None}

    work = df.copy()
    work["rsi6"] = calculate_rsi(work["close"], period=6)
    vol_ma20 = work["volume"].rolling(20, min_periods=1).mean()
    work["volume_ratio"] = work["volume"] / vol_ma20.clip(lower=1e-9)

    sar_df = calculate_parabolic_sar(work["high"], work["low"])
    work = pd.concat([work, sar_df], axis=1)

    current = work.iloc[-1]
    recent = work.iloc[-(LOOKBACK + 1):-1]
    recent_low = recent["low"].min()
    recent_high = recent["high"].max()

    swept_low = current["low"] < recent_low
    recovered = current["close"] > recent_low
    swept_high = current["high"] > recent_high
    faded = current["close"] < recent_high

    vol_panic_down = (current["close"] < current["open"]) and (current["volume_ratio"] >= PANIC_VOL_RATIO)
    vol_panic_up = (current["close"] > current["open"]) and (current["volume_ratio"] >= PANIC_VOL_RATIO)

    if swept_low and recovered and current["rsi6"] < 30 and bool(current["flip"]) and bool(current["trend_up"]) and vol_panic_down:
        entry_low, entry_high = current["close"] - 2, current["close"] + 2
        sweep_extreme = current["low"]
        stop = sweep_extreme * (1 - 0.005)
        tp1 = current["close"] * (1 + 0.008)
        tp2 = current["close"] * (1 + 0.015)
        rr1 = (tp1 - current["close"]) / (current["close"] - stop)
        rr2 = (tp2 - current["close"]) / (current["close"] - stop)

        strength = min(max((recent_low - sweep_extreme) / recent_low * 10000, 80), 95)
        msg = (
            "🟢 ETH LIQUIDITY SWEEP LONG\n\n"
            f"Entry:\n{entry_low:.2f} - {entry_high:.2f}\n\n"
            f"Stop Loss:\n{stop:.2f}\n\n"
            f"Take Profit:\nTP1 {tp1:.2f}\nTP2 {tp2:.2f}\n\n"
            f"Risk/Reward:\nTP1 1:{rr1:.2f} | TP2 1:{rr2:.2f}\n\n"
            "Plan:\n扫低恐慌后反转\n不追跌，只做回收\n\n"
            f"Confidence:\n{strength:.1f}"
        )
        return {"log": "LIQUIDITY LONG", "signal": {"direction": "LONG", "message": msg}}

    if swept_high and faded and current["rsi6"] > 70 and bool(current["flip"]) and (not bool(current["trend_up"])) and vol_panic_up:
        entry_low, entry_high = current["close"] - 2, current["close"] + 2
        sweep_extreme = current["high"]
        stop = sweep_extreme * (1 + 0.005)
        tp1 = current["close"] * (1 - 0.008)
        tp2 = current["close"] * (1 - 0.015)
        rr1 = (current["close"] - tp1) / (stop - current["close"])
        rr2 = (current["close"] - tp2) / (stop - current["close"])

        strength = min(max((sweep_extreme - recent_high) / recent_high * 10000, 80), 95)
        msg = (
            "🔴 ETH LIQUIDITY SWEEP SHORT\n\n"
            f"Entry:\n{entry_low:.2f} - {entry_high:.2f}\n\n"
            f"Stop Loss:\n{stop:.2f}\n\n"
            f"Take Profit:\nTP1 {tp1:.2f}\nTP2 {tp2:.2f}\n\n"
            f"Risk/Reward:\nTP1 1:{rr1:.2f} | TP2 1:{rr2:.2f}\n\n"
            "Plan:\n扫高诱多后反杀\n不追涨，只做回落\n\n"
            f"Confidence:\n{strength:.1f}"
        )
        return {"log": "LIQUIDITY SHORT", "signal": {"direction": "SHORT", "message": msg}}

    return {"log": "NO LIQUIDITY EVENT", "signal": None}


def send_bark(message: str) -> None:
    bark_url = os.getenv("BARK_URL", "").strip()
    if not bark_url:
        return
    requests.get(bark_url, params={"title": "ETH Liquidity Alert", "body": message}, timeout=REQUEST_TIMEOUT)


def send_telegram(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=REQUEST_TIMEOUT)


def next_close_after(now: datetime, minutes: int = 15) -> datetime:
    minute_bucket = (now.minute // minutes + 1) * minutes
    if minute_bucket >= 60:
        dt = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        dt = now.replace(minute=minute_bucket, second=0, microsecond=0)
    return dt


def run_monitor() -> None:
    print("ETHUSDT 永续流动性猎杀监控启动（15m，仅提醒不下单）")
    last_closed_candle_time: Optional[pd.Timestamp] = None
    last_signal_at: Dict[str, datetime] = {"LONG": datetime.min.replace(tzinfo=timezone.utc), "SHORT": datetime.min.replace(tzinfo=timezone.utc)}

    while True:
        now = datetime.now(timezone.utc)
        target = next_close_after(now, 15) + timedelta(seconds=SCAN_BUFFER_SECONDS)
        sleep_seconds = max((target - now).total_seconds(), 1)
        time.sleep(sleep_seconds)

        try:
            df = fetch_futures_klines(limit=120)
            closed = df.iloc[:-1]  # 最后一根通常是未收盘K线
            if closed.empty:
                print("NO LIQUIDITY EVENT")
                continue

            latest_closed_time = closed.iloc[-1]["close_time"]
            if last_closed_candle_time is not None and latest_closed_time <= last_closed_candle_time:
                continue

            last_closed_candle_time = latest_closed_time
            result = liquidity_signal(closed)
            log_text = result["log"]
            signal = result["signal"]

            if signal is None:
                print(log_text)
                continue

            direction = signal["direction"]
            if datetime.now(timezone.utc) - last_signal_at[direction] < timedelta(hours=COOLDOWN_HOURS):
                print("NO LIQUIDITY EVENT")
                continue

            message = signal["message"]
            print(log_text)
            print(message)

            send_bark(message)
            send_telegram(message)
            last_signal_at[direction] = datetime.now(timezone.utc)
        except Exception as exc:
            print(f"NO LIQUIDITY EVENT\nError: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    run_monitor()
