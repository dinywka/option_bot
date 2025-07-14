
import pandas as pd
import numpy as np
import joblib
import yfinance as yf
from datetime import datetime
from sklearn.ensemble import GradientBoostingClassifier
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands

# ==== Настройки ====
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
LOOKAHEAD = 4  # часов
THRESHOLD = 0.001  # 0.1%
START_DATE = "2025-01-01"
END_DATE = "2025-07-14"

def download_data(symbol):
    df = yf.download(symbol, start=START_DATE, end=END_DATE, interval="1h", progress=False)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "volume"]
    df.reset_index(inplace=True)
    df.rename(columns={"Datetime": "timestamp"}, inplace=True)
    return df

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

def generate_labels(df):
    df["future_return"] = df["close"].shift(-LOOKAHEAD) / df["close"] - 1
    df["label"] = 0
    df.loc[df["future_return"] > THRESHOLD, "label"] = 1
    df.loc[df["future_return"] < -THRESHOLD, "label"] = -1
    return df

def build_dataset():
    all_data = []
    for pair in PAIRS:
        df = download_data(pair)
        df = add_indicators(df)
        df = generate_labels(df)
        df["pair"] = pair
        all_data.append(df)
    full_df = pd.concat(all_data, ignore_index=True)
    full_df.dropna(inplace=True)
    return full_df

def train_model(df):
    FEATURES = ["rsi", "macd", "ema_10", "ema_20", "bb_high", "bb_low", "volume_ema"]
    X = df[FEATURES]
    y = df["label"]
    model = GradientBoostingClassifier()
    model.fit(X, y)
    joblib.dump(model, "forex_model.pkl")
    print("✅ Модель обучена и сохранена как 'forex_model.pkl'")

if __name__ == "__main__":
    df = build_dataset()
    df.to_csv("forex_dataset.csv", index=False)
    train_model(df)
