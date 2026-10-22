# bitvavo-aio

This Python library provides access to the [Bitvavo crypto exchange](https://bitvavo.com/en) REST API. It is focused on Bitvavo's REST API only, as lean and mean as possible.

`bitvavo-aio` is a fully asynchronous library built on [aiohttp](https://docs.aiohttp.org/).

For changes see the [CHANGELOG](https://github.com/cyberjunky/bitvavo-aio/blob/main/CHANGELOG.md).

### Features
 - Access to Bitvavo's REST API: market data, account details, balances, staking, transaction history and order management
 - Fully asynchronous, can share an existing `aiohttp.ClientSession`
 - Request timeouts and typed exceptions (`BitvavoAuthError`, `BitvavoRateLimitError`, `BitvavoConnectionError`)
 - Tracks the remaining rate limit weight (`client.rate_limit_remaining`)

### Installation
```bash
pip3 install bitvavo-aio
```

Python 3.11 or newer is required.

### Prerequisites
Market data (tickers, markets, assets, order books, candles) is public and needs no API key.

For account data and trading, create an API key on the Bitvavo website and set the needed permissions (*View* for read-only use, *Trade* for orders). Optionally restrict the key to your IP address.

### Basic Example
```python
import asyncio
import os

from bitvavo.BitvavoClient import BitvavoClient
from bitvavo.BitvavoExceptions import BitvavoAuthError, BitvavoException


async def run() -> None:
    async with BitvavoClient(os.environ["APIKEY"], os.environ["SECKEY"]) as client:
        print(await client.get_24h_price_ticker("BTC-EUR"))
        print(await client.get_markets("BTC-EUR"))

        try:
            print(await client.get_balance())
            print(await client.get_staking_balance())
            print(await client.get_account_fees(quote="EUR"))
        except BitvavoAuthError as err:
            print(f"Check your API key: {err.error_code} {err.error}")
        except BitvavoException as err:
            print(f"API error: {err}")

        print(f"Rate limit weight left: {client.rate_limit_remaining}")


asyncio.run(run())
```

To reuse an existing session (for example in Home Assistant), pass `session=`; the client will not close it:

```python
client = BitvavoClient(api_key, secret, session=my_session, timeout=10)
```

A full overview of implemented API calls can be found in [examples/client.py](https://github.com/cyberjunky/bitvavo-aio/blob/main/examples/client.py).

### Development
```bash
pdm install --group dev
pdm run ruff check . && pdm run ruff format --check .
pdm run mypy bitvavo
pdm run pytest
```

### Support and Contact

If you like this library and you want to support further development or have a bug to report, please open a GitHub Issue.
