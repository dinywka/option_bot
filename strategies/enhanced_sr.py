# # strategies/enhanced_sr.py
#
# import pandas as pd
# import numpy as np
# from strategies.base_strategy import BaseStrategy
#
#
# class EnhancedSRStrategy(BaseStrategy):
#     def __init__(self, df=None):
#         super().__init__()
#         if df is not None:
#             self.df = self.preprocess_data(df)
#         else:
#             self.df = None
#
#         super().__init__()
#
#     def generate_signal(self, data):
#         """
#         Точка входа: принимает df и возвращает 'BUY', 'SELL' или None.
#         """
#         return self.analyze(data)
#
#     def analyze(self, df):
#         """
#         Анализ уровней поддержки/сопротивления на основе данных.
#         """
#         df = df.copy()
#         if len(df) < 30:
#             self.logger.warning("Недостаточно данных для анализа.")
#             return None
#
#         last_close = df['close'].iloc[-1]
#         recent_lows = df['low'].rolling(20).min().iloc[-1]
#         recent_highs = df['high'].rolling(20).max().iloc[-1]
#
#         support = recent_lows
#         resistance = recent_highs
#
#         signal = None
#         if last_close <= support * 1.01:
#             signal = "BUY"
#         elif last_close >= resistance * 0.99:
#             signal = "SELL"
#
#         self.logger.info(f"[ANALYZE] Close: {last_close}, Support: {support}, Resistance: {resistance}, Signal: {signal}")
#         return signal
#
#     def calculate_risk(self, df):
#         """
#         Вычисляет уровни SL/TP и риск %.
#         """
#         df = df.copy()
#         last_close = df['close'].iloc[-1]
#         support = df['low'].rolling(20).min().iloc[-1]
#         resistance = df['high'].rolling(20).max().iloc[-1]
#
#         signal = self.analyze(df)
#         sl = None
#         tp = None
#
#         if signal == "BUY":
#             sl = support
#             risk_pct = abs((last_close - sl) / last_close)
#             tp = last_close + (last_close - sl) * 1.6
#         elif signal == "SELL":
#             sl = resistance
#             risk_pct = abs((sl - last_close) / last_close)
#             tp = last_close - (sl - last_close) * 1.6
#         else:
#             return {"stop_loss": None, "take_profit": None, "risk_pct": 0.0}
#
#         return {
#             "stop_loss": round(sl, 2),
#             "take_profit": round(tp, 2),
#             "risk_pct": round(risk_pct, 4)
#         }
#
#     def calculate_stop_loss_take_profit(self, df, direction, entry_price, window=20, sl_buffer=0.001, tp_multiplier=1.6):
#         """
#         Определяет SL и TP по ближайшим экстремумам.
#         """
#         recent = df.iloc[-window:]
#
#         if direction == 'long':
#             sl_level = recent['low'].min() - sl_buffer * entry_price
#             sl_distance = entry_price - sl_level
#             tp_level = entry_price + sl_distance * tp_multiplier
#
#         elif direction == 'short':
#             sl_level = recent['high'].max() + sl_buffer * entry_price
#             sl_distance = sl_level - entry_price
#             tp_level = entry_price - sl_distance * tp_multiplier
#
#         else:
#             raise ValueError("Направление должно быть 'long' или 'short'.")
#
#         return round(sl_level, 2), round(tp_level, 2)


# strategies/enhanced_sr.py

import pandas as pd
import numpy as np
from strategies.base_strategy import BaseStrategy

class EnhancedSRStrategy(BaseStrategy):
    def __init__(self, df=None):
        super().__init__()
        self.df = self.preprocess_data(df) if df is not None else None
        self.last_signal_time = None  # фильтр входа по времени
#для backtest
    # def generate_signal(self, df):
    #     return self.analyze(df)

    def generate_signal(self, df):
        direction = self.analyze(df)
        if not direction:
            return None

        entry_price = df['close'].iloc[-1]
        position = "long" if direction.lower() == "buy" else "short"
        sl, tp = self.calculate_stop_loss_take_profit(df, position, entry_price)

        return {
            "signal": direction,
            "entry": entry_price,
            "sl": sl,
            "tp": tp
        }

    def analyze(self, df):
        df = df.copy()
        if len(df) < 60:
            self.logger.warning("❌ Недостаточно данных (<60)")
            return None

        # Фильтр тренда (SMA-50)
        sma_50 = df['close'].rolling(50).mean()
        trend = sma_50.iloc[-1]
        price = df['close'].iloc[-1]

        # Фильтр объема
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        curr_volume = df['volume'].iloc[-1]
        if curr_volume < avg_volume:
            self.logger.info("📉 Объем ниже среднего — нет сигнала")
            return None

        # Фильтр волатильности
        vol = df['close'].rolling(20).std().iloc[-1]
        if vol < 0.002 * price:
            self.logger.info("😴 Волатильность низкая — боковик")
            return None

        # Поддержка / сопротивление
        recent_lows = df['low'].rolling(20).min().iloc[-1]
        recent_highs = df['high'].rolling(20).max().iloc[-1]

        support = recent_lows
        resistance = recent_highs

        signal = None

        # BUY: цена у поддержки, и выше SMA (по тренду)
        if price <= support * 1.01 and price > trend:
            signal = "BUY"

        # SELL: цена у сопротивления, и ниже SMA
        elif price >= resistance * 0.99 and price < trend:
            signal = "SELL"

        self.logger.info(f"[ANALYZE] close={price:.2f}, SMA50={trend:.2f}, vol={curr_volume:.0f}, "
                         f"support={support:.2f}, resistance={resistance:.2f}, signal={signal}")
        return signal

    def calculate_risk(self, df):
        price = df['close'].iloc[-1]
        support = df['low'].rolling(20).min().iloc[-1]
        resistance = df['high'].rolling(20).max().iloc[-1]
        signal = self.analyze(df)

        sl = None
        tp = None

        if signal == "BUY":
            sl = support
            risk_pct = abs((price - sl) / price)
            tp = price + (price - sl) * 1.6
        elif signal == "SELL":
            sl = resistance
            risk_pct = abs((sl - price) / price)
            tp = price - (sl - price) * 1.6
        else:
            return {"stop_loss": None, "take_profit": None, "risk_pct": 0.0}

        return {
            "stop_loss": round(sl, 2),
            "take_profit": round(tp, 2),
            "risk_pct": round(risk_pct, 4)
        }

    def calculate_stop_loss_take_profit(self, df, direction, entry_price, window=20, sl_buffer=0.001, tp_multiplier=1.6):
        """
        SL/TP по экстремумам.
        """
        recent = df.iloc[-window:]
        if direction == "long":
            sl = recent['low'].min() - sl_buffer * entry_price
            tp = entry_price + (entry_price - sl) * tp_multiplier
        elif direction == "short":
            sl = recent['high'].max() + sl_buffer * entry_price
            tp = entry_price - (sl - entry_price) * tp_multiplier
        else:
            raise ValueError("Направление должно быть 'long' или 'short'.")

        return round(sl, 2), round(tp, 2)

