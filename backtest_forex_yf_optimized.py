
import pandas as pd
import joblib
import yfinance as yf
from tqdm import tqdm
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
FEATURES = ["rsi", "macd", "ema_10", "ema_20", "bb_high", "bb_low", "volume_ema"]
LOOKAHEAD = 4
COMMISSION = 0.0002
START_DATE = "2025-01-01"
END_DATE = "2025-07-01"
LIMIT_ROWS = 1000  # Ограничим свечи на пару

def download_data(symbol):
    df = yf.download(symbol, start=START_DATE, end=END_DATE, interval="1h", progress=False)
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
results = []

# Обработка всех пар
for pair in tqdm(PAIRS, desc="🔍 Обрабатываем пары"):
    df = download_data(pair)
    df = add_indicators(df)
    df.dropna(inplace=True)

    for i in range(len(df) - LOOKAHEAD):
        row = df.iloc[i]
        X = row[FEATURES].values.reshape(1, -1)
        try:
            proba = model.predict_proba(X)[0]
        except Exception as e:
            print(f"❌ Ошибка в predict_proba для {pair} @ {row['timestamp']}: {e}")
            continue

        pred = model.predict(X)[0]
        if pred == 0:
            continue

        entry = row["close"]
        exit_price = df.iloc[i + LOOKAHEAD]["close"]
        direction = "BUY" if pred == 1 else "SELL"

        if direction == "BUY":
            pnl = (exit_price - entry) / entry
        else:
            pnl = (entry - exit_price) / entry

        pnl -= COMMISSION * 2

        results.append({
            "timestamp": row["timestamp"],
            "pair": pair,
            "direction": direction,
            "entry": round(entry, 5),
            "exit": round(exit_price, 5),
            "pnl_%": round(pnl * 100, 2),
            "win": pnl > 0
        })

# Вывод результатов
results_df = pd.DataFrame(results)
if results_df.empty:
    print("⚠️ Нет сделок за период.")
else:
    winrate = round(results_df['win'].mean() * 100, 2)
    pnl_sum = round(results_df["pnl_%"].sum(), 2)
    max_dd = round(results_df["pnl_%"].cumsum().cummax().sub(results_df["pnl_%"].cumsum()).max(), 2)

    print(f"📊 Результаты бэктеста по {len(PAIRS)} парам:")
    print(f"Сделок: {len(results_df)}")
    print(f"WinRate: {winrate}%")
    print(f"PnL: {pnl_sum}%")
    print(f"Max Drawdown: {max_dd}%")
    print("\nПоследние 5 сделок:")
    print(results_df.tail(5)[["timestamp", "pair", "direction", "entry", "exit", "pnl_%"]])
