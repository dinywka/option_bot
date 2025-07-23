#config/paths.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = BASE_DIR / "logs"
BACKTEST_DIR = BASE_DIR / "backtests"
MODELS_DIR = BASE_DIR / "models"