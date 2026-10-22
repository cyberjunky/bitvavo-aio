"""Bitvavo REST API Client code."""

from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import logging
from typing import Any
from urllib.parse import urlencode

import aiohttp

from bitvavo.BitvavoExceptions import (
    BitvavoConnectionError,
    BitvavoException,
    exception_for_response,
)
from bitvavo.enums import (
    CandelstickInterval,
    OrderSide,
    OrderType,
    RestCallType,
    SelfTradePrevention,
    TimeInForce,
)
from bitvavo.Pair import Pair
from bitvavo.Timer import Timer

LOG = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


class BitvavoClient:
    """Client Object.

    Pass an existing ``aiohttp.ClientSession`` as ``session`` to share it; the
    client will then never close it. Without one, the client creates its own
    session on first use, which ``close()`` (or ``async with``) cleans up.
    """

    REST_API_URI = "https://api.bitvavo.com/v2/"
    VALIDITY_WINDOW_MS = 10000

    def __init__(
        self,
        api_key: str | None = None,
        sec_key: str | None = None,
        api_trace_log: bool = False,
        *,
        session: aiohttp.ClientSession | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize."""

        self.api_key = api_key
        self.sec_key = sec_key

        self.rest_session: aiohttp.ClientSession | None = session
        self._close_session = session is None
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        self.api_trace_log = api_trace_log

        # Updated from the response headers of every call
        self.rate_limit_remaining: int | None = None
        self.rate_limit_reset_at: int | None = None

    async def __aenter__(self) -> BitvavoClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    def _get_rest_api_uri(self) -> str:
        """Return api url."""
        return self.REST_API_URI

    def _sign_payload(
        self,
        rest_call_type: RestCallType,
        resource: str,
        data: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> None:
        """Create signature payload."""
        if not self.api_key or not self.sec_key:
            raise BitvavoException(None, "API key and secret are required for this call")
        if headers is None:
            raise ValueError("headers must be a dict")

        timestamp = self._get_current_timestamp_ms()

        resource_string = resource

        if params:
            params_string = urlencode(params)
            if "?" in resource:
                resource_string += "&"
            else:
                resource_string += "?"
            resource_string += params_string

        signature_string = str(timestamp) + rest_call_type.value + "/v2/" + resource_string
        if data is not None:
            signature_string += json.dumps(data, separators=(",", ":"))

        LOG.debug("Signature input string: %s", signature_string)
        signature = hmac.new(
            self.sec_key.encode("utf-8"),
            signature_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers["Bitvavo-Access-Key"] = self.api_key
        headers["Bitvavo-Access-Signature"] = signature
        headers["Bitvavo-Access-Timestamp"] = str(timestamp)
        headers["Bitvavo-Access-Window"] = str(self.VALIDITY_WINDOW_MS)

    @staticmethod
    def _preprocess_rest_response(status_code: int, body: Any) -> None:
        """Trigger exception if needed."""
        if str(status_code)[0] != "2":
            raise exception_for_response(status_code, body)

    def _update_rate_limit(self, response_headers: Any) -> None:
        """Store the rate limit state reported by the API."""
        remaining = response_headers.get("bitvavo-ratelimit-remaining")
        reset_at = response_headers.get("bitvavo-ratelimit-resetat")
        if remaining is not None and str(remaining).lstrip("-").isdigit():
            self.rate_limit_remaining = int(remaining)
        if reset_at is not None and str(reset_at).isdigit():
            self.rate_limit_reset_at = int(reset_at)

    async def _create_get(
        self,
        resource: str,
        params: dict | None = None,
        headers: dict | None = None,
        signed: bool = False,
    ) -> Any:
        """Create get request."""
        return await self._create_rest_call(
            RestCallType.GET, resource, None, params, headers, signed
        )

    async def _create_post(
        self,
        resource: str,
        data: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
        signed: bool = False,
    ) -> Any:
        """Create post request."""
        return await self._create_rest_call(
            RestCallType.POST, resource, data, params, headers, signed
        )

    async def _create_delete(
        self,
        resource: str,
        params: dict | None = None,
        headers: dict | None = None,
        signed: bool = False,
    ) -> Any:
        """Create delete request."""
        return await self._create_rest_call(
            RestCallType.DELETE, resource, None, params, headers, signed
        )

    async def _create_put(
        self,
        resource: str,
        data: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
        signed: bool = False,
    ) -> Any:
        """Create put request."""
        return await self._create_rest_call(
            RestCallType.PUT, resource, data, params, headers, signed
        )

    async def _create_rest_call(
        self,
        rest_call_type: RestCallType,
        resource: str,
        data: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
        signed: bool = False,
        api_variable_path: str | None = None,
    ) -> Any:
        """Create rest call."""
        with Timer("RestCall"):
            # ensure headers is always a valid object
            if headers is None:
                headers = {}

            # add signature into the parameters
            if signed:
                self._sign_payload(rest_call_type, resource, data, params, headers)

            resource_uri = self._get_rest_api_uri()
            if api_variable_path is not None:
                resource_uri += api_variable_path
            resource_uri += resource
            # Encode the query ourselves so it is byte-identical to what was signed
            if params:
                resource_uri += ("&" if "?" in resource else "?") + urlencode(params)

            LOG.debug(
                "> rest type [%s], resource [%s], params [%s], data [%s]",
                rest_call_type.name,
                resource,
                params,
                data,
            )

            # Serialise the body ourselves so it is byte-identical to what was signed
            body_bytes = (
                json.dumps(data, separators=(",", ":")).encode("utf-8")
                if data is not None
                else None
            )
            if body_bytes is not None:
                headers["Content-Type"] = "application/json"

            try:
                async with self._get_rest_session().request(
                    rest_call_type.value,
                    resource_uri,
                    data=body_bytes,
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    status_code = response.status
                    self._update_rate_limit(response.headers)
                    text = await response.text()
            except TimeoutError as error:
                raise BitvavoConnectionError(f"Timeout calling {resource}") from error
            except aiohttp.ClientError as error:
                raise BitvavoConnectionError(f"Error calling {resource}: {error}") from error

            LOG.debug("<: status [%s], response [%s]", status_code, text)

            body: Any = text
            if len(text) > 0:
                try:
                    body = json.loads(text)
                except json.JSONDecodeError:
                    body = {"raw": text}

            self._preprocess_rest_response(status_code, body)

            return body

    def _get_rest_session(self) -> aiohttp.ClientSession:
        """Get rest session."""
        if self.rest_session is not None and not self.rest_session.closed:
            return self.rest_session

        if self.api_trace_log:
            trace_config = aiohttp.TraceConfig()
            trace_config.on_request_start.append(BitvavoClient._on_request_start)
            trace_config.on_request_end.append(BitvavoClient._on_request_end)
            trace_configs = [trace_config]
        else:
            trace_configs = None

        self.rest_session = aiohttp.ClientSession(trace_configs=trace_configs)
        self._close_session = True

        return self.rest_session

    @staticmethod
    def _clean_request_params(params: dict) -> dict:
        """Create clean query parameters (drop ``None``, stringify the rest)."""
        return {key: str(value) for key, value in params.items() if value is not None}

    @staticmethod
    def _clean_request_body(data: dict) -> dict:
        """Create clean body (drop ``None``, keep JSON types)."""
        return {key: value for key, value in data.items() if value is not None}

    @staticmethod
    async def _on_request_start(
        session: aiohttp.ClientSession, trace_config_ctx: Any, params: Any
    ) -> None:
        """Log request start."""
        LOG.debug("> Context: %s", trace_config_ctx)
        LOG.debug("> Params: %s %s", params.method, params.url)

    @staticmethod
    async def _on_request_end(
        session: aiohttp.ClientSession, trace_config_ctx: Any, params: Any
    ) -> None:
        """Log request end."""
        LOG.debug("< Context: %s", trace_config_ctx)
        LOG.debug("< Params: %s %s %s", params.method, params.url, params.response.status)

    @staticmethod
    def _get_current_timestamp_ms() -> int:
        """Return timestamp."""
        return int(datetime.datetime.now(tz=datetime.UTC).timestamp() * 1000)

    @staticmethod
    def _map_pair(pair: Pair | str | None) -> str | None:
        """Return pair string (``BTC-EUR``); market strings are passed through."""
        if pair is None:
            return None
        if isinstance(pair, str):
            return pair
        return f"{pair.base}-{pair.quote}"

    @staticmethod
    def _map_order_type(order_type: OrderType) -> str:
        """Return Bitvavo order type (``STOP_LOSS_LIMIT`` -> ``stopLossLimit``)."""
        first, *rest = order_type.value.lower().split("_")
        return first + "".join(part.capitalize() for part in rest)

    async def close(self) -> None:
        """Close session (only if it was created by this client)."""
        if self.rest_session is not None and self._close_session:
            await self.rest_session.close()
        self.rest_session = None

    # General

    async def get_time(self) -> Any:
        """Get time API call."""
        return await self._create_get("time")

    async def get_markets(self, pair: Pair | str | None = None) -> Any:
        """Get markets API call."""
        params = self._clean_request_params({"market": self._map_pair(pair)})

        return await self._create_get("markets", params=params)

    async def get_assets(self, symbol: str | None = None) -> Any:
        """Get assets API call."""
        params = self._clean_request_params({"symbol": symbol})

        return await self._create_get("assets", params=params)

    # Market data

    async def get_orderbook(self, pair: Pair | str, limit: int | None = None) -> Any:
        """Get orderbook API call."""
        params = self._clean_request_params({"depth": limit})

        return await self._create_get(f"{self._map_pair(pair)}/book", params=params)

    async def get_trades(self, pair: Pair | str, limit: int | None = None) -> Any:
        """Get trades API call."""
        params = self._clean_request_params({"limit": limit})

        return await self._create_get(f"{self._map_pair(pair)}/trades", params=params)

    async def get_candlesticks(
        self,
        pair: Pair | str,
        interval: CandelstickInterval | str = "1m",
        limit: int | None = None,
        start: int | None = None,
        end: int | None = None,
    ) -> Any:
        """Get candlesticks API call."""
        if isinstance(interval, CandelstickInterval):
            interval = interval.value
        params = self._clean_request_params(
            {"interval": interval, "limit": limit, "start": start, "end": end}
        )

        return await self._create_get(f"{self._map_pair(pair)}/candles", params=params)

    async def get_candelsticks(
        self, pair: Pair | str, interval: CandelstickInterval | str = "1m", limit: int | None = None
    ) -> Any:
        """Get candlesticks API call (kept for backwards compatibility)."""
        return await self.get_candlesticks(pair, interval, limit)

    async def get_price_ticker(self, pair: Pair | str | None = None) -> Any:
        """Get price ticker API call."""
        params = self._clean_request_params({"market": self._map_pair(pair)})

        return await self._create_get("ticker/price", params=params)

    async def get_best_orderbook_ticker(self, pair: Pair | str | None = None) -> Any:
        """Get best bid/ask ticker API call."""
        params = self._clean_request_params({"market": self._map_pair(pair)})

        return await self._create_get("ticker/book", params=params)

    async def get_24h_price_ticker(self, pair: Pair | str | None = None) -> Any:
        """Get 24h ticker API call."""
        params = self._clean_request_params({"market": self._map_pair(pair)})

        return await self._create_get("ticker/24h", params=params)

    # Orders

    async def get_open_orders(self, pair: Pair | str | None = None) -> Any:
        """Get open orders API call."""
        params = self._clean_request_params({"market": self._map_pair(pair)})

        return await self._create_get("ordersOpen", params=params, signed=True)

    async def get_orders(self, pair: Pair | str, limit: int | None = None) -> Any:
        """Get orders API call."""
        params = self._clean_request_params({"market": self._map_pair(pair), "limit": limit})

        return await self._create_get("orders", params=params, signed=True)

    async def get_order(self, pair: Pair | str, order_id: str) -> Any:
        """Get order API call."""
        params = self._clean_request_params({"market": self._map_pair(pair), "orderId": order_id})

        return await self._create_get("order", params=params, signed=True)

    async def create_order(
        self,
        pair: Pair | str,
        type: OrderType,
        side: OrderSide,
        amount: str | None = None,
        price: str | None = None,
        amount_quote: str | None = None,
        time_in_force: TimeInForce | None = None,
        self_trade_prevention: SelfTradePrevention | None = None,
        prevent_limit_immediate_fill: bool | None = None,
        disable_market_protection: bool | None = None,
        full_response: bool | None = None,
        operator_id: int | None = None,
    ) -> Any:
        """Create order API call."""
        data = self._clean_request_body(
            {
                "market": self._map_pair(pair),
                "side": side.value.lower(),
                "orderType": self._map_order_type(type),
                "amount": amount,
                "price": price,
                "amountQuote": amount_quote,
                "timeInForce": time_in_force.value if time_in_force else None,
                "selfTradePrevention": (
                    self_trade_prevention.value if self_trade_prevention else None
                ),
                "postOnly": prevent_limit_immediate_fill,
                "disableMarketProtection": disable_market_protection,
                "responseRequired": full_response,
                "operatorId": operator_id,
            }
        )

        return await self._create_post("order", data=data, signed=True)

    async def cancel_order(
        self, pair: Pair | str, order_id: str, operator_id: int | None = None
    ) -> Any:
        """Cancel order API call."""
        params = self._clean_request_params(
            {"market": self._map_pair(pair), "orderId": order_id, "operatorId": operator_id}
        )

        return await self._create_delete("order", params=params, signed=True)

    async def cancel_orders(
        self, pair: Pair | str | None = None, operator_id: int | None = None
    ) -> Any:
        """Cancel orders API call."""
        params = self._clean_request_params(
            {"market": self._map_pair(pair), "operatorId": operator_id}
        )

        return await self._create_delete("orders", params=params, signed=True)

    # Trades

    async def get_historical_trades(self, pair: Pair | str, limit: int | None = None) -> Any:
        """Get trades history API call."""
        params = self._clean_request_params({"market": self._map_pair(pair), "limit": limit})

        return await self._create_get("trades", params=params, signed=True)

    # Account

    async def get_account(self) -> Any:
        """Get account API call."""
        return await self._create_get("account", signed=True)

    async def get_account_fees(
        self, pair: Pair | str | None = None, quote: str | None = None
    ) -> Any:
        """Get account fee tier and 30 day volume API call."""
        params = self._clean_request_params({"market": self._map_pair(pair), "quote": quote})

        return await self._create_get("account/fees", params=params, signed=True)

    async def get_account_history(
        self,
        from_date: int | None = None,
        to_date: int | None = None,
        page: int | None = None,
        max_items: int | None = None,
        type: str | None = None,
    ) -> Any:
        """Get transaction history API call (paginated, dates in ms)."""
        params = self._clean_request_params(
            {
                "fromDate": from_date,
                "toDate": to_date,
                "page": page,
                "maxItems": max_items,
                "type": type,
            }
        )

        return await self._create_get("account/history", params=params, signed=True)

    async def get_staking_balance(self, symbol: str | None = None) -> Any:
        """Get fixed staking balance API call."""
        params = self._clean_request_params({"symbol": symbol})

        return await self._create_get("stakingBalance", params=params, signed=True)

    async def get_balance(self, symbol: str | None = None) -> Any:
        """Get balance API call."""
        params = self._clean_request_params({"symbol": symbol})

        return await self._create_get("balance", params=params, signed=True)

    async def get_deposit(self, symbol: str | None = None) -> Any:
        """Get deposit data API call."""
        params = self._clean_request_params({"symbol": symbol})

        return await self._create_get("deposit", params=params, signed=True)

    async def get_deposit_history(self, symbol: str | None = None, limit: int | None = None) -> Any:
        """Get deposit history API call."""
        params = self._clean_request_params({"symbol": symbol, "limit": limit})

        return await self._create_get("depositHistory", params=params, signed=True)

    async def get_withdrawal_history(
        self, symbol: str | None = None, limit: int | None = None
    ) -> Any:
        """Get withdrawal history API call."""
        params = self._clean_request_params({"symbol": symbol, "limit": limit})

        return await self._create_get("withdrawalHistory", params=params, signed=True)
