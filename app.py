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
        self.symbol_info = {}  # Кэш информации о символах
        self.setup_logging()

    def setup_logging(self):
        """Настройка логирования с ротацией файлов"""
        from logging.handlers import RotatingFileHandler

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
        balance = await self.connector.get_wallet_balance()
        self.logger.info(f"Current balance: {balance}")

        if not balance or balance <= 0:
            await self.send_telegram("⚠️ Внимание: нулевой баланс на счете!")

        return balance

    async def get_symbol_info(self, symbol: str) -> dict:
        """Получение информации о символе с кэшированием"""
        if symbol in self.symbol_info:
            return self.symbol_info[symbol]

        try:
            info = await self.connector.get_instruments_info(symbol)
            if info:
                self.symbol_info[symbol] = info
                self.logger.info(f"Loaded symbol info for {symbol}: {info}")
                return info
        except Exception as e:
            self.logger.error(f"Failed to get symbol info for {symbol}: {e}")

        # Возвращаем дефолтные значения
        default_info = {
            'minOrderQty': MIN_QTY.get(symbol, 0.001),
            'qtyStep': 0.001,
            'minOrderAmt': 1.0,
            'tickSize': 0.01
        }
        self.symbol_info[symbol] = default_info
        return default_info

    async def calculate_position_size(self, price: float, symbol: str) -> tuple[float, bool]:
        """
        Рассчитывает размер позиции с учетом минимальных требований
        Возвращает: (quantity, is_valid)
        """
        try:
            if not self.start_balance or self.start_balance <= 0:
                self.logger.warning("Start balance is None or zero!")
                return 0.0, False

            # Получаем информацию о символе
            symbol_info = await self.get_symbol_info(symbol)
            min_qty = symbol_info['minOrderQty']
            qty_step = symbol_info['qtyStep']
            min_notional = symbol_info.get('minOrderAmt', 1.0)

            # Рассчитываем размер позиции (1.5% от баланса)
            risk_amount = self.start_balance * (RISK_PERCENT / 100)
            calculated_qty = risk_amount / price

            # Проверяем минимальную сумму ордера
            if calculated_qty * price < min_notional:
                calculated_qty = min_notional / price
                self.logger.info(f"Adjusted qty to meet min notional: {calculated_qty}")

            # Проверяем минимальное количество
            if calculated_qty < min_qty:
                calculated_qty = min_qty
                self.logger.info(f"Adjusted qty to meet min quantity: {calculated_qty}")

            # Округляем до нужного шага
            precision = QTY_PRECISION.get(symbol, 3)

            # Используем Decimal для точного округления
            decimal_qty = Decimal(str(calculated_qty))
            decimal_step = Decimal(str(qty_step))

            # Округляем вниз до ближайшего шага
            steps = decimal_qty / decimal_step
            rounded_steps = steps.quantize(Decimal('1'), rounding=ROUND_DOWN)
            final_qty = float(rounded_steps * decimal_step)

            # Финальная проверка
            if final_qty < min_qty:
                final_qty = min_qty

            # Проверяем, не превышает ли позиция 5% баланса (защита)
            position_value = final_qty * price
            if position_value > self.start_balance * 0.05:
                self.logger.warning(f"Position too large: {position_value:.2f} > {self.start_balance * 0.05:.2f}")
                return 0.0, False

            self.logger.info(f"Position calculation for {symbol}: "
                             f"price={price:.4f}, risk_amount={risk_amount:.2f}, "
                             f"calculated={calculated_qty:.6f}, final={final_qty:.6f}")

            return final_qty, True

        except Exception as e:
            self.logger.error(f"Position calculation error for {symbol}: {e}")
            return 0.0, False

    async def can_trade(self, symbol: str) -> bool:
        """Проверяет возможность торговли символом"""
        # Проверяем открытые позиции
        if symbol in self.positions:
            return False

        # Проверяем ожидающие ордера
        if symbol in self.pending_orders:
            return False

        # Проверяем cooldown с учетом неудачных сделок
        last_time = self.last_trade_time.get(symbol)
        if last_time:
            failed_count = self.failed_trades.get(symbol, 0)
            cooldown_minutes = 15 + (failed_count * 10)
            cooldown_minutes = min(cooldown_minutes, 120)  # Максимум 2 часа

            time_since = datetime.utcnow() - last_time
            if time_since < timedelta(minutes=cooldown_minutes):
                return False

        # Проверяем частоту ошибок API
        api_error_count = self.api_errors.get(symbol, 0)
        if api_error_count >= 5:
            # Блокируем символ на 1 час при частых ошибках API
            if last_time and (datetime.utcnow() - last_time) < timedelta(hours=1):
                return False

        # Проверяем баланс
        balance = await self.get_account_balance()
        if balance < 10:
            return False

        return True

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

                # ИСПРАВЛЕНИЕ: Правильная проверка DataFrame
                if data is None:
                    self.logger.warning(f"❌ Данные не получены для {symbol}")
                    continue

                if data.empty:  # Правильная проверка пустого DataFrame
                    self.logger.warning(f"❌ Пустые данные для {symbol}")
                    continue

                if len(data) < 50:
                    self.logger.warning(f"❌ Недостаточно данных для {symbol}: {len(data)}")
                    continue

                self.logger.debug(f"✅ Получено {len(data)} свечей для {symbol}")

                # Анализируем сигнал
                strategy = EnhancedSRStrategy(data)
                trade = strategy.generate_signal(data)

                # ИСПРАВЛЕНИЕ: Правильная проверка результата стратегии
                if trade is not None and isinstance(trade, dict) and trade.get('signal'):
                    self.logger.info(f"📊 Сигнал для {symbol}: {trade}")
                    await self.place_order(symbol, trade)
                else:
                    self.logger.debug(f"📊 Нет сигнала для {symbol}")

            except Exception as e:
                self.logger.error(f"Trading cycle error for {symbol}: {e}")
                # Увеличиваем счетчик ошибок API
                self.api_errors[symbol] = self.api_errors.get(symbol, 0) + 1
                await asyncio.sleep(5)

    async def get_safe_market_price(self, symbol: str, side: str, entry_price: float):
        """Использует цену входа из сигнала с небольшим буфером для безопасности"""
        try:
            # Добавляем буфер для безопасности
            if side == "Buy":
                # Для покупки берем цену чуть выше цены входа
                safe_price = entry_price * 1.002  # +0.2%
            else:
                # Для продажи берем цену чуть ниже цены входа
                safe_price = entry_price * 0.998  # -0.2%

            safe_price = round(safe_price, 2)  # Округляем до 2 знаков для SOL
            self.logger.info(f"💰 Безопасная цена для {symbol} ({side}): {entry_price} → {safe_price}")
            return safe_price

        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета безопасной цены для {symbol}: {e}")
            return None

    # ИСПРАВЛЕНИЕ 4: Улучшенная функция place_order_with_retry (ИДЕТ ПЕРВОЙ)
    async def place_order_with_retry(self, order_params: dict, symbol: str, max_retries: int = 3) -> dict:
        """Размещение ордера с экспоненциальным бэкоффом"""
        for attempt in range(max_retries):
            try:
                order = await self.connector.place_order(order_params)

                if order is None:
                    self.api_errors[symbol] = self.api_errors.get(symbol, 0) + 1
                    error_count = self.api_errors[symbol]

                    self.logger.error(f"❌ Получен None ответ от Bybit для {symbol} (ошибка #{error_count})")

                    if attempt < max_retries - 1:
                        # Экспоненциальная задержка: 1s, 2s, 4s
                        wait_time = (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    return None

                ret_code = order.get("retCode")
                ret_msg = order.get("retMsg", "Unknown error")

                if ret_code == 0:
                    return order

                # Обработка специфических ошибок
                if ret_code == 110017:  # "current position is zero"
                    self.logger.warning(f"⚠️ Позиция еще не создана для {symbol}, попытка {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0)  # Ждем дольше для этой ошибки
                        continue

                elif ret_code == 10001:  # Minimum size error
                    current_qty = float(order_params['qty'])
                    symbol_info = await self.get_symbol_info(symbol)
                    min_qty = symbol_info['minOrderQty']

                    if current_qty < min_qty:
                        new_qty = min_qty * 1.1
                        order_params['qty'] = str(round(new_qty, QTY_PRECISION.get(symbol, 3)))
                        self.logger.warning(f"Adjusting qty from {current_qty} to {new_qty} for {symbol}")

                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue

                elif ret_code in [10002, 10003]:  # Balance errors
                    self.logger.error(f"Недостаточный баланс для {symbol}")
                    await self.send_telegram(f"❌ {symbol} недостаточный баланс")
                    break

                else:
                    self.logger.error(f"❌ Ошибка размещения ордера: код {ret_code}, сообщение: {ret_msg}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue

                break

            except Exception as e:
                self.logger.error(f"Exception on attempt {attempt + 1} for {symbol}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return None

    # ИСПРАВЛЕНИЕ 2: Исправленная функция place_order
    async def place_order(self, symbol: str, trade: dict):
        """Размещение ордера с ПРОСТЫМ решением"""
        try:
            direction = trade["signal"]
            sl = trade["sl"]
            tp = trade["tp"]
            entry_price = trade["entry"]

            # Рассчитываем размер позиции
            qty, is_valid = await self.calculate_position_size(entry_price, symbol)

            if not is_valid or qty <= 0:
                self.logger.warning(f"❌ Нулевое количество для {symbol}: {qty}")
                return

            self.logger.info(f"💰 Расчёт позиции: qty={qty}, entry={entry_price}, balance={self.start_balance}")

            # Формируем параметры ордера
            if symbol == "SOLUSDT":
                safe_price = await self.get_safe_market_price(
                    symbol,
                    'Buy' if direction == 'BUY' else 'Sell',
                    entry_price
                )

                if not safe_price:
                    self.logger.error(f"❌ Не удалось получить безопасную цену для {symbol}")
                    return

                order_params = {
                    'category': 'linear',
                    'symbol': symbol,
                    'side': 'Buy' if direction == 'BUY' else 'Sell',
                    'orderType': 'Limit',
                    'qty': str(qty),
                    'price': str(safe_price),
                    'timeInForce': 'IOC'
                }

                self.logger.info(f"💰 SOLUSDT лимитный ордер: entry={entry_price}, safe={safe_price}")
            else:
                order_params = {
                    'category': 'linear',
                    'symbol': symbol,
                    'side': 'Buy' if direction == 'BUY' else 'Sell',
                    'orderType': 'Market',
                    'qty': str(qty)
                }

            self.logger.info(f"📤 Отправка ордера: {order_params}")

            # Размещаем основной ордер
            order = await self.place_order_with_retry(order_params, symbol)

            if not order:
                return

            # Получаем order_id
            result = order.get("result", {})
            order_id = result.get("orderId")

            if not order_id:
                self.logger.error(f"❌ Не удалось получить order_id! Ответ: {order}")
                await self.send_telegram(f"❌ {symbol} - Не получен ID ордера")
                return

            self.logger.info(f"✅ Order {order_id} placed successfully with qty {qty}")

            # 🔥 ПРОСТОЕ РЕШЕНИЕ: Просто ждем 3-5 секунд
            self.logger.info(f"⏳ Ожидание исполнения ордера {symbol}...")
            await asyncio.sleep(3.0)  # Фиксированная задержка 3 секунды

            # Дополнительная проверка позиции (опционально)
            try:
                positions = await self.connector.get_positions(symbol)
                has_position = False
                if positions and len(positions) > 0:
                    has_position = any(float(pos.get('size', 0)) != 0 for pos in positions)

                if not has_position:
                    self.logger.warning(f"⚠️ Позиция не найдена для {symbol}, но продолжаем")
                    # Не прерываем процесс, просто предупреждаем
            except Exception as e:
                self.logger.debug(f"Ошибка проверки позиции: {e}")

            # Сбрасываем счетчики ошибок при успехе
            if symbol in self.api_errors:
                del self.api_errors[symbol]

            # Добавляем в ожидающие ордера
            self.pending_orders[symbol] = {
                "order_id": order_id,
                "trade": trade,
                "direction": direction,
                "qty": qty,
                "attempts": 0,
                "created_at": datetime.utcnow()
            }

            await self.send_telegram(
                f"📤 <b>{symbol} {direction}</b> order placed\n"
                f"ID: {order_id}\n"
                f"Qty: {qty}\n"
                f"Entry: {entry_price:.4f}\n"
                f"SL: {sl:.4f} | TP: {tp:.4f}"
            )

            # Теперь размещаем защитные ордера
            protective_success = await self.place_protective_orders(
                symbol=symbol,
                side=order_params['side'],
                entry_price=entry_price,
                sl_price=sl,
                tp_price=tp,
                qty=qty
            )

            if protective_success:
                self.logger.info(f"🛡 Защитные ордера размещены для {symbol}")
                await self.send_telegram(f"🛡 <b>{symbol}</b> - Stop-Loss и Take-Profit размещены")
            else:
                self.logger.warning(f"⚠️ Не удалось разместить защитные ордера для {symbol}")
                await self.send_telegram(f"⚠️ <b>{symbol}</b> - Ошибка размещения защитных ордеров")

        except Exception as e:
            self.logger.error(f"Order placement error for {symbol}: {e}")
            await self.send_telegram(f"❌ {symbol} order error: {str(e)}")

            # Увеличиваем счетчик неудач
            self.failed_trades[symbol] = self.failed_trades.get(symbol, 0) + 1
            self.last_trade_time[symbol] = datetime.utcnow()

    # ИСПРАВЛЕНИЕ 3: Улучшенная функция размещения защитных ордеров
    async def place_protective_orders(self, symbol: str, side: str, entry_price: float, sl_price: float,
                                      tp_price: float, qty: float):
        """Размещает защитные ордера с дополнительными проверками"""
        try:
            # Определяем противоположную сторону для закрытия позиции
            close_side = "Sell" if side == "Buy" else "Buy"

            # Добавляем задержку для стабилизации позиции
            await asyncio.sleep(1.0)

            sl_success = False
            tp_success = False

            # 1. Размещаем стоп-лосс
            try:
                sl_order = {
                    "category": "linear",
                    "symbol": symbol,
                    "side": close_side,
                    "orderType": "Limit",
                    "qty": str(qty),
                    "price": str(sl_price),
                    "reduceOnly": True,
                    "timeInForce": "GTC"
                }

                # Используем больше попыток для защитных ордеров
                sl_response = await self.place_order_with_retry(sl_order, symbol, max_retries=5)
                if sl_response:
                    self.logger.info(f"✅ Stop-Loss (Limit) размещен для {symbol}: {sl_price}")
                    sl_success = True
                else:
                    self.logger.error(f"❌ Ошибка размещения Stop-Loss для {symbol}")

            except Exception as e:
                self.logger.error(f"❌ Исключение при размещении Stop-Loss для {symbol}: {e}")

            # Пауза между ордерами
            await asyncio.sleep(0.5)

            # 2. Размещаем тейк-профит
            try:
                tp_order = {
                    "category": "linear",
                    "symbol": symbol,
                    "side": close_side,
                    "orderType": "Limit",
                    "qty": str(qty),
                    "price": str(tp_price),
                    "reduceOnly": True,
                    "timeInForce": "GTC"
                }

                tp_response = await self.place_order_with_retry(tp_order, symbol, max_retries=5)
                if tp_response:
                    self.logger.info(f"✅ Take-Profit (Limit) размещен для {symbol}: {tp_price}")
                    tp_success = True
                else:
                    self.logger.error(f"❌ Ошибка размещения Take-Profit для {symbol}")

            except Exception as e:
                self.logger.error(f"❌ Исключение при размещении Take-Profit для {symbol}: {e}")

            return sl_success and tp_success

        except Exception as e:
            self.logger.error(f"❌ Общая ошибка размещения защитных ордеров для {symbol}: {e}")
            return False

    async def place_order_with_retry(self, order_params: dict, symbol: str, max_retries: int = 3) -> dict:
        """Размещение ордера с экспоненциальным бэкоффом"""
        for attempt in range(max_retries):
            try:
                order = await self.connector.place_order(order_params)

                if order is None:
                    self.api_errors[symbol] = self.api_errors.get(symbol, 0) + 1
                    error_count = self.api_errors[symbol]

                    self.logger.error(f"❌ Получен None ответ от Bybit для {symbol} (ошибка #{error_count})")

                    if attempt < max_retries - 1:
                        # Экспоненциальная задержка: 1s, 2s, 4s
                        wait_time = (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    return None

                ret_code = order.get("retCode")
                ret_msg = order.get("retMsg", "Unknown error")

                if ret_code == 0:
                    return order

                # Обработка специфических ошибок
                if ret_code == 110017:  # "current position is zero"
                    self.logger.warning(f"⚠️ Позиция еще не создана для {symbol}, попытка {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0)  # Ждем дольше для этой ошибки
                        continue

                elif ret_code == 10001:  # Minimum size error
                    current_qty = float(order_params['qty'])
                    symbol_info = await self.get_symbol_info(symbol)
                    min_qty = symbol_info['minOrderQty']

                    if current_qty < min_qty:
                        new_qty = min_qty * 1.1
                        order_params['qty'] = str(round(new_qty, QTY_PRECISION.get(symbol, 3)))
                        self.logger.warning(f"Adjusting qty from {current_qty} to {new_qty} for {symbol}")

                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue

                elif ret_code in [10002, 10003]:  # Balance errors
                    self.logger.error(f"Недостаточный баланс для {symbol}")
                    await self.send_telegram(f"❌ {symbol} недостаточный баланс")
                    break

                else:
                    self.logger.error(f"❌ Ошибка размещения ордера: код {ret_code}, сообщение: {ret_msg}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue

                break

            except Exception as e:
                self.logger.error(f"Exception on attempt {attempt + 1} for {symbol}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return None

    async def check_pending_orders(self):
        """Проверка статуса ожидающих ордеров"""
        for symbol in list(self.pending_orders.keys()):
            try:
                pending = self.pending_orders[symbol]
                order_id = pending["order_id"]
                pending["attempts"] += 1

                # Получаем статус ордера
                status = await self.connector.get_order_status(symbol, order_id)

                self.logger.debug(f"Order {order_id} status: {status} (attempt {pending['attempts']})")

                if status == "Filled":
                    # Ордер исполнен
                    await self._handle_filled_order(symbol, pending)

                elif status in ["Cancelled", "Rejected", "Expired"]:
                    # Ордер отменен
                    await self._handle_cancelled_order(symbol, pending, status)

                elif status in ["Unknown", None]:
                    # Неопределенный статус - проверяем через позиции
                    await self._handle_unknown_status(symbol, pending)

                elif pending["attempts"] > 20:  # Таймаут
                    await self._handle_timeout_order(symbol, pending)

            except Exception as e:
                self.logger.error(f"Pending order check error for {symbol}: {e}")
                if symbol in self.pending_orders:
                    self.pending_orders[symbol]["attempts"] += 1

    async def _handle_filled_order(self, symbol: str, pending: dict):
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

    async def _handle_cancelled_order(self, symbol: str, pending: dict, status: str):
        """Обработка отмененного ордера"""
        order_id = pending["order_id"]
        del self.pending_orders[symbol]

        await self.send_telegram(
            f"❌ <b>{symbol}</b> order {status.lower()}\n"
            f"ID: {order_id}"
        )

    async def _handle_unknown_status(self, symbol: str, pending: dict):
        """Обработка неопределенного статуса"""
        order_id = pending["order_id"]

        # Проверяем наличие позиции
        try:
            positions = await self.connector.get_positions(symbol)
            has_position = False

            # ИСПРАВЛЕНИЕ: Правильная проверка позиций
            if positions and len(positions) > 0:
                has_position = any(float(pos.get('size', 0)) != 0 for pos in positions)

            if has_position:
                await self._handle_filled_order(symbol, pending)
            elif pending["attempts"] > 10:
                # Прекращаем отслеживание
                del self.pending_orders[symbol]
                await self.send_telegram(
                    f"⏰ <b>{symbol}</b> tracking stopped\n"
                    f"ID: {order_id}\n"
                    f"Status unclear after {pending['attempts']} checks"
                )
        except Exception as e:
            self.logger.error(f"Error checking positions for {symbol}: {e}")

    async def _handle_timeout_order(self, symbol: str, pending: dict):
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
            self.logger.error(f"Error cancelling order {order_id}: {e}")

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
                sl_hit, tp_hit = self._check_sl_tp(current_price, direction, sl_price, tp_price)

                if sl_hit:
                    await self._handle_sl_hit(symbol, pos, current_price, entry_price, direction)
                elif tp_hit:
                    await self._handle_tp_hit(symbol, pos, current_price, entry_price, direction)
                else:
                    # Периодический отчет о PnL
                    await self._report_pnl(symbol, pos, current_price, entry_price, direction)

            except Exception as e:
                self.logger.error(f"Position check error for {symbol}: {e}")

    def _check_sl_tp(self, current_price: float, direction: str, sl_price: float, tp_price: float) -> tuple[bool, bool]:
        """Проверка срабатывания SL/TP"""
        if direction == "BUY":
            sl_hit = current_price <= sl_price
            tp_hit = current_price >= tp_price
        else:  # SELL
            sl_hit = current_price >= sl_price
            tp_hit = current_price <= tp_price

        return sl_hit, tp_hit

    async def _handle_sl_hit(self, symbol: str, pos: dict, current_price: float, entry_price: float, direction: str):
        """Обработка срабатывания Stop Loss"""
        pnl_pct = self._calculate_pnl_pct(current_price, entry_price, direction)

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

    async def _handle_tp_hit(self, symbol: str, pos: dict, current_price: float, entry_price: float, direction: str):
        """Обработка срабатывания Take Profit"""
        pnl_pct = self._calculate_pnl_pct(current_price, entry_price, direction)

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

    def _calculate_pnl_pct(self, current_price: float, entry_price: float, direction: str) -> float:
        """Расчет PnL в процентах"""
        if direction == "BUY":
            return ((current_price - entry_price) / entry_price) * 100
        else:  # SELL
            return ((entry_price - current_price) / entry_price) * 100

    async def _report_pnl(self, symbol: str, pos: dict, current_price: float, entry_price: float, direction: str):
        """Периодический отчет о PnL"""
        # Отчет только каждые 10 минут
        if not hasattr(self, '_last_pnl_report'):
            self._last_pnl_report = {}

        last_report = self._last_pnl_report.get(symbol)
        if last_report and (datetime.utcnow() - last_report).seconds < 600:
            return

        pnl_pct = self._calculate_pnl_pct(current_price, entry_price, direction)
        balance = await self.get_account_balance()

        await self.send_telegram(
            f"📊 <b>{symbol}</b> PnL: {pnl_pct:+.2f}%\n"
            f"Entry: {entry_price:.4f} → Now: {current_price:.4f}\n"
            f"💰 Balance: {balance:.2f} USDT"
        )

        self._last_pnl_report[symbol] = datetime.utcnow()

    async def run(self):
        """Главный цикл бота"""
        await self.send_telegram("🤖 Bot started")

        # Получаем начальный баланс
        self.start_balance = await self.get_account_balance()

        if not self.start_balance or self.start_balance <= 0:
            await self.send_telegram("❌ Critical error: zero balance!")
            return

        cycle_count = 0

        while True:
            try:
                cycle_count += 1
                self.logger.info(f"=== Cycle {cycle_count} ===")

                # 1. Проверяем ожидающие ордера
                await self.check_pending_orders()

                # 2. Проверяем активные позиции
                await self.check_positions()

                # 3. Ищем новые торговые возможности
                await self.trading_cycle()

                # Периодический отчет
                if cycle_count % 15 == 0:  # Каждые 15 минут
                    await self._send_status_report(cycle_count)

                # Обновляем баланс каждые 30 циклов
                if cycle_count % 30 == 0:
                    self.start_balance = await self.get_account_balance()

                await asyncio.sleep(60)  # 1 минута между циклами

            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                await self.send_telegram(f"⚠️ Main loop error: {str(e)}")
                await asyncio.sleep(30)

    async def _send_status_report(self, cycle_count: int):
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
                f"• Balance: {current_balance:.2f} USDT ({balance_change:+.2f}%)"
            )
        except Exception as e:
            self.logger.error(f"Status report error: {e}")


if __name__ == "__main__":
    bot = TradingBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        bot.logger.info("Bot stopped by user")
    except Exception as e:
        bot.logger.critical(f"Fatal error: {e}")