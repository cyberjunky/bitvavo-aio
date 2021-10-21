# bitvavo-aio


This Python library provides access to [Bitvavo crypto exchange](https://bitvavo.com/en) API. The library is focussed on Bitvavo's REST API only for the moment, as lean and mean as possible, websocket support may follow later.

`bitvavo-aio` is designed as an asynchronous library utilizing modern features of Python using [aiohttp](https://aiohttp.readthedocs.io/en/stable/).

For changes see: [CHANGELOG](https://github.com/cyberjunky/bitvavo-aio/blob/master/CHANGELOG.md).

### Features
 - Access to Bitvavo's REST API like account details, market data and order management
 - Fully asynchronous, designed for good performance

### Installation
```bash
pip3 install bitvavo-aio
```

### Prerequisites
Due to dependencies and Python features used by the library please make sure you use Python version > `3.6`.

Before you can use `bitvavo-aio` you need to define a API key pair inside your account on the website of Bitvavo, and set the needed permissions and specify your whitelist IP address.
Write down the Bitvavo API and SECRET key given to be used in the code.

### Basic Example
```python
#!/usr/bin/env python3
import asyncio
import logging
import os
from datetime import datetime

from bitvavo.BitvavoClient import BitvavoClient
from bitvavo.Pair import Pair
from bitvavo import enums
from bitvavo.BitvavoExceptions import BitvavoException

LOG = logging.getLogger("bitvavo")
LOG.setLevel(logging.DEBUG)
LOG.addHandler(logging.StreamHandler())

print(f"Available loggers: {[name for name in logging.root.manager.loggerDict]}\n")

async def run():

    # Retrieve your API and SECRET key from the Bitvavo website
    # and store them in the following environment variables.
    api_key = os.environ['APIKEY']
    sec_key = os.environ['SECKEY']

    client = BitvavoClient(api_key, sec_key)

    # General
    print("\nServer time:")
    await client.get_time()

    print("\nMarkets:")
    await client.get_markets()

    print("\nMarkets ETH-BTC:")
    await client.get_markets(pair = Pair('ETH', 'BTC'))

    print("\nAssets:")
    await client.get_assets()

    print("\nAssets BTC:")
    await client.get_assets('BTC')

    # Market data
    print("\nOrder book:")
    await client.get_orderbook(pair = Pair('ETH', 'BTC'))

    print("\nCandelsticks:")
    await client.get_candelsticks(pair=Pair('ETH', 'BTC'), interval = '1m', limit = 5)

    print("\nPrice ticker:")
    await client.get_price_ticker()

    print("\nBest order book:")
    await client.get_best_orderbook_ticker()

    print("\n24hour price ticker:")
    await client.get_24h_price_ticker()

    # Orders
    print("\nGet open orders:")
    await client.get_open_orders()

    print("\nGet orders ETH-BTC:")
    await client.get_orders(pair = Pair('ETH', 'BTC'))

    # Trades
    print("\nGet historical trades ETH-BTC:")
    await client.get_historical_trades(pair = Pair('ETH', 'BTC'), limit = 5)

    # Account
    print("\nAccount:")
    await client.get_account()

    print("\nBalance:")
    await client.get_balance()

    print("\nDeposit history:")
    await client.get_deposit_history()

    await client.close()

if __name__ == "__main__":
    asyncio.run(run())
```

A full overview of implemented API calls can be found in: [examples/client.py](https://github.com/cyberjunky/bitvavo-aio/blob/master/examples/client.py)

### Support and Contact

If you like this library and you want to support further development or have a bug to report, please open a Github Issue.
