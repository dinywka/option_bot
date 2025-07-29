#connectors/bybit_connector.py

import os
import logging
import asyncio
import pandas as pd
from pybit.unified_trading import HTTP
from config.paths import LOG_DIR


class BybitConnector:
    def __init__(self):
        self.logger = logging.getLogger('BybitConnector')
        self.session = HTTP(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            testnet=os.getenv("BYBIT_DEMO") == "true"
        )

    async def run_blocking(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def get_klines(self, symbol):
        try:
            timeframe = os.getenv("TIMEFRAME", "5")
            valid_intervals = {
                '1': '1', '3': '3', '5': '5', '15': '15', '30': '30',
                '60': '60', '120': '120', '240': '240', '360': '360',
                '720': '720', 'D': 'D', 'W': 'W', 'M': 'M'
            }
            interval = valid_intervals.get(timeframe, '5')

            resp = await self.run_blocking(
                self.session.get_kline,
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=100
            )
            return self._process_data(resp)
        except Exception as e:
            self._log_error(f"Kline error: {str(e)}")
            return None

    async def get_wallet_balance(self):
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
                    return float(account_data['totalAvailableBalance'])
                if 'coin' in account_data:
                    for coin in account_data['coin']:
                        if coin.get('coin') == 'USDT':
                            return float(coin.get('equity', 0))
            return 0.0

        except Exception as e:
            self._log_error(f"Balance processing failed: {str(e)}")
            return 0.0

    async def get_last_price(self, symbol):
        try:
            response = await self.run_blocking(
                self.session.get_tickers,
                category="linear",
                symbol=symbol
            )
            if response and response['result'] and response['result']['list']:
                return {
                    'last_price': float(response['result']['list'][0]['lastPrice']),
                    'bid': float(response['result']['list'][0]['bid1Price']),
                    'ask': float(response['result']['list'][0]['ask1Price'])
                }
            return None
        except Exception as e:
            self._log_error(f"Price error: {str(e)}")
            return None

    async def place_order(self, params):
        try:
            self.logger.info(f"📤 Отправка ордера на Bybit: {params}")
            resp = await self.run_blocking(self.session.place_order, **params)
            self.logger.info(f"📥 Ответ от Bybit: {resp}")
            return resp
        except Exception as e:
            self._log_error(f"Order placement failed: {str(e)}")
            return None

    def get_order_status(self, symbol: str, order_id: str):
        try:
            response = self.session.get_order_realtime(
                category="linear",
                symbol=symbol,
                orderId=order_id
            )
            self.logger.info(f"🔍 Статус ордера {order_id}: {response}")
            result = response.get("result", {}).get("list", [])
            if result:
                return result[0].get("orderStatus")  # 'Filled', 'Cancelled', 'Created'
            else:
                return None
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статуса ордера: {e}")
            return None

    async def check_api_connection(self):
        try:
            response = await self.run_blocking(self.session.get_server_time)
            return response['retCode'] == 0
        except Exception:
            return False

    def _process_data(self, resp):
        try:
            if not resp or 'result' not in resp or not resp['result']['list']:
                return None

            df = pd.DataFrame(
                resp['result']['list'],
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
            )

            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].astype(float)
            df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')

            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            self._log_error(f"Data processing error: {str(e)}")
            return None

    def _log_error(self, msg):
        print(f"[BybitConnector ERROR] {msg}")
        self.logger.error(msg)
