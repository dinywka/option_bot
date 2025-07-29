#data/collect_bybit_data.py
import os
import pandas as pd
import time
from datetime import datetime, timedelta, timezone
from tqdm import tqdm
from pybit.unified_trading import HTTP

# Настройки
SYMBOLS = ["XRPUSDT"]
INTERVAL = 5  # минут
DAYS_TO_FETCH = 30
DATA_DIR = "bybit_data"
os.makedirs(DATA_DIR, exist_ok=True)

session = HTTP(testnet=False)


def calculate_expected_candles(days, interval):
    return (24 * 60 // interval) * days


def fetch_klines(symbol, interval=INTERVAL, days=DAYS_TO_FETCH):
    print(f"\n📥 Скачиваем {symbol} за {days} дней ({interval} минутные свечи)...")

    end_time = datetime.utcnow().replace(second=0, microsecond=0)
    start_time = (end_time - timedelta(days=days)).replace(second=0, microsecond=0)
    expected = calculate_expected_candles(days, interval)
    print(f"Ожидаемое количество свечей: {expected}")

    # Вычисляем сколько запросов нужно сделать
    candles_per_request = 200  # Безопасное значение для 5-минутного таймфрейма
    requests_needed = (expected // candles_per_request) + 1

    all_data = []

    with tqdm(total=requests_needed, desc=f"{symbol} ({interval}m)") as pbar:
        current_end = end_time
        for _ in range(requests_needed):
            try:
                # Вычисляем start_time для этого запроса
                current_start = current_end - timedelta(minutes=interval * candles_per_request)
                current_start = max(current_start, start_time)

                response = session.get_kline(
                    category="linear",
                    symbol=symbol,
                    interval=str(interval),
                    start=int(current_start.timestamp() * 1000),
                    end=int(current_end.timestamp() * 1000),
                    limit=candles_per_request
                )

                if not response or not response.get('result', {}).get('list'):
                    break

                candles = response['result']['list']

                df = pd.DataFrame(candles, columns=[
                    "timestamp", "open", "high", "low", "close", "volume", "turnover"
                ])

                df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
                for col in ["open", "high", "low", "close", "volume", "turnover"]:
                    df[col] = pd.to_numeric(df[col])

                all_data.append(df)
                pbar.update(1)

                # Обновляем current_end для следующего запроса
                if len(candles) > 0:
                    first_timestamp = pd.to_numeric(candles[0][0])
                    current_end = pd.to_datetime(first_timestamp, unit='ms')
                else:
                    break

                time.sleep(0.1)  # Защита от rate limit

            except Exception as e:
                print(f"\n⚠️ Ошибка: {str(e)}")
                break

    if all_data:
        final_df = pd.concat(all_data).drop_duplicates(subset=['timestamp'])
        final_df = final_df.sort_values('timestamp')
        final_df = final_df[(final_df['timestamp'] >= start_time) &
                            (final_df['timestamp'] <= end_time)]

        actual = len(final_df)
        print(f"\nПолучено свечей: {actual} (ожидалось {expected})")
        print(f"Покрытие периода: {final_df['timestamp'].min()} - {final_df['timestamp'].max()}")

        # Проверяем качество данных
        if actual > expected * 1.2:
            print("⚠️ Внимание: получено слишком много данных! Проверьте на дубликаты.")
        elif actual < expected * 0.8:
            print("⚠️ Внимание: получено слишком мало данных! Возможны пропуски.")

        filename = f"{symbol}_{interval}min.csv"
        filepath = os.path.join(DATA_DIR, filename)
        final_df.to_csv(filepath, index=False)
        print(f"✅ Сохранено: {filepath}")
    else:
        print("⚠️ Не удалось получить данные")


if __name__ == "__main__":
    print(f"🚀 Начинаем скачивание ({DAYS_TO_FETCH} дней, таймфрейм {INTERVAL} минут)")

    for symbol in SYMBOLS:
        try:
            fetch_klines(symbol)
        except Exception as e:
            print(f"Ошибка для {symbol}: {str(e)}")
            continue

    print("\n✅ Завершено!")




