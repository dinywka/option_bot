#strategies/ai_enhanced.py
import numpy as np
import pandas as pd
import pandas_ta as ta
from tensorflow.keras.models import load_model
from config.settings import MODEL_DIR, USE_AI, AI_MODEL_NAME
from strategies.base_strategy import BaseStrategy
from typing import Optional


class AIEnhancedStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.model = self._load_model() if USE_AI else None
        self.required_bars = 60  # Количество свечей для анализа моделью

    def _load_model(self):
        """Загрузка предобученной модели"""
        try:
            model_path = MODEL_DIR / AI_MODEL_NAME
            if model_path.exists():
                return load_model(model_path)
            self.logger.warning(f"AI model not found at {model_path}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load AI model: {str(e)}")
            return None

    def analyze(self, data: pd.DataFrame) -> Optional[str]:
        """
        Генерация сигнала с AI-фильтрацией
        Возвращает 'BUY', 'SELL' или None
        """
        try:
            df = self.preprocess_data(data)

            # Проверка на достаточное количество данных
            if len(df) < self.required_bars:
                self.logger.warning(f"Not enough data: {len(df)} < {self.required_bars}")
                return None

            # Базовый сигнал
            base_signal = self._base_signal(df)
            if not base_signal:
                return None

            # Если модель не загружена, возвращаем базовый сигнал
            if not self.model:
                return base_signal

            # AI-коррекция
            ai_score = self._predict_ai(df)
            if ai_score < 0.6:  # Порог уверенности модели
                self.logger.info(f"AI rejected signal (score: {ai_score:.2f})")
                return None

            self.logger.info(f"AI confirmed signal (score: {ai_score:.2f})")
            return base_signal

        except Exception as e:
            self.logger.error(f"Analysis error: {str(e)}")
            return None

    def _base_signal(self, df: pd.DataFrame) -> Optional[str]:
        """Базовая стратегия (SMA+RSI) через pandas-ta"""
        try:
            # Расчет индикаторов
            sma20 = ta.sma(df['close'], length=20)
            rsi = ta.rsi(df['close'], length=14)

            last_close = df['close'].iloc[-1]
            last_sma = sma20.iloc[-1]
            last_rsi = rsi.iloc[-1]

            if last_close > last_sma and last_rsi < 30:
                return "BUY"
            elif last_close < last_sma and last_rsi > 70:
                return "SELL"

            return None
        except Exception as e:
            self.logger.error(f"Signal generation error: {str(e)}")
            return None

    def _predict_ai(self, df: pd.DataFrame) -> float:
        """Предсказание AI-модели"""
        try:
            X = self._prepare_features(df)
            prediction = self.model.predict(X, verbose=0)
            return float(prediction[0][0])
        except Exception as e:
            self.logger.error(f"AI prediction failed: {str(e)}")
            return 0.0

    def _prepare_features(self, df: pd.DataFrame) -> np.array:
        """Подготовка данных для модели"""
        closes = df['close'].values[-self.required_bars:]
        # Нормализация цен
        normalized = (closes - closes.min()) / (closes.max() - closes.min() + 1e-10)
        return np.array([normalized]).reshape(1, self.required_bars, 1)

    def preprocess_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """Расширенная предобработка данных"""
        df = super().preprocess_data(raw_data)

        # Дополнительные фичи
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()

        # Удаление NaN значений
        df = df.dropna()

        return df