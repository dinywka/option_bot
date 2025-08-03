#utils.py
import pandas as pd
import numpy as np
import logging


class DataFrameValidator:
    """Утилиты для валидации DataFrame и предотвращения ошибки 'ambiguous truth value'"""

    def __init__(self):
        self.logger = logging.getLogger('DataFrameValidator')

    @staticmethod
    def is_valid_dataframe(df, min_rows=1, required_columns=None):
        """
        Безопасная проверка DataFrame
        Возвращает: (is_valid: bool, error_message: str)
        """
        try:
            # Проверка на None
            if df is None:
                return False, "DataFrame is None"

            # Проверка на тип
            if not isinstance(df, pd.DataFrame):
                return False, f"Expected DataFrame, got {type(df)}"

            # Проверка на пустоту (ПРАВИЛЬНЫЙ способ)
            if df.empty:
                return False, "DataFrame is empty"

            # Проверка минимального количества строк
            if len(df) < min_rows:
                return False, f"Not enough rows: {len(df)} < {min_rows}"

            # Проверка обязательных колонок
            if required_columns:
                missing_cols = [col for col in required_columns if col not in df.columns]
                if missing_cols:
                    return False, f"Missing columns: {missing_cols}"

            # Проверка на NaN в критических колонках
            if required_columns:
                for col in required_columns:
                    if df[col].isnull().all():
                        return False, f"Column '{col}' contains only NaN values"

            return True, "DataFrame is valid"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def safe_dataframe_check(df, condition_func=None):
        """
        Безопасная проверка условий на DataFrame

        Args:
            df: DataFrame для проверки
            condition_func: функция, возвращающая boolean Series или значение

        Returns:
            bool: результат проверки
        """
        try:
            if df is None or df.empty:
                return False

            if condition_func is None:
                return len(df) > 0

            result = condition_func(df)

            # Если результат - Series, используем any() или all()
            if isinstance(result, pd.Series):
                # Для большинства случаев подходит any()
                return result.any()

            # Если результат - скалярное значение
            return bool(result)

        except Exception as e:
            logging.getLogger('DataFrameValidator').error(f"Safe check error: {e}")
            return False

    @staticmethod
    def clean_dataframe(df, required_columns=None):
        """
        Очистка DataFrame от проблемных данных

        Returns:
            pd.DataFrame: очищенный DataFrame или None если данные непригодны
        """
        try:
            if df is None or df.empty:
                return None

            # Создаем копию
            clean_df = df.copy()

            # Удаляем строки с NaN в критических колонках
            if required_columns:
                clean_df = clean_df.dropna(subset=required_columns)

            # Проверяем, что остались данные
            if clean_df.empty:
                return None

            # Заменяем inf на NaN и удаляем
            clean_df = clean_df.replace([np.inf, -np.inf], np.nan)
            clean_df = clean_df.dropna()

            # Финальная проверка
            if clean_df.empty or len(clean_df) < 10:
                return None

            return clean_df

        except Exception as e:
            logging.getLogger('DataFrameValidator').error(f"DataFrame cleaning error: {e}")
            return None

    @staticmethod
    def safe_condition_check(df, *conditions):
        """
        Безопасная проверка множественных условий

        Args:
            df: DataFrame
            *conditions: список функций-условий

        Returns:
            bool: True если все условия выполнены
        """
        try:
            if df is None or df.empty:
                return False

            for condition in conditions:
                try:
                    result = condition(df)
                    # Правильная обработка результата
                    if isinstance(result, pd.Series):
                        if not result.any():  # Используем any() для Series
                            return False
                    elif isinstance(result, pd.DataFrame):
                        if result.empty:  # Для DataFrame используем empty
                            return False
                    else:
                        if not bool(result):  # Для скаляров используем bool()
                            return False
                except Exception as e:
                    logging.getLogger('DataFrameValidator').warning(f"Condition check failed: {e}")
                    return False

            return True

        except Exception as e:
            logging.getLogger('DataFrameValidator').error(f"Safe condition check error: {e}")
            return False


# Примеры использования для исправления проблем в торговом боте
class TradingDataValidator(DataFrameValidator):
    """Специализированные проверки для торговых данных"""

    REQUIRED_OHLCV_COLUMNS = ['open', 'high', 'low', 'close', 'volume']

    @classmethod
    def validate_kline_data(cls, df):
        """Валидация данных свечей"""
        is_valid, message = cls.is_valid_dataframe(
            df,
            min_rows=50,
            required_columns=cls.REQUIRED_OHLCV_COLUMNS
        )

        if not is_valid:
            return False, message

        # Дополнительные проверки для торговых данных
        try:
            # Проверяем, что цены положительные
            price_cols = ['open', 'high', 'low', 'close']
            for col in price_cols:
                if (df[col] <= 0).any():
                    return False, f"Invalid prices in column {col}"

            # Проверяем логику OHLC
            if ((df['high'] < df['low']) |
                (df['high'] < df['open']) |
                (df['high'] < df['close']) |
                (df['low'] > df['open']) |
                (df['low'] > df['close'])).any():
                return False, "Invalid OHLC relationships"

            # Проверяем объемы
            if (df['volume'] < 0).any():
                return False, "Negative volume values"

            return True, "Valid trading data"

        except Exception as e:
            return False, f"Trading data validation error: {str(e)}"

    @classmethod
    def safe_strategy_check(cls, df, strategy_conditions):
        """
        Безопасная проверка условий стратегии

        Args:
            df: DataFrame с торговыми данными
            strategy_conditions: список условий для проверки

        Returns:
            dict: результат с сигналом или None
        """
        try:
            # Сначала валидируем данные
            is_valid, message = cls.validate_kline_data(df)
            if not is_valid:
                logging.getLogger('TradingDataValidator').warning(f"Invalid data: {message}")
                return None

            # Проверяем условия стратегии безопасным способом
            if cls.safe_condition_check(df, *strategy_conditions):
                return {"signal": "VALID", "data_quality": "good"}

            return None

        except Exception as e:
            logging.getLogger('TradingDataValidator').error(f"Strategy check error: {e}")
            return None


# Декоратор для безопасной работы с DataFrame
def safe_dataframe_operation(required_columns=None, min_rows=1):
    """
    Декоратор для безопасного выполнения операций с DataFrame
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Находим DataFrame в аргументах
                df = None
                for arg in args:
                    if isinstance(arg, pd.DataFrame):
                        df = arg
                        break

                if df is None:
                    # Ищем в kwargs
                    for key, value in kwargs.items():
                        if isinstance(value, pd.DataFrame):
                            df = value
                            break

                if df is None:
                    raise ValueError("No DataFrame found in arguments")

                # Валидируем DataFrame
                is_valid, message = DataFrameValidator.is_valid_dataframe(
                    df, min_rows, required_columns
                )

                if not is_valid:
                    logging.getLogger('safe_dataframe_operation').warning(f"DataFrame validation failed: {message}")
                    return None

                # Выполняем функцию
                return func(*args, **kwargs)

            except Exception as e:
                logging.getLogger('safe_dataframe_operation').error(f"Operation failed: {e}")
                return None

        return wrapper

    return decorator


# Пример использования в стратегии
class SafeStrategy:
    """Пример безопасной стратегии с правильной обработкой DataFrame"""

    def __init__(self):
        self.validator = TradingDataValidator()
        self.logger = logging.getLogger('SafeStrategy')

    @safe_dataframe_operation(required_columns=['open', 'high', 'low', 'close'], min_rows=50)
    def generate_signal(self, df):
        """Безопасная генерация сигнала"""
        try:
            # Все проверки DataFrame уже выполнены декоратором
            self.logger.info(f"Processing {len(df)} candles")

            # Рассчитываем индикаторы
            df = self._add_indicators(df)

            # Проверяем условия (безопасно)
            conditions = [
                lambda x: x['close'].iloc[-1] > x['close'].rolling(20).mean().iloc[-1],
                lambda x: x['volume'].iloc[-1] > x['volume'].rolling(10).mean().iloc[-1]
            ]

            if self.validator.safe_condition_check(df, *conditions):
                return {
                    'signal': 'BUY',
                    'entry': df['close'].iloc[-1],
                    'sl': df['close'].iloc[-1] * 0.98,
                    'tp': df['close'].iloc[-1] * 1.02
                }

            return None

        except Exception as e:
            self.logger.error(f"Signal generation error: {e}")
            return None

    def _add_indicators(self, df):
        """Добавление индикаторов с обработкой ошибок"""
        try:
            df = df.copy()
            df['sma_20'] = df['close'].rolling(20).mean()
            df['volume_sma'] = df['volume'].rolling(10).mean()
            return df
        except Exception as e:
            self.logger.error(f"Indicator calculation error: {e}")
            return df