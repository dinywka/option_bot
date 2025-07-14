import joblib
import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import telegram
from telegram.ext import Updater, CommandHandler
import numpy as np
import time

# Конфигурация
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
RISK_REWARD_RATIO = 1.5
ATR_MULTIPLIER = 3.0

# Инициализация бота
bot = telegram.Bot(token=TOKEN)
model = joblib.load("forex_model.pkl")


def get_current_data(pair):
    df = yf.download(pair, period="1d", interval="1h")
    if df.empty:
        return None

    df = df[["Open", "High", "Low", "Close", "Volume"]].rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume"
    })

    # Добавляем индикаторы
    df["ema_10"] = EMAIndicator(df["close"], window=10).ema_indicator()
    df["ema_20"] = EMAIndicator(df["close"], window=20).ema_indicator()
    df["macd"] = MACD(df["close"]).macd_diff()
    df["adx"] = ADXIndicator(df["high"], df["low"], df["close"], window=14).adx()
    df["bb_width"] = BollingerBands(df["close"]).bollinger_hband() - BollingerBands(df["close"]).bollinger_lband()
    df["atr"] = AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    df["stoch_rsi"] = (df["rsi"] - df["rsi"].rolling(14).min()) / \
                      (df["rsi"].rolling(14).max() - df["rsi"].rolling(14).min())

    return df.dropna().iloc[-1]


def generate_signal(row, pair):
    features = pd.DataFrame([[
        row["rsi"], row["macd"], row["ema_10"], row["ema_20"],
        row["adx"], row["bb_width"] / row["close"], row["atr"], row["stoch_rsi"]
    ]])

    try:
        pred = model.predict(features)[0]
        if pred == 0:
            return None

        current_price = row["close"]
        atr = row["atr"]

        if pred == 1:  # BUY
            sl = current_price - atr * ATR_MULTIPLIER
            tp = current_price + atr * ATR_MULTIPLIER * RISK_REWARD_RATIO
        else:  # SELL
            sl = current_price + atr * ATR_MULTIPLIER
            tp = current_price - atr * ATR_MULTIPLIER * RISK_REWARD_RATIO

        return {
            "pair": pair.replace("=X", ""),
            "direction": "BUY" if pred == 1 else "SELL",
            "entry": round(current_price, 5),
            "stop_loss": round(sl, 5),
            "take_profit": round(tp, 5),
            "time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        }
    except Exception as e:
        print(f"Ошибка генерации сигнала: {e}")
        return None


def send_signal(signal):
    if not signal:
        return

    message = (
        f"🚀 *Торговый сигнал* 🚀\n\n"
        f"*Пара*: {signal['pair']}\n"
        f"*Направление*: {signal['direction']}\n"
        f"*Цена входа*: {signal['entry']}\n"
        f"*Стоп-лосс*: {signal['stop_loss']}\n"
        f"*Тейк-профит*: {signal['take_profit']}\n\n"
        f"*Время*: {signal['time']}\n"
        f"#Forex #Trading #Signals"
    )

    try:
        bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode=telegram.ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")


def check_signals(context):
    print(f"Проверка сигналов в {pd.Timestamp.now()}")
    for pair in PAIRS:
        try:
            data = get_current_data(pair)
            if data is not None:
                signal = generate_signal(data, pair)
                send_signal(signal)
                time.sleep(2)  # Задержка между запросами
        except Exception as e:
            print(f"Ошибка для пары {pair}: {e}")


def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Бот мониторинга торговых сигналов запущен!"
    )


def main():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))

    # Проверка сигналов каждые 4 часа
    job_queue = updater.job_queue
    job_queue.run_repeating(check_signals, interval=3600 * 4, first=0)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()