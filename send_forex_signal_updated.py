import os
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingClassifier
import joblib

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
LOOKAHEAD = 4
TP_RATIO = 0.004
SL_RATIO = 0.002
N_HOURS = 500
FEATURES = ["rsi", "macd"]

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_signal(pair, direction, entry, sl, tp, entry_time):
    exit_time = datetime.strptime(entry_time, "%Y-%m-%d %H:%M") + timedelta(hours=LOOKAHEAD)
    msg = f"""🚀 Торговый сигнал 🚀

Пара: {pair}
Направление: {direction}
Цена входа: {entry}
Стоп-лосс: {sl}
Тейк-профит: {tp}

Время входа: {entry_time}
Время выхода: {exit_time.strftime("%Y-%m-%d %H:%M")} (через {LOOKAHEAD} ч)
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def add_indicators(df):
    df["rsi"] = df["close"].diff().rolling(14).apply(
        lambda x: 100 - 100 / (1 + (x[x > 0].mean() / (-x[x < 0].mean() + 1e-6))), raw=False)
    df["ema"] = df["close"].ewm(span=12).mean()
    df["signal"] = df["close"].ewm(span=26).mean()
    df["macd"] = df["ema"] - df["signal"]
    return df.dropna()

model = joblib.load("forex_model.pkl")

best_signal = None
best_score = 0

for pair in PAIRS:
    df = yf.download(pair, interval="1h", period=f"{int(N_HOURS/24)+5}d")
    if len(df) < LOOKAHEAD + 10:
        continue
    df = df.reset_index()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    df = df[["datetime", "open", "high", "low", "close", "volume"]]
    df = add_indicators(df).reset_index(drop=True)

    for i in range(len(df) - LOOKAHEAD):
        row = df.iloc[i]
        X = row[FEATURES].values.reshape(1, -1)
        try:
            proba = model.predict_proba(X)[0]
        except:
            continue
        buy_score = proba[2]
        if buy_score > best_score:
            entry_price = row["close"]
            entry_time = row["datetime"].strftime("%Y-%m-%d %H:%M")
            sl = entry_price * (1 - SL_RATIO)
            tp = entry_price * (1 + TP_RATIO)
            best_signal = {
                "pair": pair.replace("=X", ""),
                "entry": f"{entry_price:.5f}",
                "sl": f"{sl:.5f}",
                "tp": f"{tp:.5f}",
                "time": entry_time,
                "direction": "BUY"
            }
            best_score = buy_score

if best_signal:
    send_signal(
        pair=best_signal["pair"],
        direction=best_signal["direction"],
        entry=best_signal["entry"],
        sl=best_signal["sl"],
        tp=best_signal["tp"],
        entry_time=best_signal["time"]
    )
else:
    print("⚠️ Сегодня сигналов не найдено.")
