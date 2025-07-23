# data/load_binance_csv.py
import pandas as pd
import os


def load_csv_data(symbol: str, data_dir="data") -> pd.DataFrame:
    file_path = os.path.join(data_dir, f"{symbol}.csv")

    try:
        df = pd.read_csv(file_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        return df
    except Exception as e:
        print(f"❌ Ошибка при загрузке {file_path}: {e}")
        return pd.DataFrame()
