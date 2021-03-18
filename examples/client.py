import asyncio
import logging
import os
from datetime import datetime

from bitvavo import enums
from bitvavo.BitvavoClient import BitvavoClient
from bitvavo.BitvavoExceptions import BitvavoException
from bitvavo.Pair import Pair

LOG = logging.getLogger("bitvavo")
LOG.setLevel(logging.DEBUG)
LOG.addHandler(logging.StreamHandler())

print(f"Available loggers: {[name for name in logging.root.manager.loggerDict]}\n")


async def run():

    # Retrieve your API and SECRET key from the Bitvavo website, create the keys and store them in APIKEY/SECKEY
    # environment variables
    api_key = os.environ["APIKEY"]
    sec_key = os.environ["SECKEY"]

    client = BitvavoClient(api_key, sec_key)

    # General
    print("\nServer time:")
    await client.get_time()

    print("\nMarkets:")
    await client.get_markets()

    print("\nMarkets ETH-BTC:")
    await client.get_markets(pair=Pair("ETH", "BTC"))

    print("\nAssets:")
    await client.get_assets()

    print("\nAssets BTC:")
    await client.get_assets("BTC")

    # Market data
    print("\nOrder book:")
    await client.get_orderbook(pair=Pair("ETH", "BTC"))

    print("\nOrder book depth 5:")
    await client.get_orderbook(pair=Pair("ETH", "BTC"), limit=5)

    print("\nTrades ETH-BTC")
    await client.get_trades(pair=Pair("ETH", "BTC"))

    print("\nTrades depth 5:")
    await client.get_trades(pair=Pair("ETH", "BTC"), limit=5)

    print("\nCandelsticks:")
    await client.get_candelsticks(pair=Pair("ETH", "BTC"), interval="1m", limit=5)

    print("\nPrice ticker:")
    await client.get_price_ticker()

    print("\nPrice ticker ETH-BTC:")
    await client.get_price_ticker(pair=Pair("ETH", "BTC"))

    print("\nBest order book:")
    await client.get_best_orderbook_ticker()

    print("\nBest order book BTC-EUR:")
    await client.get_best_orderbook_ticker(pair=Pair("ETH", "BTC"))

    print("\n24hour price ticker:")
    await client.get_24h_price_ticker()

    print("\n24hour price ticker ETH-BTC:")
    await client.get_24h_price_ticker(pair=Pair("ETH", "BTC"))

    # Orders
    print("\nCreate order:")
    try:
        await client.create_order(
            pair=Pair("BTC", "EUR"),
            side=enums.OrderSide.BUY,
            type=enums.OrderType.LIMIT,
            amount="1",
            price="1",
        )
    except BitvavoException as e:
        print(e)

    print("\nCancel order:")
    try:
        await client.cancel_order(pair=Pair("ETH", "BTC"), order_id="1")
    except BitvavoException as e:
        print(e)

    print("\nGet order:")
    try:
        await client.get_order(pair=Pair("ETH", "BTC"), order_id=1)
    except BitvavoException as e:
        print(e)

    print("\nGet open orders:")
    await client.get_open_orders()

    print("\nGet open orders ETH-BTC:")
    await client.get_open_orders(pair=Pair("ETH", "BTC"))

    print("\nGet orders ETH-BTC:")
    await client.get_orders(pair=Pair("ETH", "BTC"))

    # Trades
    print("\nGet historical trades ETH-BTC:")
    await client.get_historical_trades(pair=Pair("ETH", "BTC"), limit=5)

    # Account
    print("\nAccount:")
    await client.get_account()

    print("\nBalance:")
    await client.get_balance()

    print("\nDeposit EUR:")
    await client.get_deposit("EUR")

    print("\nDeposit history:")
    await client.get_deposit_history()

    print("\nDeposit history BTC:")
    await client.get_deposit_history("BTC")

    print("\nWithdrawal history:")
    await client.get_withdrawal_history()

    print("\nWithdrawal history BTC:")
    await client.get_withdrawal_history("BTC")

    await client.close()


if __name__ == "__main__":
    asyncio.run(run())
