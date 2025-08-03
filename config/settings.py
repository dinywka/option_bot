# #config/paths.py
# from pathlib import Path
# from dotenv import load_dotenv
# import os
#
# # Загрузка переменных окружения
# load_dotenv()
#
# # Параметры торговли
# SYMBOLS = os.getenv("SYMBOLS", "BNBUSDT,XRPUSDT,BTCUSDT").split(",")
# TIMEFRAME = os.getenv("TIMEFRAME", "5m")
# RISK_PERCENT = float(os.getenv("RISK_PERCENT", 1.5))
# LEVERAGE = int(os.getenv("LEVERAGE", 10))
#
# # Фильтры
# MIN_VOLUME = float(os.getenv("MIN_VOLUME", 1500000))  # Минимальный объем в USDT
# BLACKLIST_HOURS = list(map(int, os.getenv("BLACKLIST_HOURS", "0,1,2,3").split(",")))  # Часы без торговли (UTC)
#
# # Пути
# BASE_DIR = Path(__file__).resolve().parent.parent
# LOG_DIR = BASE_DIR / "logs"
# DATA_DIR = BASE_DIR / "data"
# MODEL_DIR = BASE_DIR / "models"
#
# # Параметры AI (если используется)
# USE_AI = os.getenv("USE_AI", "false").lower() == "true"
# AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "lstm_volatility.h5")
#
# MIN_QTY = {
#     "BTCUSDT": 0.001,
#     "ETHUSDT": 0.01,
#     "XRPUSDT": 5,
#     "BNBUSDT": 0.1,
#     "SOLUSDT": 0.1
# }

#config/settings.py
from pathlib import Path
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Параметры торговли
SYMBOLS = os.getenv("SYMBOLS", "BNBUSDT,XRPUSDT,BTCUSDT").split(",")
TIMEFRAME = os.getenv("TIMEFRAME", "5")
RISK_PERCENT = float(os.getenv("RISK_PERCENT", 1.5))
LEVERAGE = int(os.getenv("LEVERAGE", 10))

# Фильтры
MIN_VOLUME = float(os.getenv("MIN_VOLUME", 1500000))  # Минимальный объем в USDT
BLACKLIST_HOURS = list(map(int, os.getenv("BLACKLIST_HOURS", "0,1,2,3").split(",")))  # Часы без торговли (UTC)

# Пути
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

# Параметры AI (если используется)
USE_AI = os.getenv("USE_AI", "false").lower() == "true"
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "lstm_volatility.h5")

# Минимальные количества для каждого символа
MIN_QTY = {
    "BTCUSDT": 0.001,
    "ETHUSDT": 0.01,
    "XRPUSDT": 1.0,
    "BNBUSDT": 0.001,    # ← ИСПРАВЛЕНО
    "SOLUSDT": 0.001     # ← РЕКОМЕНДУЕТСЯ
}

QTY_PRECISION = {
    "BTCUSDT": 3,    # 0.001
    "ETHUSDT": 2,    # 0.01
    "XRPUSDT": 0,    # 1 (целое число)
    "BNBUSDT": 3,    # 0.001 - ВАЖНО для исправления ошибки!
    "SOLUSDT": 3     # 0.001
}

# Создаём директории если их нет
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)