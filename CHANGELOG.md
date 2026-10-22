# Changelog

## 1.0.0 - 2021-03-16

Initial release

## 1.0.1 - 2021-03-16

Return response.txt on calls instead of array
Fill Exception with status code and text

## 1.0.2 - 2021-03-17

Syntax errrors fixed

## 1.0.3 - 2021-05-15

Added license tag
Don't pin aiohttp version

## 1.1.0 - 2026-10-22

Backwards compatible modernisation, checked against the current Bitvavo API docs.

Added:
- `session=` argument to share an `aiohttp.ClientSession` (not closed by the client) and `timeout=` (default 30s)
- Async context manager support (`async with BitvavoClient(...)`)
- Typed exceptions: `BitvavoAuthError` (HTTP 403 / errorCodes 300-322), `BitvavoRateLimitError` (429 / 105), `BitvavoConnectionError` (network errors and timeouts); all subclass `BitvavoException`, which now exposes `error_code` and `error`
- Rate limit tracking via `rate_limit_remaining` and `rate_limit_reset_at`
- New endpoints: `get_account_fees`, `get_staking_balance`, `get_account_history`
- `get_candlesticks` (with `start`/`end`); `get_candelsticks` is kept as an alias
- `operator_id` for `create_order`, `cancel_order` and `cancel_orders` (now required by Bitvavo)
- Markets can be passed as `Pair` or as a string such as `"BTC-EUR"`; `Pair.from_market()`
- Type hints and `py.typed`, tests, CI, dependabot

Fixed:
- Creating the client no longer does blocking SSL setup, so it is safe in an event loop
- `create_order` sent upper case side/type, booleans as strings, and crashed when only `time_in_force` was given
- `get_orders` and `get_historical_trades` crashed when no pair was given
- Query strings are now signed exactly as sent
- API keys are no longer written to the debug log
- Default access window raised to 10s (Bitvavo default) to tolerate clock skew
- Stop loss / take profit order types are sent as `stopLoss`, `stopLossLimit`, etc.
- `get_candlesticks` accepts `CandelstickInterval` values; `I_1W` is now `1W`

Removed (never supported by Bitvavo):
- `OrderType.LIMIT_MAKER`, `CandelstickInterval.I_3MIN` / `I_3D`, `OrderResponseType` (use `full_response`)

Changed:
- Packaging moved to `pyproject.toml`; requires Python 3.11+ and aiohttp 3.9+
