import asyncio
import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()


async def check_balance():
    session = HTTP(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        testnet=True
    )

    try:
        response = session.get_wallet_balance(accountType="UNIFIED")
        print("Full balance response:", response)

        if 'result' in response and 'list' in response['result']:
            print("Available balance:", response['result']['list'][0]['totalAvailableBalance'])
    except Exception as e:
        print("Error:", e)


asyncio.run(check_balance())