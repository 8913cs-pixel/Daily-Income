import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram credentials")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=10)
        print("Signal sent to Telegram")
    except Exception as e:
        print("Telegram error:", e)


def get_data():
    df = yf.download("^GSPC", period="5d", interval="15m", progress=False, auto_adjust=True)
    
    if df.empty:
        return None

    # Fix MultiIndex columns (common with newer yfinance)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()
    return df


def calculate_indicators(df):
    df = df.copy()
    df["sma20"] = df["Close"].rolling(20).mean()
    df["sma50"] = df["Close"].rolling(50).mean()
    df["atr"] = (df["High"] - df["Low"]).rolling(14).mean()
    return df


def detect_regime(df):
    if len(df) < 50:
        return "UNKNOWN", 20.0

    last = df.iloc[-1]

    # Safe extraction of scalar values
    close = float(last["Close"]) if not isinstance(last["Close"], pd.Series) else float(last["Close"].iloc[0])
    sma20 = float(last["sma20"]) if not isinstance(last["sma20"], pd.Series) else float(last["sma20"].iloc[0])
    sma50 = float(last["sma50"]) if not isinstance(last["sma50"], pd.Series) else float(last["sma50"].iloc[0])
    
    atr_val = last["atr"]
    atr = float(atr_val) if not isinstance(atr_val, pd.Series) else float(atr_val.iloc[0])
    if pd.isna(atr):
        atr = 20.0

    recent_high = float(df["High"].tail(20).max())
    recent_low = float(df["Low"].tail(20).min())
    recent_range = (recent_high - recent_low) / close

    if close > sma20 > sma50 and recent_range > 0.012:
        return "TRENDING_BULL", atr
    elif close < sma20 < sma50 and recent_range > 0.012:
        return "TRENDING_BEAR", atr
    else:
        return "RANGING", atr


def generate_signal(regime, price, atr):
    price = round(float(price))
    atr = max(float(atr), 15)
    expected_move = round(atr * 1.8)

    if regime == "TRENDING_BULL":
        strike = price + round(atr * 0.4)
        return (
            f"📈 <b>Daily SPX Signal – TRENDING BULL</b>\n"
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Price: <b>{price}</b>\n\n"
            f"<b>Idea: Call</b>\n"
            f"Look ~{strike} Call (0DTE / weekly)\n"
            f"Expected move: ±{expected_move} pts"
        )

    elif regime == "TRENDING_BEAR":
        strike = price - round(atr * 0.4)
        return (
            f"📉 <b>Daily SPX Signal – TRENDING BEAR</b>\n"
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Price: <b>{price}</b>\n\n"
            f"<b>Idea: Put</b>\n"
            f"Look ~{strike} Put (0DTE / weekly)\n"
            f"Expected move: ±{expected_move} pts"
        )

    else:
        short_put = round((price - expected_move) / 5) * 5
        long_put = short_put - 25
        short_call = round((price + expected_move) / 5) * 5
        long_call = short_call + 25
        center = round(price / 5) * 5

        return (
            f"↔️ <b>Daily SPX Signal – RANGING</b>\n"
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Price: <b>{price}</b>\n"
            f"Expected range: ±{expected_move} pts\n\n"
            f"<b>Iron Condor Idea:</b>\n"
            f"Sell {short_put}P / Buy {long_put}P\n"
            f"Sell {short_call}C / Buy {long_call}C\n\n"
            f"<b>Butterfly Idea:</b>\n"
            f"Center {center} | Wings ±25"
        )


def main():
    print("Running daily SPX signal via GitHub Actions...")

    df = get_data()
    if df is None or df.empty:
        send_telegram("⚠️ Daily SPX Signal failed – no market data")
        return

    df = calculate_indicators(df)
    regime, atr = detect_regime(df)
    price = float(df["Close"].iloc[-1])

    signal = generate_signal(regime, price, atr)
    print(signal)
    send_telegram(signal)


if __name__ == "__main__":
    main()
