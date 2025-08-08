# #app.py
# import asyncio
# import logging
# import os
# from datetime import datetime
# from decimal import Decimal
# from telegram import Bot
# from connectors.bybit_connector import BybitConnector
# from strategies.enhanced_sr import EnhancedSRStrategy
# from config.settings import SYMBOLS, RISK_PERCENT, LEVERAGE
# from config.paths import LOG_DIR
# from config.settings import MIN_QTY
# from datetime import datetime
#
#
#
# class TradingBot:
#     def __init__(self):
#         self.logger = logging.getLogger('TradingBot')
#         self.connector = BybitConnector()
#         self.tg_bot = Bot(token=os.getenv("BOT_TOKEN"))
#         self.chat_id = os.getenv("CHAT_ID")
#         self.symbols = SYMBOLS
#         self.positions = {}
#         self.start_balance = None
#         self.setup_logging()
#
#     def setup_logging(self):
#         level = os.getenv("LOG_LEVEL", "INFO")
#         logging.basicConfig(
#             level=level,
#             format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#             handlers=[
#                 logging.FileHandler(LOG_DIR / 'trading_bot.log'),
#                 logging.StreamHandler()
#             ]
#         )
#
#     async def send_telegram(self, message: str):
#         try:
#             await self.tg_bot.send_message(
#                 chat_id=self.chat_id,
#                 text=f"<b>{datetime.utcnow().strftime('%H:%M:%S')}</b>\n{message}",
#                 parse_mode='HTML'
#             )
#         except Exception as e:
#             self.logger.error(f"Telegram error: {str(e)}")
#
#     async def send_message(self, text: str):
#         await self.send_telegram(text)
#
#     async def get_account_balance(self):
#         balance = await self.connector.get_wallet_balance()
#         self.logger.info(f"Current balance: {balance}")
#
#         if not balance or balance <= 0:
#             await self.send_telegram("⚠️ Внимание: нулевой баланс на счете!")
#
#         return balance
#
#     def calculate_position_size(self, price: float) -> float:
#         if not self.start_balance:
#             self.logger.warning("Start balance is None!")
#             return 0.0
#         risk_amount = self.start_balance * (RISK_PERCENT / 100)
#         return risk_amount / price
#
#     async def trading_cycle(self):
#         for symbol in self.symbols:
#             data = await self.connector.get_klines(symbol)
#             if data is None:
#                 continue
#
#             strategy = EnhancedSRStrategy(data)
#             trade = strategy.generate_signal(data)
#
#             if trade:
#                 await self.place_order(symbol, trade)
#
#
#     async def place_order(self, symbol: str, trade: dict):
#         try:
#             direction = trade["signal"]
#             sl = trade["sl"]
#             tp = trade["tp"]
#             entry_price = trade["entry"]
#
#             qty = max(self.calculate_position_size(entry_price), MIN_QTY.get(symbol, 0.001))
#             self.logger.info(f"💰 Расчёт позиции: qty={qty}, entry={entry_price}, balance={self.start_balance}")
#
#             if qty <= 0:
#                 self.logger.warning(f"Zero quantity for {symbol}")
#                 return
#
#             order_params = {
#                 'category': 'linear',
#                 'symbol': symbol,
#                 'side': 'Buy' if direction == 'BUY' else 'Sell',
#                 'orderType': 'Market',
#                 'qty': round(qty, 3),
#                 'leverage': LEVERAGE
#             }
#
#             self.logger.info(f"📤 Отправка ордера: {order_params}")
#             order = await self.connector.place_order(order_params)
#
#
#             if order is None or order.get("retCode") != 0:
#                 err_msg = order.get('retMsg') if order else "None response"
#                 self.logger.error(f"❌ Ошибка размещения ордера: {err_msg}")
#                 await self.send_telegram(f"❌ Ордер не размещён: {err_msg}")
#                 return
#
#             order_id = order.get("result", {}).get("orderId")
#             time_now = datetime.utcnow().strftime("%H:%M:%S")
#
#             if order_id:
#                 await asyncio.sleep(1.5)
#                 status = self.connector.get_order_status(symbol, order_id)
#
#                 if status != "Filled":
#                     self.logger.warning(f"⚠️ Ордер {order_id} не исполнен! Статус: {status}")
#                     await self.send_message(f"{time_now}\n⚠️ Ордер не исполнен: статус {status}")
#                 else:
#                     self.logger.info(f"✅ Ордер исполнен: {order_id}")
#                     await self.send_message(f"{time_now}\n✅ Ордер исполнен: {order_id}")
#             else:
#                 self.logger.error("❌ Не удалось получить order_id от Bybit!")
#                 await self.send_message(f"{time_now}\n❌ Ошибка при размещении ордера")
#
#             await self.send_telegram(
#                 f"📥 <b>{symbol} {direction}</b>\n"
#                 f"Entry: {entry_price:.2f}\n"
#                 f"SL: {sl:.2f}\n"
#                 f"TP: {tp:.2f}"
#             )
#
#             self.positions[symbol] = {
#                 "entry_price": entry_price,
#                 "sl": sl,
#                 "tp": tp,
#                 "side": direction
#             }
#
#         except Exception as e:
#             self.logger.error(f"❌ Order failed: {str(e)}")
#             await self.send_telegram(f"❌ Order error: {str(e)}")
#
#     async def check_positions(self):
#         for symbol, pos in list(self.positions.items()):
#             try:
#                 price_data = await self.connector.get_last_price(symbol)
#                 current_price = float(price_data['last_price'])
#                 direction = pos["side"]
#
#                 # Проверка на достижение SL / TP
#                 sl_hit = direction == "BUY" and current_price <= pos["sl"] \
#                     or direction == "SELL" and current_price >= pos["sl"]
#
#                 tp_hit = direction == "BUY" and current_price >= pos["tp"] \
#                     or direction == "SELL" and current_price <= pos["tp"]
#
#                 if sl_hit:
#                     await self.send_telegram(
#                         f"❌ <b>{symbol}</b> SL hit at {current_price:.2f}"
#                     )
#                     del self.positions[symbol]
#                     continue
#
#                 if tp_hit:
#                     await self.send_telegram(
#                         f"✅ <b>{symbol}</b> TP hit at {current_price:.2f}"
#                     )
#                     del self.positions[symbol]
#                     continue
#
#                 # Отображение PnL
#                 entry = pos['entry_price']
#                 pnl = (current_price - entry) / entry * 100
#                 if direction == 'SELL':
#                     pnl *= -1
#
#                 balance = await self.connector.get_wallet_balance()
#
#                 await self.send_telegram(
#                     f"📊 {symbol} PnL: {pnl:.2f}%\n"
#                     f"Entry: {entry:.2f}\n"
#                     f"Price: {current_price:.2f}"
#                     f"💰 Balance: {balance:.2f} USDT"
#                 )
#
#             except Exception as e:
#                 self.logger.error(f"Position check error: {str(e)}")
#
#     async def run(self):
#         await self.send_telegram("🤖 Бот запущен")
#         self.start_balance = await self.get_account_balance()
#
#         while True:
#             try:
#                 await self.trading_cycle()
#                 await self.check_positions()
#                 await asyncio.sleep(60)  # каждый цикл 1 минута
#             except Exception as e:
#                 self.logger.error(f"Main loop error: {str(e)}")
#                 await asyncio.sleep(30)
#
#
# if __name__ == "__main__":
#     bot = TradingBot()
#     try:
#         asyncio.run(bot.run())
#     except KeyboardInterrupt:
#         bot.logger.info("Bot stopped by user")
#     except Exception as e:
#         bot.logger.critical(f"Fatal error: {str(e)}")

# app.py
import asyncio
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from telegram import Bot
import time
from connectors.bybit_connector import BybitConnector
from strategies.enhanced_sr import EnhancedSRStrategy
from config.settings import SYMBOLS, RISK_PERCENT, LEVERAGE, MIN_QTY, LOG_DIR, QTY_PRECISION

import asyncio
import logging
import os
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from telegram import Bot


class TradingBot:
    def __init__(self):
        self.logger = logging.getLogger('TradingBot')
        self.connector = BybitConnector()
        self.tg_bot = Bot(token=os.getenv("BOT_TOKEN"))
        self.chat_id = os.getenv("CHAT_ID")
        self.symbols = SYMBOLS
        self.positions = {}
        self.pending_orders = {}
        self.last_trade_time = {}
        self.failed_trades = {}
        self.api_errors = {}
        self.start_balance = None
        self.symbol_info = {}
        self.emergency_stop = False
        self.max_daily_loss = 0.05
        self.daily_start_balance = None
        self._last_pnl_report = {}
        self.setup_logging()

    def setup_logging(self):
        """Настройка логирования с ротацией файлов"""
        level = os.getenv("LOG_LEVEL", "INFO")

        # Создаем форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Файловый обработчик с ротацией
        file_handler = RotatingFileHandler(
            LOG_DIR / 'trading_bot.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, level))

        # Настройка логгера
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Добавляем обработчик для критических ошибок
        critical_handler = logging.FileHandler('critical_errors.log')
        critical_handler.setLevel(logging.ERROR)
        critical_formatter = logging.Formatter(
            '%(asctime)s - CRITICAL - %(name)s - %(levelname)s - %(message)s'
        )
        critical_handler.setFormatter(critical_formatter)
        self.logger.addHandler(critical_handler)

    async def send_telegram(self, message: str):
        """Отправка сообщения в Telegram с обработкой ошибок"""
        try:
            await self.tg_bot.send_message(
                chat_id=self.chat_id,
                text=f"<b>{datetime.utcnow().strftime('%H:%M:%S')}</b>\n{message}",
                parse_mode='HTML'
            )
        except Exception as e:
            self.logger.error(f"Telegram error: {str(e)}")

    async def get_account_balance(self) -> float:
        """Получение баланса аккаунта"""
        try:
            balance = await self.connector.get_wallet_balance()
            self.logger.info(f"💰 Current balance: {balance}")

            if not balance or balance <= 0:
                await self.send_telegram("⚠️ Внимание: нулевой баланс на счете!")
                return 0.0

            return balance
        except Exception as e:
            self.logger.error(f"❌ Error getting balance: {e}")
            return 0.0

    async def get_symbol_info(self, symbol: str) -> dict:
        """Получение информации о символе с кэшированием"""
        if symbol in self.symbol_info:
            return self.symbol_info[symbol]

        try:
            info = await self.connector.get_instruments_info(symbol)
            if info:
                self.symbol_info[symbol] = info
                self.logger.info(f"📋 Loaded symbol info for {symbol}: {info}")
                return info
        except Exception as e:
            self.logger.error(f"❌ Failed to get symbol info for {symbol}: {e}")

        # Возвращаем дефолтные значения
        default_info = {
            'minOrderQty': MIN_QTY.get(symbol, 0.001),
            'maxOrderQty': 1000.0,
            'qtyStep': 0.001,
            'minOrderAmt': 1.0,
            'tickSize': 0.01
        }
        self.symbol_info[symbol] = default_info
        self.logger.warning(f"⚠️ Using default symbol info for {symbol}")
        return default_info

    async def calculate_position_size(self, entry_price: float, symbol: str) -> tuple[float, bool]:
        """Расчет размера позиции с учетом ограничений"""
        try:
            # Получаем текущий баланс
            balance = await self.get_account_balance()
            if balance < 10:
                self.logger.warning(f"❌ Недостаточный баланс для торговли: {balance}")
                return 0.0, False

            # Рассчитываем сумму риска (1% от баланса)
            risk_amount = balance * 0.01

            # Получаем информацию о символе
            symbol_info = await self.get_symbol_info(symbol)

            # Рассчитываем сырой размер позиции
            raw_qty = risk_amount / entry_price

            # Применяем ограничения символа
            min_qty = symbol_info['minOrderQty']
            max_qty = symbol_info['maxOrderQty']
            qty_step = symbol_info['qtyStep']

            # Округляем до валидного размера
            adjusted_qty = max(min_qty, raw_qty)
            adjusted_qty = round(adjusted_qty / qty_step) * qty_step
            adjusted_qty = min(adjusted_qty, max_qty)

            # Проверяем минимальную стоимость ордера
            order_value = adjusted_qty * entry_price
            min_order_amt = symbol_info.get('minOrderAmt', 1.0)

            if order_value < min_order_amt:
                adjusted_qty = min_order_amt / entry_price
                adjusted_qty = round(adjusted_qty / qty_step) * qty_step

            # Финальная проверка
            final_order_value = adjusted_qty * entry_price
            max_order_value = balance * 0.02  # Не больше 2% баланса

            if final_order_value > max_order_value:
                self.logger.error(f"❌ Ордер слишком большой для {symbol}: {final_order_value} > {max_order_value}")
                return 0.0, False

            if adjusted_qty < min_qty:
                self.logger.error(f"❌ Размер позиции меньше минимального: {adjusted_qty} < {min_qty}")
                return 0.0, False

            self.logger.info(
                f"🔢 Расчет позиции {symbol}: сырой={raw_qty:.6f}, итоговый={adjusted_qty:.6f}, стоимость={final_order_value:.2f}")

            return adjusted_qty, True

        except Exception as e:
            self.logger.error(f"❌ Error calculating position size for {symbol}: {e}")
            return 0.0, False

    async def can_trade(self, symbol: str) -> bool:
        """Проверяет возможность торговли символом"""
        try:
            # Проверяем аварийную остановку
            if self.emergency_stop:
                return False

            # Проверяем открытые позиции
            if symbol in self.positions:
                self.logger.debug(f"❌ {symbol} уже в позициях")
                return False

            # Проверяем ожидающие ордера
            if symbol in self.pending_orders:
                self.logger.debug(f"❌ {symbol} имеет ожидающий ордер")
                return False

            # Проверяем cooldown с учетом неудачных сделок
            last_time = self.last_trade_time.get(symbol)
            if last_time:
                failed_count = self.failed_trades.get(symbol, 0)
                cooldown_minutes = 15 + (failed_count * 10)
                cooldown_minutes = min(cooldown_minutes, 120)  # Максимум 2 часа

                time_since = datetime.utcnow() - last_time
                if time_since < timedelta(minutes=cooldown_minutes):
                    self.logger.debug(f"❌ {symbol} в cooldown еще {cooldown_minutes - time_since.seconds // 60} мин")
                    return False

            # Проверяем частоту ошибок API
            api_error_count = self.api_errors.get(symbol, 0)
            if api_error_count >= 5:
                if last_time and (datetime.utcnow() - last_time) < timedelta(hours=1):
                    self.logger.debug(f"❌ {symbol} заблокирован из-за частых ошибок API")
                    return False

            # Проверяем баланс
            balance = await self.get_account_balance()
            if balance < 10:
                self.logger.debug(f"❌ Недостаточный баланс: {balance}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"❌ Error in can_trade for {symbol}: {e}")
            return False

    async def place_order_with_retry(self, order_params: dict, symbol: str, max_retries: int = 3) -> dict:
        """Размещение ордера с повторными попытками"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"📤 Попытка {attempt + 1}/{max_retries} размещения ордера {symbol}: {order_params}")

                order = await self.connector.place_order(order_params)

                if order is None:
                    self.api_errors[symbol] = self.api_errors.get(symbol, 0) + 1
                    self.logger.error(f"❌ Получен None ответ от Bybit для {symbol}")

                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    return None

                ret_code = order.get("retCode")
                ret_msg = order.get("retMsg", "Unknown error")

                if ret_code == 0:
                    self.logger.info(f"✅ Ордер успешно размещен для {symbol}")
                    return order

                # Обработка специфических ошибок
                if ret_code == 110017:  # "current position is zero"
                    self.logger.warning(f"⚠️ Позиция еще не создана для {symbol}, попытка {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2.0)
                        continue

                elif ret_code == 10001:  # Minimum size error
                    current_qty = float(order_params['qty'])
                    symbol_info = await self.get_symbol_info(symbol)
                    min_qty = symbol_info['minOrderQty']

                    if current_qty < min_qty:
                        new_qty = min_qty * 1.1
                        order_params['qty'] = str(round(new_qty, 6))
                        self.logger.warning(f"⚠️ Adjusting qty from {current_qty} to {new_qty} for {symbol}")

                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue

                elif ret_code in [10002, 10003]:  # Balance errors
                    self.logger.error(f"❌ Недостаточный баланс для {symbol}")
                    await self.send_telegram(f"❌ {symbol} недостаточный баланс")
                    break

                self.logger.error(f"❌ Ошибка размещения ордера {symbol}: код {ret_code}, сообщение: {ret_msg}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                self.logger.error(f"❌ Exception on attempt {attempt + 1} for {symbol}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return None

    async def wait_for_position(self, symbol: str, expected_qty: float, timeout: int = 20) -> tuple[bool, float]:
        """Ожидание создания позиции с контролем размера"""
        self.logger.info(f"⏳ Ожидание создания позиции для {symbol} (ожидаем: {expected_qty})...")

        for attempt in range(timeout):
            try:
                positions = await self.connector.get_positions(symbol)

                if positions and len(positions) > 0:
                    for pos in positions:
                        pos_size = abs(float(pos.get('size', 0)))

                        if pos_size > 0:
                            # Контроль размера: если позиция больше чем в 2 раза - проблема
                            if pos_size > expected_qty * 2:
                                self.logger.error(
                                    f"🚨 КРИТИЧНО! Размер позиции {symbol} превышен: "
                                    f"ожидали {expected_qty}, получили {pos_size}"
                                )
                                await self.emergency_close_excess_position(symbol, expected_qty, pos_size)
                                return True, expected_qty

                            # Если размер в разумных пределах
                            elif pos_size >= expected_qty * 0.8:  # 80% от ожидаемого
                                self.logger.info(f"✅ Позиция создана для {symbol}: размер={pos_size}")
                                return True, pos_size

                            # Частичное исполнение
                            elif pos_size > 0:
                                self.logger.info(f"📊 Частичная позиция {symbol}: {pos_size}")
                                if attempt >= timeout // 2:
                                    return True, pos_size

                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"❌ Ошибка проверки позиции {symbol}: {e}")
                await asyncio.sleep(1)

        self.logger.warning(f"⚠️ Позиция не найдена для {symbol} за {timeout} секунд")
        return False, 0.0

    async def emergency_close_excess_position(self, symbol: str, expected_qty: float, actual_qty: float):
        """Экстренное закрытие излишка позиции"""
        try:
            excess_qty = actual_qty - expected_qty
            self.logger.warning(f"🚨 Экстренное закрытие излишка {symbol}: {excess_qty}")

            positions = await self.connector.get_positions(symbol)
            if not positions:
                return

            position = positions[0]
            pos_side = position.get('side', '')
            close_side = "Sell" if pos_side == "Buy" else "Buy"

            close_params = {
                "category": "linear",
                "symbol": symbol,
                "side": close_side,
                "orderType": "Market",
                "qty": str(round(excess_qty, 6)),
                "reduceOnly": True
            }

            response = await self.connector.place_order(close_params)

            if response and response.get("retCode") == 0:
                self.logger.info(f"✅ Излишек {symbol} закрыт: {excess_qty}")
                await self.send_telegram(f"🚨 Закрыт излишек позиции {symbol}: {excess_qty}")
            else:
                self.logger.error(f"❌ Не удалось закрыть излишек {symbol}: {response}")

        except Exception as e:
            self.logger.error(f"❌ Ошибка экстренного закрытия {symbol}: {e}")

    async def place_protective_orders(self, symbol: str, side: str, entry_price: float,
                                      sl_price: float, tp_price: float, qty: float) -> bool:
        """Установка защитных ордеров SL/TP"""
        self.logger.info(f"🛡 Установка защитных ордеров для {symbol}: SL={sl_price}, TP={tp_price}")

        try:
            # Метод 1: Пытаемся использовать set_trading_stop
            success = await self.set_trading_stop(symbol, sl_price, tp_price)
            if success:
                self.logger.info(f"✅ set_trading_stop успешно для {symbol}")
                return True

            # Метод 2: Fallback - используем reduce-only ордера
            self.logger.info(f"🔄 Fallback: размещение reduce-only ордеров для {symbol}")
            success = await self.place_reduce_only_orders(symbol, side, sl_price, tp_price, qty)

            return success

        except Exception as e:
            self.logger.error(f"❌ Ошибка установки защитных ордеров {symbol}: {e}")
            return False

    async def set_trading_stop(self, symbol: str, sl_price: float, tp_price: float, max_attempts: int = 3) -> bool:
        """Установка SL/TP через set_trading_stop"""
        for attempt in range(1, max_attempts + 1):
            try:
                if attempt > 1:
                    await asyncio.sleep(2)

                result = await self.connector.set_trading_stop(
                    symbol=symbol,
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    category="linear"
                )

                self.logger.info(f"🔁 Попытка {attempt}: set_trading_stop результат: {result}")

                if result and result.get("retCode") == 0:
                    self.logger.info(f"✅ set_trading_stop успешно для {symbol}")
                    return True
                elif result and "not modified" in str(result.get("retMsg", "")).lower():
                    self.logger.info(f"ℹ️ SL/TP уже установлены для {symbol}")
                    return True
                else:
                    error_msg = result.get("retMsg", "Unknown error") if result else "No response"
                    self.logger.warning(f"⚠️ set_trading_stop попытка {attempt} неудачна: {error_msg}")

            except Exception as e:
                self.logger.error(f"❌ Исключение в set_trading_stop попытка {attempt}: {e}")

        return False

    async def place_reduce_only_orders(self, symbol: str, side: str, sl_price: float, tp_price: float,
                                       qty: float) -> bool:
        """Установка SL/TP через reduce-only ордера"""
        try:
            close_side = "Sell" if side == "Buy" else "Buy"
            sl_success = False
            tp_success = False

            # Stop Loss ордер (StopMarket)
            try:
                sl_params = {
                    "category": "linear",
                    "symbol": symbol,
                    "side": close_side,
                    "orderType": "StopMarket",
                    "qty": str(qty),
                    "stopPrice": str(sl_price),
                    "reduceOnly": True,
                    "timeInForce": "GTC"
                }

                sl_response = await self.connector.place_order(sl_params)
                if sl_response and sl_response.get("retCode") == 0:
                    sl_success = True
                    self.logger.info(f"✅ SL ордер установлен для {symbol}")
                else:
                    self.logger.error(f"❌ Ошибка SL ордера: {sl_response}")

            except Exception as e:
                self.logger.error(f"❌ Исключение при размещении SL ордера: {e}")

            # Take Profit ордер (Limit)
            try:
                tp_params = {
                    "category": "linear",
                    "symbol": symbol,
                    "side": close_side,
                    "orderType": "Limit",
                    "qty": str(qty),
                    "price": str(tp_price),
                    "reduceOnly": True,
                    "timeInForce": "GTC"
                }

                tp_response = await self.connector.place_order(tp_params)
                if tp_response and tp_response.get("retCode") == 0:
                    tp_success = True
                    self.logger.info(f"✅ TP ордер установлен для {symbol}")
                else:
                    self.logger.error(f"❌ Ошибка TP ордера: {tp_response}")

            except Exception as e:
                self.logger.error(f"❌ Исключение при размещении TP ордера: {e}")

            success = sl_success or tp_success
            if success:
                self.logger.info(f"✅ Reduce-only ордера размещены для {symbol} (SL={sl_success}, TP={tp_success})")
            else:
                self.logger.error(f"❌ Не удалось разместить ни одного reduce-only ордера для {symbol}")

            return success

        except Exception as e:
            self.logger.error(f"❌ Ошибка в place_reduce_only_orders: {e}")
            return False

    async def place_order(self, symbol: str, trade: dict):
        """Основная функция размещения ордера"""
        try:
            direction = trade["signal"]
            sl = trade["sl"]
            tp = trade["tp"]
            entry_price = trade["entry"]

            self.logger.info(f"🎯 Начинаем размещение ордера {symbol}: {direction} @ {entry_price}")

            # 1. Проверяем баланс
            current_balance = await self.get_account_balance()
            if current_balance < 50:
                self.logger.warning(f"❌ Недостаточный баланс для торговли: {current_balance}")
                return

            # 2. Рассчитываем размер позиции
            qty, is_valid = await self.calculate_position_size(entry_price, symbol)
            if not is_valid or qty <= 0:
                self.logger.warning(f"❌ Неверное количество для {symbol}: {qty}")
                return

            # 3. Формируем параметры ордера
            order_params = {
                'category': 'linear',
                'symbol': symbol,
                'side': 'Buy' if direction == 'BUY' else 'Sell',
                'orderType': 'Market',
                'qty': str(qty)
            }

            # 4. Размещаем ордер
            order = await self.place_order_with_retry(order_params, symbol)
            if not order or order.get("retCode") != 0:
                self.logger.error(f"❌ Ордер не размещен для {symbol}")
                self.failed_trades[symbol] = self.failed_trades.get(symbol, 0) + 1
                self.last_trade_time[symbol] = datetime.utcnow()
                return

            # 5. Получаем order_id
            result = order.get("result", {})
            order_id = result.get("orderId")
            if not order_id:
                self.logger.error(f"❌ Не получен order_id для {symbol}")
                return

            # 6. Ждем создания позиции
            position_created, actual_qty = await self.wait_for_position(symbol, qty, timeout=15)
            if not position_created:
                self.logger.warning(f"⚠️ Позиция не создана для {symbol}")
                await self.send_telegram(f"❌ {symbol} - позиция не создана")
                return

            self.logger.info(f"✅ Позиция {symbol} создана: {actual_qty}")

            # 7. Размещаем защитные ордера
            protective_success = await self.place_protective_orders(
                symbol=symbol,
                side=order_params['side'],
                entry_price=entry_price,
                sl_price=sl,
                tp_price=tp,
                qty=actual_qty
            )

            # 8. Добавляем в отслеживание
            self.positions[symbol] = {
                "entry_price": entry_price,
                "sl": sl,
                "tp": tp,
                "side": direction,
                "order_id": order_id,
                "qty": actual_qty,
                "created_at": datetime.utcnow(),
                "protected": protective_success
            }

            # 9. Уведомления
            protection_status = "🛡 Защищен" if protective_success else "⚠️ Не защищен"
            await self.send_telegram(
                f"✅ <b>{symbol} {direction}</b>\n"
                f"Размер: {actual_qty}\n"
                f"Цена: {entry_price:.4f}\n"
                f"SL: {sl:.4f} | TP: {tp:.4f}\n"
                f"Статус: {protection_status}"
            )

            # Сбрасываем счетчики ошибок при успехе
            if symbol in self.api_errors:
                del self.api_errors[symbol]
            if symbol in self.failed_trades:
                del self.failed_trades[symbol]

        except Exception as e:
            self.logger.error(f"❌ Ошибка размещения ордера {symbol}: {e}")
            await self.send_telegram(f"❌ {symbol} ошибка: {str(e)}")
            self.failed_trades[symbol] = self.failed_trades.get(symbol, 0) + 1
            self.last_trade_time[symbol] = datetime.utcnow()

    async def trading_cycle(self):
        """Основной торговый цикл"""
        for symbol in self.symbols:
            try:
                if not await self.can_trade(symbol):
                    continue

                # Проверяем соединение API
                if not await self.connector.check_api_connection():
                    self.logger.warning(f"⚠️ API соединение недоступно, пропускаем {symbol}")
                    continue

                # Получаем данные
                data = await self.connector.get_klines(symbol)

                if data is None or data.empty or len(data) < 50:
                    self.logger.warning(f"❌ Недостаточно данных для {symbol}")
                    continue

                self.logger.debug(f"✅ Получено {len(data)} свечей для {symbol}")

                # Анализируем сигнал
                strategy = EnhancedSRStrategy(data)
                trade = strategy.generate_signal(data)

                if trade is not None and isinstance(trade, dict) and trade.get('signal'):
                    self.logger.info(f"📊 Сигнал для {symbol}: {trade}")
                    await self.place_order(symbol, trade)
                else:
                    self.logger.debug(f"📊 Нет сигнала для {symbol}")

            except Exception as e:
                self.logger.error(f"❌ Trading cycle error for {symbol}: {e}")
                self.api_errors[symbol] = self.api_errors.get(symbol, 0) + 1
                await asyncio.sleep(5)

    async def check_positions(self):
        """Проверка активных позиций"""
        for symbol, pos in list(self.positions.items()):
            try:
                # Получаем текущую цену
                price_data = await self.connector.get_last_price(symbol)
                if not price_data:
                    continue

                current_price = float(price_data['last_price'])
                direction = pos["side"]
                entry_price = pos["entry_price"]
                sl_price = pos["sl"]
                tp_price = pos["tp"]

                # Проверяем SL/TP
                sl_hit, tp_hit = self.check_sl_tp_hit(current_price, direction, sl_price, tp_price)

                if sl_hit:
                    await self.handle_sl_hit(symbol, pos, current_price, entry_price, direction)
                elif tp_hit:
                    await self.handle_tp_hit(symbol, pos, current_price, entry_price, direction)
                else:
                    # Периодический отчет о PnL
                    await self.report_pnl(symbol, pos, current_price, entry_price, direction)

            except Exception as e:
                self.logger.error(f"❌ Position check error for {symbol}: {e}")

    def check_sl_tp_hit(self, current_price: float, direction: str, sl_price: float, tp_price: float) -> tuple[
        bool, bool]:
        """Проверка срабатывания SL/TP"""
        if direction == "BUY":
            sl_hit = current_price <= sl_price
            tp_hit = current_price >= tp_price
        else:  # SELL
            sl_hit = current_price >= sl_price
            tp_hit = current_price <= tp_price

        return sl_hit, tp_hit

    async def handle_sl_hit(self, symbol: str, pos: dict, current_price: float, entry_price: float, direction: str):
        """Обработка срабатывания Stop Loss"""
        pnl_pct = self.calculate_pnl_pct(current_price, entry_price, direction)

        await self.send_telegram(
            f"❌ <b>{symbol}</b> SL HIT!\n"
            f"Entry: {entry_price:.4f} → Exit: {current_price:.4f}\n"
            f"PnL: {pnl_pct:+.2f}%\n"
            f"Direction: {direction}"
        )

        # Увеличиваем счетчик неудач
        self.failed_trades[symbol] = self.failed_trades.get(symbol, 0) + 1
        self.last_trade_time[symbol] = datetime.utcnow()

        failed_count = self.failed_trades[symbol]
        cooldown_minutes = 15 + (failed_count * 10)

        await self.send_telegram(
            f"🔒 {symbol} blocked for {cooldown_minutes} min\n"
            f"Failed trades: {failed_count}"
        )

        del self.positions[symbol]

    async def handle_tp_hit(self, symbol: str, pos: dict, current_price: float, entry_price: float, direction: str):
        """Обработка срабатывания Take Profit"""
        pnl_pct = self.calculate_pnl_pct(current_price, entry_price, direction)

        await self.send_telegram(
            f"✅ <b>{symbol}</b> TP HIT!\n"
            f"Entry: {entry_price:.4f} → Exit: {current_price:.4f}\n"
            f"PnL: {pnl_pct:+.2f}%\n"
            f"Direction: {direction}"
        )

        # Сбрасываем счетчик неудач
        if symbol in self.failed_trades:
            del self.failed_trades[symbol]
            await self.send_telegram(f"🎯 {symbol} - failed series reset!")

        del self.positions[symbol]

    def calculate_pnl_pct(self, current_price: float, entry_price: float, direction: str) -> float:
        """Расчет PnL в процентах"""
        if direction == "BUY":
            return ((current_price - entry_price) / entry_price) * 100
        else:  # SELL
            return ((entry_price - current_price) / entry_price) * 100

    async def report_pnl(self, symbol: str, pos: dict, current_price: float, entry_price: float, direction: str):
        """Периодический отчет о PnL"""
        # Отчет только каждые 10 минут
        last_report = self._last_pnl_report.get(symbol)
        if last_report and (datetime.utcnow() - last_report).seconds < 600:
            return

        pnl_pct = self.calculate_pnl_pct(current_price, entry_price, direction)
        balance = await self.get_account_balance()

        await self.send_telegram(
            f"📊 <b>{symbol}</b> PnL: {pnl_pct:+.2f}%\n"
            f"Entry: {entry_price:.4f} → Now: {current_price:.4f}\n"
            f"💰 Balance: {balance:.2f} USDT"
        )

        self._last_pnl_report[symbol] = datetime.utcnow()

    async def check_pending_orders(self):
        """Проверка статуса ожидающих ордеров"""
        for symbol in list(self.pending_orders.keys()):
            try:
                pending = self.pending_orders[symbol]
                order_id = pending["order_id"]
                pending["attempts"] += 1

                # Получаем статус ордера
                status = await self.connector.get_order_status(symbol, order_id)

                self.logger.debug(f"📋 Order {order_id} status: {status} (attempt {pending['attempts']})")

                if status == "Filled":
                    await self.handle_filled_order(symbol, pending)
                elif status in ["Cancelled", "Rejected", "Expired"]:
                    await self.handle_cancelled_order(symbol, pending, status)
                elif status in ["Unknown", None]:
                    await self.handle_unknown_status(symbol, pending)
                elif pending["attempts"] > 20:  # Таймаут
                    await self.handle_timeout_order(symbol, pending)

            except Exception as e:
                self.logger.error(f"❌ Pending order check error for {symbol}: {e}")
                if symbol in self.pending_orders:
                    self.pending_orders[symbol]["attempts"] += 1

    async def handle_filled_order(self, symbol: str, pending: dict):
        """Обработка исполненного ордера"""
        trade = pending["trade"]
        order_id = pending["order_id"]

        self.positions[symbol] = {
            "entry_price": trade["entry"],
            "sl": trade["sl"],
            "tp": trade["tp"],
            "side": pending["direction"],
            "order_id": order_id,
            "qty": pending["qty"],
            "created_at": datetime.utcnow()
        }

        del self.pending_orders[symbol]

        await self.send_telegram(
            f"✅ <b>{symbol}</b> order filled!\n"
            f"ID: {order_id}\n"
            f"Entry: {trade['entry']:.4f}\n"
            f"Direction: {pending['direction']}\n"
            f"Qty: {pending['qty']}"
        )

        protective_success = await self.place_protective_orders(
            symbol=symbol,
            side='Buy' if pending["direction"] == 'BUY' else 'Sell',
            entry_price=trade["entry"],
            sl_price=trade["sl"],
            tp_price=trade["tp"],
            qty=pending["qty"]
        )

        if protective_success:
            await self.send_telegram(f"🛡 <b>{symbol}</b> - Защитные ордера размещены")
        else:
            await self.send_telegram(f"⚠️ <b>{symbol}</b> - Ошибка размещения защитных ордеров")

    async def handle_cancelled_order(self, symbol: str, pending: dict, status: str):
        """Обработка отмененного ордера"""
        order_id = pending["order_id"]
        del self.pending_orders[symbol]

        await self.send_telegram(
            f"❌ <b>{symbol}</b> order {status.lower()}\n"
            f"ID: {order_id}"
        )

    async def handle_unknown_status(self, symbol: str, pending: dict):
        """Обработка неопределенного статуса"""
        order_id = pending["order_id"]

        # Проверяем наличие позиции
        try:
            positions = await self.connector.get_positions(symbol)
            has_position = False

            if positions and len(positions) > 0:
                has_position = any(float(pos.get('size', 0)) != 0 for pos in positions)

            if has_position:
                await self.handle_filled_order(symbol, pending)
            elif pending["attempts"] > 10:
                # Прекращаем отслеживание
                del self.pending_orders[symbol]
                await self.send_telegram(
                    f"⏰ <b>{symbol}</b> tracking stopped\n"
                    f"ID: {order_id}\n"
                    f"Status unclear after {pending['attempts']} checks"
                )
        except Exception as e:
            self.logger.error(f"❌ Error checking positions for {symbol}: {e}")

    async def handle_timeout_order(self, symbol: str, pending: dict):
        """Обработка ордера по таймауту"""
        order_id = pending["order_id"]

        # Пытаемся отменить ордер
        try:
            cancel_result = await self.connector.cancel_order(symbol, order_id)
            del self.pending_orders[symbol]

            await self.send_telegram(
                f"⏰ <b>{symbol}</b> order timeout\n"
                f"ID: {order_id}\n"
                f"Cancellation: {'✅' if cancel_result else '❌'}"
            )
        except Exception as e:
            self.logger.error(f"❌ Error cancelling order {order_id}: {e}")

    async def check_emergency_conditions(self):
        """Проверка аварийных условий"""
        try:
            current_balance = await self.get_account_balance()

            if self.daily_start_balance is None:
                self.daily_start_balance = current_balance
                return

            # Проверяем дневную просадку
            daily_loss_pct = (self.daily_start_balance - current_balance) / self.daily_start_balance

            if daily_loss_pct >= self.max_daily_loss:
                self.emergency_stop = True
                self.logger.critical(f"🚨 АВАРИЙНАЯ ОСТАНОВКА! Дневная просадка: {daily_loss_pct:.2%}")

                await self.send_telegram(
                    f"🚨 <b>АВАРИЙНАЯ ОСТАНОВКА!</b>\n"
                    f"Дневная просадка: {daily_loss_pct:.2%}\n"
                    f"Начальный баланс: {self.daily_start_balance:.2f}\n"
                    f"Текущий баланс: {current_balance:.2f}\n"
                    f"Бот остановлен до завтра"
                )

                # Закрываем все открытые позиции
                await self.close_all_positions()

        except Exception as e:
            self.logger.error(f"❌ Error checking emergency conditions: {e}")

    async def close_all_positions(self):
        """Закрытие всех открытых позиций"""
        try:
            for symbol in list(self.positions.keys()):
                try:
                    positions = await self.connector.get_positions(symbol)
                    if not positions:
                        continue

                    for pos in positions:
                        pos_size = float(pos.get('size', 0))
                        if pos_size == 0:
                            continue

                        pos_side = pos.get('side', '')
                        close_side = "Sell" if pos_side == "Buy" else "Buy"

                        close_params = {
                            "category": "linear",
                            "symbol": symbol,
                            "side": close_side,
                            "orderType": "Market",
                            "qty": str(abs(pos_size)),
                            "reduceOnly": True
                        }

                        response = await self.connector.place_order(close_params)

                        if response and response.get("retCode") == 0:
                            self.logger.info(f"🚨 Аварийно закрыта позиция {symbol}")
                            await self.send_telegram(f"🚨 Закрыта позиция {symbol}")
                        else:
                            self.logger.error(f"❌ Не удалось закрыть позицию {symbol}: {response}")

                except Exception as e:
                    self.logger.error(f"❌ Error closing position {symbol}: {e}")

            # Очищаем все позиции из отслеживания
            self.positions.clear()

        except Exception as e:
            self.logger.error(f"❌ Error in close_all_positions: {e}")

    async def send_status_report(self, cycle_count: int):
        """Отправка статуса бота"""
        try:
            total_api_errors = sum(self.api_errors.values())
            blocked_symbols = len([s for s in self.symbols if s in self.last_trade_time])
            current_balance = await self.get_account_balance()

            balance_change = 0.0
            if self.start_balance and self.start_balance > 0:
                balance_change = ((current_balance - self.start_balance) / self.start_balance) * 100

            await self.send_telegram(
                f"📈 Bot Status (cycle {cycle_count}):\n"
                f"• Active positions: {len(self.positions)}\n"
                f"• Pending orders: {len(self.pending_orders)}\n"
                f"• Blocked symbols: {blocked_symbols}\n"
                f"• API errors: {total_api_errors}\n"
                f"• Emergency stop: {'🔴 YES' if self.emergency_stop else '🟢 NO'}\n"
                f"• Balance: {current_balance:.2f} USDT ({balance_change:+.2f}%)"
            )

        except Exception as e:
            self.logger.error(f"❌ Status report error: {e}")

    async def reset_daily_counters(self):
        """Сброс дневных счетчиков (вызывать раз в день)"""
        try:
            current_time = datetime.utcnow()

            # Проверяем, нужно ли сбросить дневные счетчики (новый день)
            if not hasattr(self, '_last_reset_date'):
                self._last_reset_date = current_time.date()
                return

            if current_time.date() > self._last_reset_date:
                self.daily_start_balance = await self.get_account_balance()
                self.emergency_stop = False
                self._last_reset_date = current_time.date()

                self.logger.info(f"🔄 Дневные счетчики сброшены. Новый стартовый баланс: {self.daily_start_balance}")
                await self.send_telegram(
                    f"🌅 Новый торговый день!\n"
                    f"Стартовый баланс: {self.daily_start_balance:.2f} USDT\n"
                    f"Аварийная остановка сброшена"
                )

        except Exception as e:
            self.logger.error(f"❌ Error resetting daily counters: {e}")

    async def run(self):
        """Главный цикл бота"""
        self.logger.info("🤖 Bot started")
        await self.send_telegram("🤖 Bot started")

        # Получаем начальный баланс
        self.start_balance = await self.get_account_balance()
        self.daily_start_balance = self.start_balance

        if not self.start_balance or self.start_balance <= 0:
            await self.send_telegram("❌ Critical error: zero balance!")
            self.logger.critical("❌ Критическая ошибка: нулевой баланс!")
            return

        self.logger.info(f"💰 Стартовый баланс: {self.start_balance}")

        cycle_count = 0

        while True:
            try:
                cycle_count += 1
                self.logger.info(f"=== Cycle {cycle_count} ===")

                # 1. Проверяем дневные счетчики
                await self.reset_daily_counters()

                # 2. Проверяем аварийные условия
                await self.check_emergency_conditions()

                # Если аварийная остановка - пропускаем торговлю
                if self.emergency_stop:
                    self.logger.info("🚨 Аварийная остановка активна, торговля приостановлена")
                    await asyncio.sleep(300)  # 5 минут
                    continue

                # 3. Проверяем ожидающие ордера
                await self.check_pending_orders()

                # 4. Проверяем активные позиции
                await self.check_positions()

                # 5. Ищем новые торговые возможности
                await self.trading_cycle()

                # Периодический отчет
                if cycle_count % 15 == 0:  # Каждые 15 минут
                    await self.send_status_report(cycle_count)

                # Обновляем баланс каждые 30 циклов
                if cycle_count % 30 == 0:
                    self.start_balance = await self.get_account_balance()

                await asyncio.sleep(60)  # 1 минута между циклами

            except KeyboardInterrupt:
                self.logger.info("🛑 Bot stopped by user")
                await self.send_telegram("🛑 Bot stopped by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Main loop error: {e}")
                await self.send_telegram(f"⚠️ Main loop error: {str(e)}")
                await asyncio.sleep(30)


if __name__ == "__main__":
    bot = TradingBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        bot.logger.info("🛑 Bot stopped by user")
    except Exception as e:
        bot.logger.critical(f"💥 Fatal error: {e}")