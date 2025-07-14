import pandas as pd
import numpy as np
import joblib
import yfinance as yf
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GridSearchCV
from ta import add_all_ta_features
from ta.utils import dropna
import warnings

warnings.filterwarnings('ignore')

# Настройки
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
LOOKAHEAD = 4  # часов для прогноза
RISK_REWARD_RATIO = 1.5
MAX_HISTORY_DAYS = 730  # Максимальный период для часовых данных
END_DATE = datetime.today()
START_DATE = END_DATE - timedelta(days=MAX_HISTORY_DAYS)


def download_data(symbol):
    """Загрузка данных с Yahoo Finance с обработкой ошибок"""
    try:
        df = yf.download(
            symbol,
            start=START_DATE,
            end=END_DATE,
            interval="1h",
            auto_adjust=True,
            progress=False,
            threads=True
        )
        if df.empty:
            print(f"Нет данных для {symbol}")
            return None

        # Приводим к нужному формату
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        df.columns = ["open", "high", "low", "close", "volume"]
        df = df.reset_index().rename(columns={"Datetime": "timestamp"})

        print(f"Загружено {len(df)} строк для {symbol}")
        return df
    except Exception as e:
        print(f"Ошибка загрузки данных для {symbol}: {str(e)}")
        return None


def calculate_indicators(df):
    """Расчет всех индикаторов с использованием библиотеки ta"""
    try:
        if df is None or len(df) < 100:
            return None

        # Создаем копию для расчетов
        df_ta = df.copy().set_index('timestamp')

        # Добавляем все стандартные индикаторы из библиотеки ta
        df_ta = add_all_ta_features(
            df_ta,
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            fillna=True
        )

        # Выбираем только нужные индикаторы
        selected_features = [
            'trend_macd_diff',  # Линия MACD
            'trend_ema_fast',  # EMA 10
            'trend_ema_slow',  # EMA 20
            'trend_adx',  # ADX
            'volatility_bbw',  # Ширина Bollinger Bands
            'volatility_atr',  # ATR
            'momentum_rsi',  # RSI
            'momentum_stoch_rsi'  # Stochastic RSI
        ]

        # Возвращаем к исходному формату
        df_ta = df_ta[selected_features].reset_index()
        df = pd.merge(df, df_ta, on='timestamp', how='left')

        return df.dropna()
    except Exception as e:
        print(f"Ошибка расчета индикаторов: {str(e)}")
        return None


def generate_labels(df):
    """Генерация меток для обучения"""
    try:
        # Цена через LOOKAHEAD часов
        df['future_price'] = df['close'].shift(-LOOKAHEAD)

        # Определяем динамический SL/TP на основе ATR
        df['atr_multiplier'] = np.where(df['close'] > df['trend_ema_slow'], 2.5, 3.5)
        df['tp'] = df['close'] + df['volatility_atr'] * df['atr_multiplier'] * RISK_REWARD_RATIO
        df['sl'] = df['close'] - df['volatility_atr'] * df['atr_multiplier']

        # Генерируем метки
        df['label'] = np.where(
            df['future_price'] >= df['tp'], 1,  # BUY
            np.where(
                df['future_price'] <= df['sl'], -1,  # SELL
                0  # HOLD
            )
        )

        return df.dropna()
    except Exception as e:
        print(f"Ошибка генерации меток: {str(e)}")
        return None


def train_model(X, y):
    """Обучение модели с подбором параметров"""
    param_grid = {
        'n_estimators': [100, 150],
        'learning_rate': [0.05, 0.1],
        'max_depth': [3, 4],
        'min_samples_split': [2, 5]
    }

    model = GridSearchCV(
        GradientBoostingClassifier(random_state=42),
        param_grid,
        cv=3,
        scoring='accuracy',
        n_jobs=-1,
        verbose=1
    )

    model.fit(X, y)
    print(f"\nЛучшие параметры: {model.best_params_}")
    print(f"Лучшая точность: {model.best_score_:.2f}")
    return model.best_estimator_


if __name__ == "__main__":
    all_data = []
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

    for pair in PAIRS:
        print(f"\nОбработка пары {pair}...")

        # Загрузка данных
        df = download_data(pair)
        if df is None:
            continue

        # Расчет индикаторов
        df = calculate_indicators(df)
        if df is None:
            continue

        # Генерация меток
        df = generate_labels(df)
        if df is None:
            continue

        df['pair'] = pair
        all_data.append(df)
        print(f"Добавлено {len(df)} обучающих примеров")

    if not all_data:
        print("\nНе удалось подготовить данные для обучения!")
        exit()

    # Объединение всех данных
    full_df = pd.concat(all_data)
    print(f"\nВсего данных для обучения: {len(full_df)} строк")

    # Обучение модели
    print("\nНачало обучения модели...")
    model = train_model(full_df[features], full_df['label'])

    # Сохранение модели
    joblib.dump(model, "forex_model.pkl")
    print("\nМодель успешно обучена и сохранена в forex_model.pkl")

    # Сохранение данных для анализа
    full_df.to_csv("training_data.csv", index=False)
    print("Данные для обучения сохранены в training_data.csv")