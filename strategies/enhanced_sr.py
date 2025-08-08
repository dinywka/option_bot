# # # strategies/enhanced_sr.py
# #
# # import pandas as pd
# # import numpy as np
# # from strategies.base_strategy import BaseStrategy
# #
# #
# # class EnhancedSRStrategy(BaseStrategy):
# #     def __init__(self, df=None):
# #         super().__init__()
# #         if df is not None:
# #             self.df = self.preprocess_data(df)
# #         else:
# #             self.df = None
# #
# #         super().__init__()
# #
# #     def generate_signal(self, data):
# #         """
# #         Точка входа: принимает df и возвращает 'BUY', 'SELL' или None.
# #         """
# #         return self.analyze(data)
# #
# #     def analyze(self, df):
# #         """
# #         Анализ уровней поддержки/сопротивления на основе данных.
# #         """
# #         df = df.copy()
# #         if len(df) < 30:
# #             self.logger.warning("Недостаточно данных для анализа.")
# #             return None
# #
# #         last_close = df['close'].iloc[-1]
# #         recent_lows = df['low'].rolling(20).min().iloc[-1]
# #         recent_highs = df['high'].rolling(20).max().iloc[-1]
# #
# #         support = recent_lows
# #         resistance = recent_highs
# #
# #         signal = None
# #         if last_close <= support * 1.01:
# #             signal = "BUY"
# #         elif last_close >= resistance * 0.99:
# #             signal = "SELL"
# #
# #         self.logger.info(f"[ANALYZE] Close: {last_close}, Support: {support}, Resistance: {resistance}, Signal: {signal}")
# #         return signal
# #
# #     def calculate_risk(self, df):
# #         """
# #         Вычисляет уровни SL/TP и риск %.
# #         """
# #         df = df.copy()
# #         last_close = df['close'].iloc[-1]
# #         support = df['low'].rolling(20).min().iloc[-1]
# #         resistance = df['high'].rolling(20).max().iloc[-1]
# #
# #         signal = self.analyze(df)
# #         sl = None
# #         tp = None
# #
# #         if signal == "BUY":
# #             sl = support
# #             risk_pct = abs((last_close - sl) / last_close)
# #             tp = last_close + (last_close - sl) * 1.6
# #         elif signal == "SELL":
# #             sl = resistance
# #             risk_pct = abs((sl - last_close) / last_close)
# #             tp = last_close - (sl - last_close) * 1.6
# #         else:
# #             return {"stop_loss": None, "take_profit": None, "risk_pct": 0.0}
# #
# #         return {
# #             "stop_loss": round(sl, 2),
# #             "take_profit": round(tp, 2),
# #             "risk_pct": round(risk_pct, 4)
# #         }
# #
# #     def calculate_stop_loss_take_profit(self, df, direction, entry_price, window=20, sl_buffer=0.001, tp_multiplier=1.6):
# #         """
# #         Определяет SL и TP по ближайшим экстремумам.
# #         """
# #         recent = df.iloc[-window:]
# #
# #         if direction == 'long':
# #             sl_level = recent['low'].min() - sl_buffer * entry_price
# #             sl_distance = entry_price - sl_level
# #             tp_level = entry_price + sl_distance * tp_multiplier
# #
# #         elif direction == 'short':
# #             sl_level = recent['high'].max() + sl_buffer * entry_price
# #             sl_distance = sl_level - entry_price
# #             tp_level = entry_price - sl_distance * tp_multiplier
# #
# #         else:
# #             raise ValueError("Направление должно быть 'long' или 'short'.")
# #
# #         return round(sl_level, 2), round(tp_level, 2)
#
#
# # strategies/enhanced_sr.py
#
# import pandas as pd
# import numpy as np
# from strategies.base_strategy import BaseStrategy
#
# class EnhancedSRStrategy(BaseStrategy):
#     def __init__(self, df=None):
#         super().__init__()
#         self.df = self.preprocess_data(df) if df is not None else None
#         self.last_signal_time = None  # фильтр входа по времени
# #для backtest
#     # def generate_signal(self, df):
#     #     return self.analyze(df)
#
#     def generate_signal(self, df):
#         direction = self.analyze(df)
#         if not direction:
#             return None
#
#         entry_price = df['close'].iloc[-1]
#         position = "long" if direction.lower() == "buy" else "short"
#         sl, tp = self.calculate_stop_loss_take_profit(df, position, entry_price)
#
#         return {
#             "signal": direction,
#             "entry": entry_price,
#             "sl": sl,
#             "tp": tp
#         }
#
#     def analyze(self, df):
#         df = df.copy()
#         if len(df) < 60:
#             self.logger.warning("❌ Недостаточно данных (<60)")
#             return None
#
#         # Фильтр тренда (SMA-50)
#         sma_50 = df['close'].rolling(50).mean()
#         trend = sma_50.iloc[-1]
#         price = df['close'].iloc[-1]
#
#         # Фильтр объема
#         avg_volume = df['volume'].rolling(20).mean().iloc[-1]
#         curr_volume = df['volume'].iloc[-1]
#         if curr_volume < avg_volume:
#             self.logger.info("📉 Объем ниже среднего — нет сигнала")
#             return None
#
#         # Фильтр волатильности
#         vol = df['close'].rolling(20).std().iloc[-1]
#         if vol < 0.002 * price:
#             self.logger.info("😴 Волатильность низкая — боковик")
#             return None
#
#         # Поддержка / сопротивление
#         recent_lows = df['low'].rolling(20).min().iloc[-1]
#         recent_highs = df['high'].rolling(20).max().iloc[-1]
#
#         support = recent_lows
#         resistance = recent_highs
#
#         signal = None
#
#         # BUY: цена у поддержки, и выше SMA (по тренду)
#         if price <= support * 1.01 and price > trend:
#             signal = "BUY"
#
#         # SELL: цена у сопротивления, и ниже SMA
#         elif price >= resistance * 0.99 and price < trend:
#             signal = "SELL"
#
#         self.logger.info(f"[ANALYZE] close={price:.2f}, SMA50={trend:.2f}, vol={curr_volume:.0f}, "
#                          f"support={support:.2f}, resistance={resistance:.2f}, signal={signal}")
#         return signal
#
#     def calculate_risk(self, df):
#         price = df['close'].iloc[-1]
#         support = df['low'].rolling(20).min().iloc[-1]
#         resistance = df['high'].rolling(20).max().iloc[-1]
#         signal = self.analyze(df)
#
#         sl = None
#         tp = None
#
#         if signal == "BUY":
#             sl = support
#             risk_pct = abs((price - sl) / price)
#             tp = price + (price - sl) * 1.6
#         elif signal == "SELL":
#             sl = resistance
#             risk_pct = abs((sl - price) / price)
#             tp = price - (sl - price) * 1.6
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
#         SL/TP по экстремумам.
#         """
#         recent = df.iloc[-window:]
#         if direction == "long":
#             sl = recent['low'].min() - sl_buffer * entry_price
#             tp = entry_price + (entry_price - sl) * tp_multiplier
#         elif direction == "short":
#             sl = recent['high'].max() + sl_buffer * entry_price
#             tp = entry_price - (sl - entry_price) * tp_multiplier
#         else:
#             raise ValueError("Направление должно быть 'long' или 'short'.")
#
#         return round(sl, 2), round(tp, 2)
#



# strategies/enhanced_sr.py
# Добавлен cooldown (по умолчанию 15 минут) — запрет на повторный вход по символу.
#
# Добавлены проверки SL < Entry при BUY, SL > Entry при SELL.
#
# Встроен фильтр по RSI:
#
# при BUY, если RSI > 60 — сигнал не генерируется;
#
# при SELL, если RSI < 40 — тоже игнорируется.
#
# Фильтр по объему и волатильности остался.
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy

# strategies/enhanced_sr_fixed.py
import pandas as pd
import numpy as np
import logging


class EnhancedSRStrategy:
    """
    ИСПРАВЛЕННАЯ версия стратегии Enhanced SR

    Основные изменения:
    1. Упрощены условия: 3 из 5 вместо 5 из 7
    2. Расширены диапазоны RSI
    3. Исправлена обработка NaN в RSI
    4. Улучшена проверка данных
    5. Добавлены fallback значения
    """

    def __init__(self, data=None):
        self.logger = logging.getLogger('EnhancedSRStrategyFixed')
        self.data = data

    def generate_signal(self, data):
        """
        ИСПРАВЛЕННАЯ генерация торгового сигнала
        """
        try:
            # ИСПРАВЛЕНИЕ 1: Правильная проверка данных
            if data is None:
                self.logger.warning("❌ Данные равны None")
                return None

            if data.empty:  # Правильная проверка пустого DataFrame
                self.logger.warning("❌ DataFrame пустой")
                return None

            if len(data) < 20:  # Уменьшено с 50 до 20
                self.logger.warning(f"❌ Недостаточно данных: {len(data)}")
                return None

            # Проверяем наличие необходимых колонок
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                self.logger.error(f"❌ Отсутствуют колонки: {missing_cols}")
                return None

            self.logger.debug(f"✅ Анализ данных: {len(data)} свечей")

            # Основная логика стратегии
            try:
                # Рассчитываем технические индикаторы
                data = self._calculate_indicators(data.copy())

                # Определяем уровни поддержки/сопротивления
                support_resistance = self._find_support_resistance_improved(data)

                # Генерируем сигнал с УПРОЩЕННЫМИ условиями
                signal = self._generate_trading_signal_improved(data, support_resistance)

                if signal:
                    self.logger.info(f"📊 Сигнал сгенерирован: {signal}")
                else:
                    self.logger.debug("📊 Сигнал не найден")

                return signal

            except Exception as e:
                self.logger.error(f"❌ Ошибка в логике стратегии: {e}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка в generate_signal: {e}")
            return None

    def _calculate_indicators(self, data):
        """ИСПРАВЛЕННЫЙ расчет технических индикаторов"""
        try:
            # EMA с защитой от ошибок
            try:
                data['ema_20'] = data['close'].ewm(span=20, adjust=False).mean()
                data['ema_50'] = data['close'].ewm(span=50, adjust=False).mean()
            except Exception as e:
                self.logger.warning(f"EMA calculation failed: {e}")
                # Fallback: используем простую скользящую среднюю
                data['ema_20'] = data['close'].rolling(20, min_periods=1).mean()
                data['ema_50'] = data['close'].rolling(50, min_periods=1).mean()

            # ИСПРАВЛЕНИЕ 2: RSI с защитой от деления на ноль
            data['rsi'] = self._calculate_rsi_fixed(data['close'], 14)

            # Bollinger Bands с защитой
            try:
                data['bb_middle'] = data['close'].rolling(20, min_periods=1).mean()
                bb_std = data['close'].rolling(20, min_periods=1).std()
                data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
                data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
            except Exception as e:
                self.logger.warning(f"Bollinger Bands failed: {e}")
                # Fallback: простые уровни
                current_price = data['close'].iloc[-1]
                data['bb_middle'] = current_price
                data['bb_upper'] = current_price * 1.02
                data['bb_lower'] = current_price * 0.98

            # Volume analysis с защитой
            try:
                data['volume_sma'] = data['volume'].rolling(20, min_periods=1).mean()
                data['volume_ratio'] = data['volume'] / (data['volume_sma'] + 1e-10)  # Защита от деления на ноль
            except Exception as e:
                self.logger.warning(f"Volume analysis failed: {e}")
                data['volume_ratio'] = 1.0  # Fallback

            # Заполняем NaN значения
            numeric_columns = ['ema_20', 'ema_50', 'rsi', 'bb_middle', 'bb_upper', 'bb_lower', 'volume_ratio']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = data[col].fillna(method='bfill').fillna(method='ffill')

            return data

        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета индикаторов: {e}")
            raise

    def _calculate_rsi_fixed(self, prices, period=14):
        """ИСПРАВЛЕННЫЙ расчет RSI с защитой от всех ошибок"""
        try:
            if len(prices) < period:
                # Недостаточно данных - возвращаем нейтральный RSI
                return pd.Series([50.0] * len(prices), index=prices.index)

            delta = prices.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()

            # ИСПРАВЛЕНИЕ: Защита от деления на ноль
            rs = gain / (loss + 1e-10)  # Добавляем маленькое число для избежания деления на ноль
            rsi = 100 - (100 / (1 + rs))

            # Заполняем NaN и проверяем диапазон
            rsi = rsi.fillna(50.0)  # Заполняем средним значением
            rsi = rsi.clip(0, 100)  # Ограничиваем диапазон 0-100

            return rsi

        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета RSI: {e}")
            # Возвращаем нейтральный RSI в случае ошибки
            return pd.Series([50.0] * len(prices), index=prices.index)

    def _find_support_resistance_improved(self, data):
        """УЛУЧШЕННЫЙ поиск уровней поддержки и сопротивления"""
        try:
            current_price = data['close'].iloc[-1]

            # Используем более простой и надежный подход
            recent_data = data.tail(min(50, len(data)))  # Последние 50 или все доступные свечи

            # Поддержка - минимум последних 20 свечей + отступ
            # Сопротивление - максимум последних 20 свечей + отступ
            lookback = min(20, len(recent_data))

            support_base = recent_data['low'].tail(lookback).min()
            resistance_base = recent_data['high'].tail(lookback).max()

            # Добавляем отступы для безопасности
            support = support_base * 0.998  # 0.2% ниже минимума
            resistance = resistance_base * 1.002  # 0.2% выше максимума

            # Проверяем разумность уровней
            if support >= current_price:
                support = current_price * 0.985  # 1.5% ниже текущей цены

            if resistance <= current_price:
                resistance = current_price * 1.015  # 1.5% выше текущей цены

            return {
                'support': support,
                'resistance': resistance,
                'current_price': current_price
            }

        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска S/R: {e}")
            # Fallback значения
            current_price = data['close'].iloc[-1]
            return {
                'support': current_price * 0.985,
                'resistance': current_price * 1.015,
                'current_price': current_price
            }

    def _generate_trading_signal_improved(self, data, sr_levels):
        """
        КАРДИНАЛЬНО УПРОЩЕННАЯ генерация торгового сигнала

        ОСНОВНЫЕ ИЗМЕНЕНИЯ:
        1. Только 5 условий вместо 7
        2. Требуется 3 из 5 вместо 5 из 7
        3. Расширенные диапазоны RSI
        4. Упрощенная логика
        """
        try:
            # Получаем данные с защитой от ошибок
            last_row = data.iloc[-1]
            current_price = sr_levels['current_price']

            # Безопасное получение значений с fallback
            rsi = last_row.get('rsi', 50.0)
            ema_20 = last_row.get('ema_20', current_price)
            ema_50 = last_row.get('ema_50', current_price)
            volume_ratio = last_row.get('volume_ratio', 1.0)

            # Проверяем валидность данных
            if pd.isna(rsi) or rsi < 0 or rsi > 100:
                rsi = 50.0
            if pd.isna(ema_20):
                ema_20 = current_price
            if pd.isna(ema_50):
                ema_50 = current_price
            if pd.isna(volume_ratio) or volume_ratio <= 0:
                volume_ratio = 1.0

            self.logger.debug(
                f"Анализ сигнала: RSI={rsi:.1f}, EMA20={ema_20:.2f}, EMA50={ema_50:.2f}, Vol={volume_ratio:.2f}")

            # УПРОЩЕННЫЕ условия для BUY (5 условий, нужно 3)
            buy_conditions = [
                rsi < 60,  # РАСШИРЕНО: было 25-45, стало <60
                current_price > ema_20,  # Цена выше EMA20
                ema_20 >= ema_50 * 0.999,  # EMA тренд вверх (с допуском)
                current_price > sr_levels['support'] * 1.001,  # Выше поддержки
                volume_ratio > 0.8  # УПРОЩЕНО: был 1.5, стал 0.8
            ]

            # УПРОЩЕННЫЕ условия для SELL (5 условий, нужно 3)
            sell_conditions = [
                rsi > 40,  # РАСШИРЕНО: было 55-75, стало >40
                current_price < ema_20,  # Цена ниже EMA20
                ema_20 <= ema_50 * 1.001,  # EMA тренд вниз (с допуском)
                current_price < sr_levels['resistance'] * 0.999,  # Ниже сопротивления
                volume_ratio > 0.8  # УПРОЩЕНО: был 1.5, стал 0.8
            ]

            # Подсчет выполненных условий
            buy_score = sum(buy_conditions)
            sell_score = sum(sell_conditions)

            self.logger.debug(f"Счет условий: BUY={buy_score}/5, SELL={sell_score}/5")

            # ГЛАВНОЕ ИЗМЕНЕНИЕ: требуем только 3 из 5 условий (было 5 из 7)
            if buy_score >= 3:
                signal = self._create_buy_signal_improved(current_price, sr_levels)
                if signal:
                    signal['conditions_met'] = f"{buy_score}/5"
                    self.logger.info(f"🟢 BUY сигнал: условий выполнено {buy_score}/5")
                return signal

            elif sell_score >= 3:
                signal = self._create_sell_signal_improved(current_price, sr_levels)
                if signal:
                    signal['conditions_met'] = f"{sell_score}/5"
                    self.logger.info(f"🔴 SELL сигнал: условий выполнено {sell_score}/5")
                return signal

            else:
                self.logger.debug(f"Недостаточно условий: BUY={buy_score}/5, SELL={sell_score}/5 (нужно 3)")

            return None

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации сигнала: {e}")
            return None

    def _create_buy_signal_improved(self, current_price, sr_levels):
        """УЛУЧШЕННОЕ создание BUY сигнала"""
        try:
            # Более агрессивные уровни для увеличения частоты сделок
            sl_distance = abs(current_price - sr_levels['support']) / current_price

            # SL не ближе 0.5% и не дальше 3%
            # 🔥 ИСПРАВЛЕНИЕ: Увеличиваем минимальные расстояния
            sl_distance = max(0.008, min(sl_distance, 0.04))  # Минимум 0.8%, максимум 4%
            sl_price = current_price * (1 - sl_distance)

            # TP на основе risk/reward ratio 1:2
            tp_distance = sl_distance * 2
            tp_price = current_price * (1 + tp_distance)

            return {
                'signal': 'BUY',
                'entry': current_price,
                'sl': sl_price,
                'tp': tp_price,
                'confidence': 0.7,  # Снижена с 0.75
                'sl_distance_pct': sl_distance * 100,
                'tp_distance_pct': tp_distance * 100
            }
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания BUY сигнала: {e}")
            return None

    def _create_sell_signal_improved(self, current_price, sr_levels):
        """УЛУЧШЕННОЕ создание SELL сигнала"""
        try:
            # Более агрессивные уровни для увеличения частоты сделок
            sl_distance = abs(sr_levels['resistance'] - current_price) / current_price

            # SL не ближе 0.5% и не дальше 3%
            # 🔥 ИСПРАВЛЕНИЕ: Увеличиваем минимальные расстояния
            sl_distance = max(0.008, min(sl_distance, 0.04))  # Минимум 0.8%, максимум 4%
            sl_price = current_price * (1 + sl_distance)

            # TP на основе risk/reward ratio 1:2
            tp_distance = sl_distance * 2
            tp_price = current_price * (1 - tp_distance)

            return {
                'signal': 'SELL',
                'entry': current_price,
                'sl': sl_price,
                'tp': tp_price,
                'confidence': 0.7,  # Снижена с 0.75
                'sl_distance_pct': sl_distance * 100,
                'tp_distance_pct': tp_distance * 100
            }
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания SELL сигнала: {e}")
            return None

    def get_signal_statistics(self, data, lookback_periods=100):
        """Дополнительный метод для анализа частоты сигналов"""
        signals_count = 0
        buy_signals = 0
        sell_signals = 0

        start_idx = max(50, len(data) - lookback_periods)

        for i in range(start_idx, len(data)):
            test_data = data.iloc[:i + 1]
            signal = self.generate_signal(test_data)

            if signal:
                signals_count += 1
                if signal['signal'] == 'BUY':
                    buy_signals += 1
                else:
                    sell_signals += 1

        periods_tested = len(data) - start_idx
        signal_frequency = signals_count / periods_tested if periods_tested > 0 else 0

        return {
            'total_signals': signals_count,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'periods_tested': periods_tested,
            'signal_frequency': signal_frequency,
            'signals_per_day': signal_frequency * (1440 / 5) if signal_frequency > 0 else 0  # Assuming 5-min timeframe
        }
