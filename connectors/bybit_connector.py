#connectors/bybit_connector.py
import os
import logging
from pybit.unified_trading import HTTP
import pandas as pd
from config.paths import LOG_DIR

class BybitConnector:
    def __init__(self):
        self.logger = logging.getLogger('BybitConnector')
        self.session = HTTP(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            testnet=os.getenv("BYBIT_DEMO") == "true"
        )

    def _log_error(self, message):
        self.logger.error(message)

    async def get_klines(self, symbol):
        try:
            timeframe = os.getenv("TIMEFRAME", "5")
            valid_intervals = {
                '1': '1', '3': '3', '5': '5', '15': '15', '30': '30',
                '60': '60', '120': '120', '240': '240', '360': '360',
                '720': '720', 'D': 'D', 'W': 'W', 'M': 'M'
            }

            interval = valid_intervals.get(timeframe, '5')  # По умолчанию 5 минут

            resp = self.session.get_kline(
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
            response = self.session.get_wallet_balance(accountType="UNIFIED")
            self.logger.debug(f"Raw balance response: {response}")

            if not response or response.get('retCode') != 0:
                self._log_error(f"Bad API response: {response}")
                return 0.0

            # Обработка нового формата API v5
            if 'result' in response and 'list' in response['result']:
                account_data = response['result']['list'][0]

                # Способ 1: Получить из totalAvailableBalance
                if 'totalAvailableBalance' in account_data:
                    return float(account_data['totalAvailableBalance'])

                # Способ 2: Получить из монет
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
            response = self.session.get_tickers(
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
            return self.session.place_order(**params)
        except Exception as e:
            self._log_error(f"Order placement failed: {str(e)}")
            return None

    async def check_api_connection(self):
        try:
            response = self.session.get_server_time()
            return response['retCode'] == 0
        except Exception:
            return False

    def _process_data(self, resp):
        try:
            if not resp or 'result' not in resp or not resp['result']['list']:
                return None

            # Bybit возвращает 7 колонок: timestamp,open,high,low,close,volume,turnover
            df = pd.DataFrame(
                resp['result']['list'],
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
            )

            # Конвертируем нужные колонки
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].astype(float)
            df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')

            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            self._log_error(f"Data processing error: {str(e)}")
            return None

