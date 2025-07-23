import os
import pandas as pd
from strategies.enhanced_sr import EnhancedSRStrategy

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/bybit_data"))
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
RESULTS = []
LOG_FILE = "trade_log.txt"

with open(LOG_FILE, "w") as f:
    f.write("PAIR,TIME,DIRECTION,ENTRY,SL,TP,EXIT,PNL%,RESULT\n")

def simulate_trade(df, i, strategy, pair):
    data_slice = df.iloc[:i].copy()
    signal = strategy.generate_signal(data_slice)
    if signal is None:
        return None

    direction = signal.lower()
    entry_price = data_slice['close'].iloc[-1]

    # Определение SL/TP
    position_type = "long" if direction == "buy" else "short"
    sl, tp = strategy.calculate_stop_loss_take_profit(data_slice, position_type, entry_price)

    # Симуляция выхода по SL или TP
    exit_price = None
    result = None
    pnl_pct = 0

    for j in range(i + 1, len(df)):
        high = df['high'].iloc[j]
        low = df['low'].iloc[j]
        close = df['close'].iloc[j]
        ts = df['timestamp'].iloc[j]

        if direction == "buy":
            if low <= sl:
                exit_price = sl
                result = "loss"
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                break
            elif high >= tp:
                exit_price = tp
                result = "win"
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                break
        elif direction == "sell":
            if high >= sl:
                exit_price = sl
                result = "loss"
                pnl_pct = (entry_price - exit_price) / entry_price * 100
                break
            elif low <= tp:
                exit_price = tp
                result = "win"
                pnl_pct = (entry_price - exit_price) / entry_price * 100
                break

    if exit_price is not None:
        RESULTS.append({
            "pair": pair,
            "time": str(df['timestamp'].iloc[i]),
            "direction": direction,
            "entry": entry_price,
            "sl": sl,
            "tp": tp,
            "exit": exit_price,
            "pnl_pct": round(pnl_pct, 2),
            "result": result,
        })

        with open(LOG_FILE, "a") as f:
            f.write(f"{pair},{df['timestamp'].iloc[i]},{direction},{entry_price:.2f},{sl:.2f},{tp:.2f},{exit_price:.2f},{pnl_pct:.2f},{result}\n")

        return True
    return None


for symbol in SYMBOLS:
    filename = f"{symbol}_5min.csv"
    filepath = os.path.join(DATA_PATH, filename)

    if not os.path.exists(filepath):
        print(f"❌ Нет данных для {symbol}")
        continue

    df = pd.read_csv(filepath, parse_dates=['timestamp'])
    print(f"\n🔁 Бэктест пары: {symbol}")
    trades = 0
    wins = 0
    total_pnl = 0

    for i in range(50, len(df) - 1):
        strategy = EnhancedSRStrategy(df.iloc[:i].copy())
        if simulate_trade(df, i, strategy, symbol):
            trades += 1
            if RESULTS[-1]['result'] == "win":
                wins += 1
            total_pnl += RESULTS[-1]['pnl_pct']

    if trades > 0:
        avg_pnl = total_pnl / trades
        winrate = wins / trades * 100
        print(f"✅ Сделок: {trades}, WinRate: {winrate:.2f}%, Средний PnL: {avg_pnl:.2f}%")
    else:
        print(f"⚠️ Нет сделок для {symbol}")

# Финальная сводка
print("\n📊 Общая статистика:")
total_trades = len(RESULTS)
if total_trades > 0:
    win_count = sum(1 for r in RESULTS if r['result'] == 'win')
    avg_pnl = sum(r['pnl_pct'] for r in RESULTS) / total_trades
    total_pnl = sum(r['pnl_pct'] for r in RESULTS)
    winrate = win_count / total_trades * 100

    print(f"— Сделок: {total_trades}")
    print(f"— WinRate: {winrate:.2f}%")
    print(f"— Средний PnL: {avg_pnl:.2f}%")
    print(f"— Общий PnL: {total_pnl:.2f}%")
else:
    print("Нет сделок.")

print(f"\n📁 Лог записан в: {LOG_FILE}")


