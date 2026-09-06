import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# ====================== YOUR CREDENTIALS ======================
TELEGRAM_TOKEN = "8476521995:AAErD42IIM3Y8MhtplQDq_Lt1Xdh9LrMHBk"
TELEGRAM_CHAT_ID = "5106218895"
# =============================================================


def send_telegram(msg: str):
    print("Sending message to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=15)

        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Message sent successfully!")
        else:
            print("❌ Failed:", response.text)
    except Exception as e:
        print(f"❌ Error: {e}")


def get_data():
    print("Downloading SPX data...")
    df = yf.download("^GSPC", period="5d", interval="15m", progress=False, auto_adjust=True)

    if df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()
    print(f"Data rows: {len(df)}")
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
    close = float(last["Close"])
    sma20 = float(last["sma20"]) if not pd.isna(last["sma20"]) else close
    sma50 = float(last["sma50"]) if not pd.isna(last["sma50"]) else close
    atr = float(last["atr"]) if not pd.isna(last["atr"]) else 20.0

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

    # Common strikes
    short_put = round((price - expected_move) / 5) * 5
    long_put = short_put - 25
    short_call = round((price + expected_move) / 5) * 5
    long_call = short_call + 25
    center = round(price / 5) * 5

    # Inverse strikes (closer wings for reverse structures)
    inv_long_put = round((price - expected_move * 0.6) / 5) * 5
    inv_short_put = inv_long_put - 25
    inv_long_call = round((price + expected_move * 0.6) / 5) * 5
    inv_short_call = inv_long_call + 25

    if regime == "TRENDING_BULL":
        strike = price + round(atr * 0.4)
        return (
            f"📈 <b>Daily SPX Signal – TRENDING BULL</b>\n"
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Price: <b>{price}</b>\n\n"
            f"<b>Main Idea: Call</b>\n"
            f"Look ~{strike} Call (0DTE / weekly)\n"
            f"Expected move: ±{expected_move} pts"
        )

    elif regime == "TRENDING_BEAR":
        strike = price - round(atr * 0.4)
        return (
            f"📉 <b>Daily SPX Signal – TRENDING BEAR</b>\n"
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Price: <b>{price}</b>\n\n"
            f"<b>Main Idea: Put</b>\n"
            f"Look ~{strike} Put (0DTE / weekly)\n"
            f"Expected move: ±{expected_move} pts"
        )

    else:
        # RANGING – show both normal + inverse strategies
        return (
            f"↔️ <b>Daily SPX Signal – RANGING</b>\n"
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Price: <b>{price}</b>\n"
            f"Expected range: ±{expected_move} pts\n\n"

            f"<b>1. Iron Condor (Credit)</b>\n"
            f"Sell {short_put}P / Buy {long_put}P\n"
            f"Sell {short_call}C / Buy {long_call}C\n\n"

            f"<b>2. Butterfly (Debit)</b>\n"
            f"Center {center} | Wings ±25\n\n"

            f"<b>3. Inverse Iron Condor (Debit)</b>\n"
            f"Buy {inv_long_put}P / Sell {inv_short_put}P\n"
            f"Buy {inv_long_call}C / Sell {inv_short_call}C\n"
            f"(Profits from big move in either direction)\n\n"

            f"<b>4. Inverse Butterfly (Debit)</b>\n"
            f"Sell Center {center} | Buy Wings ±25\n"
            f"(Profits from strong expansion)"
        )


def main():
    print("=== Starting Daily SPX Signal ===")

    send_telegram("🔔 <b>Bot Started</b>\nGenerating daily SPX ideas...")

    df = get_data()
    if df is None or df.empty:
        send_telegram("⚠️ Failed to get market data")
        return

    df = calculate_indicators(df)
    regime, atr = detect_regime(df)
    price = float(df["Close"].iloc[-1])

    print(f"Regime: {regime} | Price: {price} | ATR: {atr:.1f}")

    signal = generate_signal(regime, price, atr)
    print(signal)
    send_telegram(signal)


if __name__ == "__main__":
    main()
