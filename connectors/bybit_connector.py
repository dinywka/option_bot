# #connectors/bybit_connector.py
#
# import os
# import logging
# import asyncio
# import pandas as pd
# from pybit.unified_trading import HTTP
# from config.paths import LOG_DIR
#
#
# class BybitConnector:
#     def __init__(self):
#         self.logger = logging.getLogger('BybitConnector')
#         self.session = HTTP(
#             api_key=os.getenv("BYBIT_API_KEY"),
#             api_secret=os.getenv("BYBIT_API_SECRET"),
#             testnet=os.getenv("BYBIT_DEMO") == "true"
#         )
#
#     async def run_blocking(self, func, *args, **kwargs):
#         loop = asyncio.get_event_loop()
#         return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
#
#     async def get_klines(self, symbol):
#         try:
#             timeframe = os.getenv("TIMEFRAME", "5")
#             valid_intervals = {
#                 '1': '1', '3': '3', '5': '5', '15': '15', '30': '30',
#                 '60': '60', '120': '120', '240': '240', '360': '360',
#                 '720': '720', 'D': 'D', 'W': 'W', 'M': 'M'
#             }
#             interval = valid_intervals.get(timeframe, '5')
#
#             resp = await self.run_blocking(
#                 self.session.get_kline,
#                 category="linear",
#                 symbol=symbol,
#                 interval=interval,
#                 limit=100
#             )
#             return self._process_data(resp)
#         except Exception as e:
#             self._log_error(f"Kline error: {str(e)}")
#             return None
#
#     async def get_wallet_balance(self):
#         try:
#             response = await self.run_blocking(
#                 self.session.get_wallet_balance,
#                 accountType="UNIFIED"
#             )
#             self.logger.debug(f"Raw balance response: {response}")
#
#             if not response or response.get('retCode') != 0:
#                 self._log_error(f"Bad API response: {response}")
#                 return 0.0
#
#             if 'result' in response and 'list' in response['result']:
#                 account_data = response['result']['list'][0]
#                 if 'totalAvailableBalance' in account_data:
#                     return float(account_data['totalAvailableBalance'])
#                 if 'coin' in account_data:
#                     for coin in account_data['coin']:
#                         if coin.get('coin') == 'USDT':
#                             return float(coin.get('equity', 0))
#             return 0.0
#
#         except Exception as e:
#             self._log_error(f"Balance processing failed: {str(e)}")
#             return 0.0
#
#     async def get_last_price(self, symbol):
#         try:
#             response = await self.run_blocking(
#                 self.session.get_tickers,
#                 category="linear",
#                 symbol=symbol
#             )
#             if response and response['result'] and response['result']['list']:
#                 return {
#                     'last_price': float(response['result']['list'][0]['lastPrice']),
#                     'bid': float(response['result']['list'][0]['bid1Price']),
#                     'ask': float(response['result']['list'][0]['ask1Price'])
#                 }
#             return None
#         except Exception as e:
#             self._log_error(f"Price error: {str(e)}")
#             return None
#
#     async def place_order(self, params):
#         try:
#             self.logger.info(f"📤 Отправка ордера на Bybit: {params}")
#             resp = await self.run_blocking(self.session.place_order, **params)
#             self.logger.info(f"📥 Ответ от Bybit: {resp}")
#             return resp
#         except Exception as e:
#             self._log_error(f"Order placement failed: {str(e)}")
#             return None
#
#     def get_order_status(self, symbol: str, order_id: str):
#         try:
#             response = self.session.get_order_realtime(
#                 category="linear",
#                 symbol=symbol,
#                 orderId=order_id
#             )
#             self.logger.info(f"🔍 Статус ордера {order_id}: {response}")
#             result = response.get("result", {}).get("list", [])
#             if result:
#                 return result[0].get("orderStatus")  # 'Filled', 'Cancelled', 'Created'
#             else:
#                 return None
#         except Exception as e:
#             self.logger.error(f"❌ Ошибка получения статуса ордера: {e}")
#             return None
#
#     async def check_api_connection(self):
#         try:
#             response = await self.run_blocking(self.session.get_server_time)
#             return response['retCode'] == 0
#         except Exception:
#             return False
#
#     def _process_data(self, resp):
#         try:
#             if not resp or 'result' not in resp or not resp['result']['list']:
#                 return None
#
#             df = pd.DataFrame(
#                 resp['result']['list'],
#                 columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
#             )
#
#             numeric_cols = ['open', 'high', 'low', 'close', 'volume']
#             df[numeric_cols] = df[numeric_cols].astype(float)
#             df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
#
#             return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
#         except Exception as e:
#             self._log_error(f"Data processing error: {str(e)}")
#             return None
#
#     def _log_error(self, msg):
#         print(f"[BybitConnector ERROR] {msg}")
#         self.logger.error(msg)

#connectors/bybit_connector.py
import os
import logging
import asyncio
import pandas as pd
from pybit.unified_trading import HTTP


class BybitConnector:
    def __init__(self):
        self.logger = logging.getLogger('BybitConnector')
        self.session = HTTP(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            testnet=os.getenv("BYBIT_DEMO") == "true"
        )

    async def run_blocking(self, func, *args, **kwargs):
        """Выполнение блокирующих операций с retry логикой"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                return result
            except Exception as e:
                self.logger.warning(f"⚠️ Попытка {attempt + 1}/{max_retries} неудачна: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Экспоненциальная задержка
                else:
                    raise e

    async def get_klines(self, symbol):
        """Получение данных свечей с улучшенной валидацией"""
        try:
            timeframe = os.getenv("TIMEFRAME", "5")
            valid_intervals = {
                '1': '1', '3': '3', '5': '5', '15': '15', '30': '30',
                '60': '60', '120': '120', '240': '240', '360': '360',
                '720': '720', 'D': 'D', 'W': 'W', 'M': 'M'
            }
            interval = valid_intervals.get(timeframe, '5')

            self.logger.debug(f"Запрашиваем данные для {symbol}, интервал: {interval}")

            resp = await self.run_blocking(
                self.session.get_kline,
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=100
            )

            # ИСПРАВЛЕНИЕ: Улучшенная обработка данных
            return self._process_data(resp, symbol)

        except Exception as e:
            self._log_error(f"Kline error for {symbol}: {str(e)}")
            return None

    async def get_wallet_balance(self):
        """Получение баланса кошелька с улучшенной обработкой ошибок"""
        try:
            response = await self.run_blocking(
                self.session.get_wallet_balance,
                accountType="UNIFIED"
            )
            self.logger.debug(f"Raw balance response: {response}")

            if not response or response.get('retCode') != 0:
                self._log_error(f"Bad API response: {response}")
                return 0.0

            if 'result' in response and 'list' in response['result']:
                account_data = response['result']['list'][0]
                if 'totalAvailableBalance' in account_data:
                    balance = float(account_data['totalAvailableBalance'])
                    self.logger.debug(f"✅ Баланс получен: {balance}")
                    return balance

                if 'coin' in account_data:
                    for coin in account_data['coin']:
                        if coin.get('coin') == 'USDT':
                            balance = float(coin.get('equity', 0))
                            self.logger.debug(f"✅ USDT баланс получен: {balance}")
                            return balance
            return 0.0

        except Exception as e:
            self._log_error(f"Balance processing failed: {str(e)}")
            return 0.0

    async def get_last_price(self, symbol):
        """Получение последней цены с валидацией"""
        try:
            response = await self.run_blocking(
                self.session.get_tickers,
                category="linear",
                symbol=symbol
            )

            if not response or response.get('retCode') != 0:
                self.logger.error(f"❌ Ошибка получения цены для {symbol}: {response}")
                return None

            if response and response['result'] and response['result']['list']:
                ticker_data = response['result']['list'][0]
                last_price = float(ticker_data['lastPrice'])
                bid_price = float(ticker_data['bid1Price'])
                ask_price = float(ticker_data['ask1Price'])

                # Проверка разумности цены
                if last_price <= 0 or bid_price <= 0 or ask_price <= 0:
                    self.logger.error(
                        f"❌ Неверные цены для {symbol}: last={last_price}, bid={bid_price}, ask={ask_price}")
                    return None

                # Проверка спреда (не должен быть слишком большим)
                spread_pct = ((ask_price - bid_price) / last_price) * 100
                if spread_pct > 1.0:  # Спред больше 1%
                    self.logger.warning(f"⚠️ Большой спред для {symbol}: {spread_pct:.2f}%")

                result = {
                    'last_price': last_price,
                    'bid': bid_price,
                    'ask': ask_price,
                    'spread_pct': spread_pct
                }

                self.logger.debug(f"📊 Цена для {symbol}: {result}")
                return result

            return None
        except Exception as e:
            self._log_error(f"Price error for {symbol}: {str(e)}")
            return None

    async def place_order(self, params):
        """Размещение ордера с улучшенной валидацией"""
        try:
            # Проверяем обязательные параметры
            required = ['category', 'symbol', 'side', 'orderType', 'qty']
            for param in required:
                if param not in params:
                    raise ValueError(f"Missing required parameter: {param}")

            # Добавляем задержку для предотвращения rate limiting
            await asyncio.sleep(0.5)

            self.logger.info(f"📤 Отправка ордера на Bybit: {params}")
            resp = await self.run_blocking(self.session.place_order, **params)

            # Подробная проверка ответа
            if resp is None:
                self.logger.error("❌ Получен None ответ от API")
                return None

            self.logger.info(f"📥 Полный ответ от Bybit: {resp}")

            ret_code = resp.get('retCode')
            ret_msg = resp.get('retMsg', 'Unknown error')

            if ret_code == 0:
                self.logger.info("✅ Ордер успешно размещён")
            else:
                self.logger.error(f"❌ Ошибка размещения ордера: код {ret_code}, сообщение: {ret_msg}")

            return resp

        except Exception as e:
            self._log_error(f"Order placement failed: {str(e)}")
            return None

    async def get_order_status(self, symbol: str, order_id: str):
        """Улучшенная проверка статуса ордера"""
        try:
            # Сначала пробуем get_order_realtime (для активных ордеров)
            response = await self.run_blocking(
                self.session.get_order_realtime,
                category="linear",
                symbol=symbol,
                orderId=order_id
            )

            self.logger.debug(f"🔍 Real-time статус ордера {order_id}: {response}")

            if response and response.get('retCode') == 0:
                result = response.get("result", {}).get("list", [])
                if result:
                    status = result[0].get("orderStatus")
                    self.logger.info(f"📊 Real-time ордер {order_id}: {status}")
                    return status

            # Если не найден в активных, проверяем историю ордеров
            self.logger.debug(f"🔄 Проверяем историю ордеров для {order_id}")
            history_response = await self.run_blocking(
                self.session.get_order_history,
                category="linear",
                symbol=symbol,
                orderId=order_id
            )

            self.logger.debug(f"📚 История ордера {order_id}: {history_response}")

            if history_response and history_response.get('retCode') == 0:
                history_result = history_response.get("result", {}).get("list", [])
                if history_result:
                    status = history_result[0].get("orderStatus")
                    self.logger.info(f"📊 История ордер {order_id}: {status}")
                    return status

            # Если ордер не найден ни в активных, ни в истории, проверяем позиции
            # Возможно, это маркет-ордер который мгновенно исполнился
            positions = await self.get_positions(symbol)
            if positions and len(positions) > 0:
                for pos in positions:
                    if float(pos.get('size', 0)) > 0:
                        self.logger.info(f"✅ Найдена позиция по {symbol}, ордер вероятно исполнен")
                        return "Filled"

            self.logger.warning(f"⚠️ Ордер {order_id} не найден нигде")
            return "Unknown"

        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статуса ордера: {e}")
            return None

    async def cancel_order(self, symbol: str, order_id: str):
        """Отмена ордера"""
        try:
            response = await self.run_blocking(
                self.session.cancel_order,
                category="linear",
                symbol=symbol,
                orderId=order_id
            )
            self.logger.info(f"🚫 Отмена ордера {order_id}: {response}")
            return response.get('retCode') == 0 if response else False
        except Exception as e:
            self.logger.error(f"❌ Ошибка отмены ордера: {e}")
            return False

    async def get_instruments_info(self, symbol: str):
        """Получение информации о торговом инструменте"""
        try:
            response = await self.run_blocking(
                self.session.get_instruments_info,
                category="linear",
                symbol=symbol
            )

            if response and response.get('retCode') == 0:
                data = response['result']['list'][0]

                # Извлекаем важные параметры для торговли
                lot_filter = data.get('lotSizeFilter', {})
                price_filter = data.get('priceFilter', {})

                info = {
                    'minOrderQty': float(lot_filter.get('minOrderQty', 0.001)),
                    'qtyStep': float(lot_filter.get('qtyStep', 0.001)),
                    'maxOrderQty': float(lot_filter.get('maxOrderQty', 10000)),
                    'minOrderAmt': float(lot_filter.get('minOrderAmt', 1.0)),
                    'tickSize': float(price_filter.get('tickSize', 0.01))
                }

                self.logger.info(f"📊 Symbol info for {symbol}: {info}")
                return info

        except Exception as e:
            self.logger.error(f"Error getting instrument info for {symbol}: {e}")

        # Возвращаем дефолтные значения если не удалось получить
        default_info = {
            'minOrderQty': 0.001,
            'qtyStep': 0.001,
            'maxOrderQty': 10000,
            'minOrderAmt': 1.0,
            'tickSize': 0.01
        }

        self.logger.warning(f"Using default info for {symbol}: {default_info}")
        return default_info

    async def set_leverage(self, symbol: str, leverage: int):
        """Установка кредитного плеча"""
        try:
            response = await self.run_blocking(
                self.session.set_leverage,
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )
            self.logger.info(f"⚙️ Установка плеча {leverage}x для {symbol}: {response}")
            return response.get('retCode') == 0 if response else False
        except Exception as e:
            self.logger.error(f"❌ Ошибка установки плеча: {e}")
            return False

    async def get_positions(self, symbol: str = None):
        """Получение текущих позиций с улучшенной обработкой"""
        try:
            params = {"category": "linear"}
            if symbol:
                params["symbol"] = symbol

            response = await self.run_blocking(
                self.session.get_positions,
                **params
            )

            self.logger.debug(f"📊 Позиции ответ: {response}")

            if response and response.get('retCode') == 0:
                positions = response['result']['list']
                self.logger.debug(f"📍 Найдено позиций: {len(positions)}")

                # Фильтруем только позиции с размером > 0
                active_positions = []
                for pos in positions:
                    size = float(pos.get('size', 0))
                    if size != 0:
                        active_positions.append(pos)
                        self.logger.info(f"📈 Активная позиция: {pos.get('symbol')} размер: {size}")

                return active_positions
            return []
        except Exception as e:
            self._log_error(f"Positions error: {str(e)}")
            return []

    async def check_api_connection(self):
        """Проверка соединения с API"""
        try:
            response = await self.run_blocking(self.session.get_server_time)
            is_connected = response and response.get('retCode') == 0
            self.logger.debug(f"🔗 API соединение: {'✅ OK' if is_connected else '❌ Fail'}")
            return is_connected
        except Exception as e:
            self.logger.error(f"❌ Проверка соединения: {e}")
            return False

    def _process_data(self, resp, symbol):
        """Обработка данных свечей с улучшенной валидацией"""
        try:
            if not resp:
                self.logger.error(f"❌ Пустой ответ для {symbol}")
                return None

            if resp.get('retCode') != 0:
                self.logger.error(f"❌ API ошибка для {symbol}: {resp.get('retMsg')}")
                return None

            if 'result' not in resp:
                self.logger.error(f"❌ Отсутствует 'result' в ответе для {symbol}")
                return None

            if not resp['result'].get('list'):
                self.logger.error(f"❌ Пустой список данных для {symbol}")
                return None

            raw_data = resp['result']['list']
            self.logger.debug(f"✅ Получено {len(raw_data)} свечей для {symbol}")

            # Создаем DataFrame
            df = pd.DataFrame(
                raw_data,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
            )

            # ИСПРАВЛЕНИЕ: Проверяем, что DataFrame не пустой
            if df.empty:
                self.logger.error(f"❌ DataFrame пустой для {symbol}")
                return None

            # Конвертируем в числовые типы
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # ИСПРАВЛЕНИЕ: Проверяем наличие NaN после конвертации
            if df[numeric_cols].isnull().any().any():
                self.logger.error(f"❌ Обнаружены NaN значения в данных для {symbol}")
                # Удаляем строки с NaN
                df = df.dropna(subset=numeric_cols)

            if df.empty:
                self.logger.error(f"❌ DataFrame пустой после очистки NaN для {symbol}")
                return None

            # Конвертируем timestamp
            df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')

            # Сортируем по времени (от старых к новым)
            df = df.sort_values('timestamp')

            # ИСПРАВЛЕНИЕ: Финальная проверка
            if len(df) < 10:
                self.logger.warning(f"⚠️ Слишком мало данных для {symbol}: {len(df)}")

            result_df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()

            # Проверяем целостность данных
            if result_df.isnull().any().any():
                self.logger.error(f"❌ Финальный DataFrame содержит NaN для {symbol}")
                return None

            self.logger.debug(f"✅ Обработано {len(result_df)} свечей для {symbol}")
            return result_df

        except Exception as e:
            self._log_error(f"Data processing error for {symbol}: {str(e)}")
            return None

    def _log_error(self, msg):
        """Централизованное логирование ошибок"""
        print(f"[BybitConnector ERROR] {msg}")
        self.logger.error(msg)