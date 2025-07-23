# strategies/base_strategy.py

from abc import ABC, abstractmethod
import pandas as pd
import logging
from config.settings import LOG_DIR


class BaseStrategy(ABC):
    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logging.basicConfig(
            filename=LOG_DIR / 'strategy.log',
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(self.__class__.__name__)

    def preprocess_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        df = raw_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        return df

    @abstractmethod
    def generate_signal(self) -> str:
        """Возвращает торговый сигнал: 'BUY', 'SELL' или None"""
        pass

    @abstractmethod
    def analyze(self) -> str:
        """Основная логика анализа"""
        pass

    @abstractmethod
    def calculate_risk(self) -> dict:
        """Возвращает параметры позиции: SL, TP, объем"""
        pass
