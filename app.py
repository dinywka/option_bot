#app.py
import asyncio
import logging
import os
from datetime import datetime
from decimal import Decimal
from telegram import Bot
from connectors.bybit_connector import BybitConnector
from strategies.enhanced_sr import EnhancedSRStrategy
from config.settings import SYMBOLS, RISK_PERCENT, LEVERAGE
from config.paths import LOG_DIR
from config.settings import MIN_QTY
from datetime import datetime



class TradingBot:
    def __init__(self):
        self.logger = logging.getLogger('TradingBot')
        self.connector = BybitConnector()
        self.tg_bot = Bot(token=os.getenv("BOT_TOKEN"))
        self.chat_id = os.getenv("CHAT_ID")
        self.symbols = SYMBOLS
        self.positions = {}
        self.start_balance = None
        self.setup_logging()

    def setup_logging(self):
        level = os.getenv("LOG_LEVEL", "INFO")
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_DIR / 'trading_bot.log'),
                logging.StreamHandler()
            ]
        )

    async def send_telegram(self, message: str):
        try:
            await self.tg_bot.send_message(
                chat_id=self.chat_id,
                text=f"<b>{datetime.utcnow().strftime('%H:%M:%S')}</b>\n{message}",
                parse_mode='HTML'
            )
        except Exception as e:
            self.logger.error(f"Telegram error: {str(e)}")

    async def send_message(self, text: str):
        await self.send_telegram(text)

    async def get_account_balance(self):
        balance = await self.connector.get_wallet_balance()
        self.logger.info(f"Current balance: {balance}")

        if not balance or balance <= 0:
            await self.send_telegram("⚠️ Внимание: нулевой баланс на счете!")

        return balance

    def calculate_position_size(self, price: float) -> float:
        if not self.start_balance:
            self.logger.warning("Start balance is None!")
            return 0.0
        risk_amount = self.start_balance * (RISK_PERCENT / 100)
        return risk_amount / price

    async def trading_cycle(self):
        for symbol in self.symbols:
            data = await self.connector.get_klines(symbol)
            if data is None:
                continue

            strategy = EnhancedSRStrategy(data)
            trade = strategy.generate_signal(data)

            if trade:
                await self.place_order(symbol, trade)


    async def place_order(self, symbol: str, trade: dict):
        try:
            direction = trade["signal"]
            sl = trade["sl"]
            tp = trade["tp"]
            entry_price = trade["entry"]

            qty = max(self.calculate_position_size(entry_price), MIN_QTY.get(symbol, 0.001))
            self.logger.info(f"💰 Расчёт позиции: qty={qty}, entry={entry_price}, balance={self.start_balance}")

            if qty <= 0:
                self.logger.warning(f"Zero quantity for {symbol}")
                return

            order_params = {
                'category': 'linear',
                'symbol': symbol,
                'side': 'Buy' if direction == 'BUY' else 'Sell',
                'orderType': 'Market',
                'qty': round(qty, 3),
                'leverage': LEVERAGE
            }

            self.logger.info(f"📤 Отправка ордера: {order_params}")
            order = await self.connector.place_order(order_params)


            if order is None or order.get("retCode") != 0:
                err_msg = order.get('retMsg') if order else "None response"
                self.logger.error(f"❌ Ошибка размещения ордера: {err_msg}")
                await self.send_telegram(f"❌ Ордер не размещён: {err_msg}")
                return

            order_id = order.get("result", {}).get("orderId")
            time_now = datetime.utcnow().strftime("%H:%M:%S")

            if order_id:
                await asyncio.sleep(1.5)
                status = self.connector.get_order_status(symbol, order_id)

                if status != "Filled":
                    self.logger.warning(f"⚠️ Ордер {order_id} не исполнен! Статус: {status}")
                    await self.send_message(f"{time_now}\n⚠️ Ордер не исполнен: статус {status}")
                else:
                    self.logger.info(f"✅ Ордер исполнен: {order_id}")
                    await self.send_message(f"{time_now}\n✅ Ордер исполнен: {order_id}")
            else:
                self.logger.error("❌ Не удалось получить order_id от Bybit!")
                await self.send_message(f"{time_now}\n❌ Ошибка при размещении ордера")

            await self.send_telegram(
                f"📥 <b>{symbol} {direction}</b>\n"
                f"Entry: {entry_price:.2f}\n"
                f"SL: {sl:.2f}\n"
                f"TP: {tp:.2f}"
            )

            self.positions[symbol] = {
                "entry_price": entry_price,
                "sl": sl,
                "tp": tp,
                "side": direction
            }

        except Exception as e:
            self.logger.error(f"❌ Order failed: {str(e)}")
            await self.send_telegram(f"❌ Order error: {str(e)}")

    async def check_positions(self):
        for symbol, pos in list(self.positions.items()):
            try:
                price_data = await self.connector.get_last_price(symbol)
                current_price = float(price_data['last_price'])
                direction = pos["side"]

                # Проверка на достижение SL / TP
                sl_hit = direction == "BUY" and current_price <= pos["sl"] \
                    or direction == "SELL" and current_price >= pos["sl"]

                tp_hit = direction == "BUY" and current_price >= pos["tp"] \
                    or direction == "SELL" and current_price <= pos["tp"]

                if sl_hit:
                    await self.send_telegram(
                        f"❌ <b>{symbol}</b> SL hit at {current_price:.2f}"
                    )
                    del self.positions[symbol]
                    continue

                if tp_hit:
                    await self.send_telegram(
                        f"✅ <b>{symbol}</b> TP hit at {current_price:.2f}"
                    )
                    del self.positions[symbol]
                    continue

                # Отображение PnL
                entry = pos['entry_price']
                pnl = (current_price - entry) / entry * 100
                if direction == 'SELL':
                    pnl *= -1

                balance = await self.connector.get_wallet_balance()

                await self.send_telegram(
                    f"📊 {symbol} PnL: {pnl:.2f}%\n"
                    f"Entry: {entry:.2f}\n"
                    f"Price: {current_price:.2f}"
                    f"💰 Balance: {balance:.2f} USDT"
                )

            except Exception as e:
                self.logger.error(f"Position check error: {str(e)}")

    async def run(self):
        await self.send_telegram("🤖 Бот запущен")
        self.start_balance = await self.get_account_balance()

        while True:
            try:
                await self.trading_cycle()
                await self.check_positions()
                await asyncio.sleep(60)  # каждый цикл 1 минута
            except Exception as e:
                self.logger.error(f"Main loop error: {str(e)}")
                await asyncio.sleep(30)


if __name__ == "__main__":
    bot = TradingBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        bot.logger.info("Bot stopped by user")
    except Exception as e:
        bot.logger.critical(f"Fatal error: {str(e)}")
