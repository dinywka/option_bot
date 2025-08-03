# #config/paths.py
# from pathlib import Path
#
# BASE_DIR = Path(__file__).resolve().parent.parent
#
# LOG_DIR = BASE_DIR / "logs"
# BACKTEST_DIR = BASE_DIR / "backtests"
# MODELS_DIR = BASE_DIR / "models"


# #config/paths.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = BASE_DIR / "logs"
BACKTEST_DIR = BASE_DIR / "backtests"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"

# Создаём директории если их нет
LOG_DIR.mkdir(exist_ok=True)
BACKTEST_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)