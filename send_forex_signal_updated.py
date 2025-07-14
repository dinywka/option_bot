import os
import time
import joblib
import requests
import yfinance as yf
import pandas as pd
from tqdm import tqdm
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands
from dotenv import load_dotenv
from datetime import datetime

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Константы
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
FEATURES = ["rsi", "macd", "ema_10", "ema_20", "bb_high", "bb_low", "volume_ema"]
LOOKAHEAD = 4
COMMISSION = 0.0002
LIMIT_ROWS = 1000

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Ошибка отправки в Telegram:", e)

def download_data(symbol):
    df = yf.download(symbol, period="30d", interval="1h", progress=False)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "volume"]
    df.reset_index(inplace=True)
    df.rename(columns={"Datetime": "timestamp"}, inplace=True)
    return df.tail(LIMIT_ROWS)

def add_indicators(df):
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    df["macd"] = MACD(df["close"]).macd_diff()
    df["ema_10"] = EMAIndicator(df["close"], window=10).ema_indicator()
    df["ema_20"] = EMAIndicator(df["close"], window=20).ema_indicator()
    bb = BollingerBands(df["close"])
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()
    df["volume_ema"] = df["volume"].ewm(span=14).mean()
    return df

# Загрузка модели
model = joblib.load("forex_model.pkl")

def run_signal_bot():
    for pair in PAIRS:
        df = download_data(pair)
        df = add_indicators(df)
        df.dropna(inplace=True)
        row = df.iloc[-LOOKAHEAD]  # последний вход перед будущей ценой
        X = row[FEATURES].values.reshape(1, -1)

        try:
            pred = model.predict(X)[0]
        except Exception as e:
            print(f"Ошибка в модели для {pair}: {e}")
            continue

        if pred == 0:
            continue  # Пропускаем, если нет сигнала

        direction = "BUY" if pred == 1 else "SELL"
        entry = row["close"]

        # SL и TP можно настраивать как соотношение 1:2
        sl_pips = 0.0025 if "JPY" not in pair else 0.25
        tp_pips = sl_pips * 2

        sl = entry - sl_pips if direction == "BUY" else entry + sl_pips
        tp = entry + tp_pips if direction == "BUY" else entry - tp_pips

        message = (
            f"🚀 <b>Торговый сигнал</b> 🚀\n\n"
            f"Пара: <b>{pair.replace('=X', '')}</b>\n"
            f"Направление: <b>{direction}</b>\n"
            f"Цена входа: <b>{entry:.5f}</b>\n"
            f"Стоп-лосс: <b>{sl:.5f}</b>\n"
            f"Тейк-профит: <b>{tp:.5f}</b>\n\n"
            f"Время: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"#Forex #Trading #Signals"
        )
        send_telegram_message(message)
        print("✅ Сигнал отправлен:", message)

# Запуск каждый час
if __name__ == "__main__":
    while True:
        print(f"⏰ Запуск проверки сигналов — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
        run_signal_bot()
        time.sleep(3600)  # Ждем 1 час
