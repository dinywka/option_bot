import pandas as pd
import joblib
import yfinance as yf
from tqdm import tqdm
from datetime import datetime, timedelta
import numpy as np

# Конфигурация
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
RISK_REWARD_RATIO = 1.5
ATR_MULTIPLIER = 3.0
TEST_PERIOD_DAYS = 180  # 6 месяцев
COMMISSION = 0.0002


def get_test_dates():
    end_date = datetime.today()
    start_date = end_date - timedelta(days=TEST_PERIOD_DAYS)
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


def download_test_data(symbol, start_date, end_date):
    try:
        df = yf.download(
            symbol,
            start=start_date,
            end=end_date,
            interval="1h",
            auto_adjust=True,
            progress=False
        )
        if df.empty:
            print(f"Нет тестовых данных для {symbol}")
            return None

        return df[["Open", "High", "Low", "Close", "Volume"]].rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume"
        }).reset_index().rename(columns={"Datetime": "timestamp"})
    except Exception as e:
        print(f"Ошибка загрузки тестовых данных для {symbol}: {str(e)}")
        return None


def run_backtest():
    start_date, end_date = get_test_dates()
    print(f"\nБэктест за период: {start_date} - {end_date}")

    try:
        model = joblib.load("forex_model.pkl")
    except Exception as e:
        print(f"Ошибка загрузки модели: {str(e)}")
        return None

    results = []

    for pair in tqdm(PAIRS, desc="Backtesting pairs"):
        df = download_test_data(pair, start_date, end_date)
        if df is None:
            continue

        df = add_indicators(df)
        if df is None:
            continue

        for i in range(len(df) - 1):
            current = df.iloc[i]
            next_candle = df.iloc[i + 1]

            features = pd.DataFrame([[
                current["rsi"], current["macd"], current["ema_10"],
                current["ema_20"], current["adx"], current["bb_width"],
                current["atr"], current["stoch_rsi"]
            ]])

            try:
                pred = model.predict(features)[0]
                if pred == 0:
                    continue

                entry = current["close"]
                atr = current["atr"]

                if pred == 1:  # BUY
                    sl = entry - atr * ATR_MULTIPLIER
                    tp = entry + atr * ATR_MULTIPLIER * RISK_REWARD_RATIO
                else:  # SELL
                    sl = entry + atr * ATR_MULTIPLIER
                    tp = entry - atr * ATR_MULTIPLIER * RISK_REWARD_RATIO

                # Исполнение сделки
                if pred == 1:  # BUY
                    if next_candle["low"] <= sl:
                        pnl_pct = (sl - entry) / entry - COMMISSION * 2
                    elif next_candle["high"] >= tp:
                        pnl_pct = (tp - entry) / entry - COMMISSION * 2
                    else:
                        pnl_pct = (next_candle["close"] - entry) / entry - COMMISSION * 2
                else:  # SELL
                    if next_candle["high"] >= sl:
                        pnl_pct = (entry - sl) / entry - COMMISSION * 2
                    elif next_candle["low"] <= tp:
                        pnl_pct = (entry - tp) / entry - COMMISSION * 2
                    else:
                        pnl_pct = (entry - next_candle["close"]) / entry - COMMISSION * 2

                results.append({
                    "timestamp": current["timestamp"],
                    "pair": pair.replace("=X", ""),
                    "direction": "BUY" if pred == 1 else "SELL",
                    "entry": round(entry, 5),
                    "sl": round(sl, 5),
                    "tp": round(tp, 5),
                    "pnl_pct": round(pnl_pct * 100, 2),
                    "win": pnl_pct > 0
                })

            except Exception as e:
                print(f"Ошибка предсказания для {pair}: {str(e)}")

    return pd.DataFrame(results) if results else None


if __name__ == "__main__":
    results_df = run_backtest()
    if results_df is not None:
        analyze_results(results_df)
        results_df.to_csv("backtest_results.csv", index=False)
    else:
        print("Нет результатов для анализа")