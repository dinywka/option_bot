#strategies/volume_filter.py
import pandas_ta as ta
from datetime import datetime
from config.settings import *
from strategies.base_strategy import BaseStrategy


class VolumeFilterStrategy(BaseStrategy):
    def __init__(self, df):
        super().__init__()
        self.df = self.preprocess_data(df)

    def generate_signal(self):
        if not self._is_valid_time():
            print("⏳ Неподходящее время для торговли")
            return None

        last_volume = self.df['volume'].iloc[-1]
        if last_volume < MIN_VOLUME:
            print(f"📉 Объем слишком низкий: {last_volume} < {MIN_VOLUME}")
            return None

        sma20 = ta.sma(self.df['close'], length=20)
        rsi = ta.rsi(self.df['close'], length=14)

        print(f"🔍 Цена: {self.df['close'].iloc[-1]}, SMA20: {sma20.iloc[-1]}, RSI: {rsi.iloc[-1]}")

        if self.df['close'].iloc[-1] > sma20.iloc[-1] and rsi.iloc[-1] < 30:
            return "BUY"
        elif self.df['close'].iloc[-1] < sma20.iloc[-1] and rsi.iloc[-1] > 70:
            return "SELL"

        print("🚫 Нет сигнала")
        return None

    def _is_valid_time(self):
        hour = datetime.now().hour
        return hour not in BLACKLIST_HOURS

    def analyze(self):
        pass  # Или реализация по желанию

    def calculate_risk(self):
        return 0.02  # Например, фиксированный риск 2%


