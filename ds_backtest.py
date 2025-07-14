import pandas as pd
import joblib
import yfinance as yf
from tqdm import tqdm
from datetime import datetime, timedelta
from ta import add_all_ta_features
import numpy as np

# Конфигурация
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
RISK_REWARD_RATIO = 1.5
ATR_MULTIPLIER = 3.0
COMMISSION = 0.0002
TEST_PERIOD_DAYS = 180  # 6 месяцев


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


def calculate_indicators(df):
    """Расчет индикаторов (исправленное название)"""
    try:
        if df is None or len(df) < 20:
            return None

        # Создаем копию для расчетов
        df_ta = df.copy().set_index('timestamp')

        # Добавляем индикаторы
        df_ta = add_all_ta_features(
            df_ta,
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            fillna=True
        )

        # Выбираем нужные фичи
        selected_features = [
            'trend_macd_diff',
            'trend_ema_fast',
            'trend_ema_slow',
            'trend_adx',
            'volatility_bbw',
            'volatility_atr',
            'momentum_rsi',
            'momentum_stoch_rsi'
        ]

        # Возвращаем к исходному формату
        df_ta = df_ta[selected_features].reset_index()
        df = pd.merge(df, df_ta, on='timestamp', how='left')

        return df.dropna()
    except Exception as e:
        print(f"Ошибка расчета индикаторов: {str(e)}")
        return None


def analyze_results(df):
    if df.empty:
        print("Нет сделок для анализа")
        return

    print("\n" + "=" * 50)
    print(f"📊 Итоги бэктеста ({df['timestamp'].min().date()} - {df['timestamp'].max().date()})")
    print("=" * 50)

    # Общая статистика
    total_trades = len(df)
    win_rate = round(df["win"].mean() * 100, 2)
    total_pnl = round(df["pnl_pct"].sum(), 2)
    avg_trade = round(df["pnl_pct"].mean(), 2)

    # Просадка
    cum_pnl = df["pnl_pct"].cumsum()
    max_drawdown = round((cum_pnl.cummax() - cum_pnl).max(), 2)

    print(f"\n🔹 Всего сделок: {total_trades}")
    print(f"🔹 Win Rate: {win_rate}%")
    print(f"🔹 Общий PnL: {total_pnl}%")
    print(f"🔹 Средний PnL за сделку: {avg_trade}%")
    print(f"🔹 Макс. просадка: {max_drawdown}%")

    # По парам
    print("\n📈 По торговым парам:")
    pair_stats = df.groupby("pair").agg({
        "pnl_pct": "sum",
        "win": "mean",
        "direction": "count"
    }).rename(columns={
        "pnl_pct": "TotalPnL%",
        "win": "WinRate",
        "direction": "Trades"
    })
    print(pair_stats.round(2))

    # Последние 5 сделок
    print("\n🔄 Последние 5 сделок:")
    print(df[["timestamp", "pair", "direction", "entry", "pnl_pct"]].tail(5))


def run_backtest():
    start_date, end_date = get_test_dates()
    print(f"\nБэктест за период: {start_date} - {end_date}")

    try:
        model = joblib.load("forex_model.pkl")
    except Exception as e:
        print(f"Ошибка загрузки модели: {str(e)}")
        return None

    results = []
    features = [
        'momentum_rsi',
        'trend_macd_diff',
        'trend_ema_fast',
        'trend_ema_slow',
        'trend_adx',
        'volatility_bbw',
        'volatility_atr',
        'momentum_stoch_rsi'
    ]

    for pair in tqdm(PAIRS, desc="Backtesting pairs"):
        df = download_test_data(pair, start_date, end_date)
        if df is None:
            continue

        df = calculate_indicators(df)  # Исправленное название функции
        if df is None:
            continue

        for i in range(len(df) - 1):
            current = df.iloc[i]
            next_candle = df.iloc[i + 1]

            try:
                pred = model.predict([current[features]])[0]
                if pred == 0:
                    continue

                entry = current["close"]
                atr = current["volatility_atr"]

                if pred == 1:  # BUY
                    sl = entry - atr * ATR_MULTIPLIER
                    tp = entry + atr * ATR_MULTIPLIER * RISK_REWARD_RATIO

                    if next_candle["low"] <= sl:
                        pnl_pct = (sl - entry) / entry - COMMISSION * 2
                    elif next_candle["high"] >= tp:
                        pnl_pct = (tp - entry) / entry - COMMISSION * 2
                    else:
                        pnl_pct = (next_candle["close"] - entry) / entry - COMMISSION * 2
                else:  # SELL
                    sl = entry + atr * ATR_MULTIPLIER
                    tp = entry - atr * ATR_MULTIPLIER * RISK_REWARD_RATIO

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