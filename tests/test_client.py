"""Tests for the Bitvavo REST client, run against a local aiohttp server."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from bitvavo.BitvavoClient import BitvavoClient
from bitvavo.BitvavoExceptions import (
    BitvavoAuthError,
    BitvavoConnectionError,
    BitvavoException,
    BitvavoRateLimitError,
)
from bitvavo.enums import CandelstickInterval, OrderSide, OrderType, TimeInForce
from bitvavo.Pair import Pair


@dataclass
class Recorded:
    """A request received by the fake API."""

    method: str
    path_qs: str
    headers: dict[str, str]
    body: bytes


@dataclass
class FakeApi:
    """Fake Bitvavo API: maps path to (status, payload, headers)."""

    routes: dict[str, tuple[int, Any, dict[str, str]]] = field(default_factory=dict)
    requests: list[Recorded] = field(default_factory=list)
    delay: float = 0

    def add(
        self, path: str, payload: Any, status: int = 200, headers: dict[str, str] | None = None
    ) -> None:
        self.routes[path] = (status, payload, headers or {})

    async def handle(self, request: web.Request) -> web.Response:
        self.requests.append(
            Recorded(request.method, request.path_qs, dict(request.headers), await request.read())
        )
        if self.delay:
            await asyncio.sleep(self.delay)
        path = request.path.removeprefix("/v2/")
        status, payload, headers = self.routes.get(path, (404, {"errorCode": 404}, {}))
        return web.json_response(payload, status=status, headers=headers)


@pytest.fixture
async def api() -> AsyncIterator[FakeApi]:
    fake = FakeApi()
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", fake.handle)
    server = TestServer(app)
    await server.start_server()
    fake.base = str(server.make_url("/v2/"))  # type: ignore[attr-defined]
    yield fake
    await server.close()


@pytest.fixture
def make_client(api: FakeApi) -> Callable[..., BitvavoClient]:
    def factory(*args: Any, **kwargs: Any) -> BitvavoClient:
        client = BitvavoClient(*args, **kwargs)
        client.REST_API_URI = api.base  # type: ignore[attr-defined]
        client._get_current_timestamp_ms = lambda: 1000  # type: ignore[method-assign]
        return client

    return factory


def _sign(payload: bytes) -> str:
    return hmac.new(b"secret", payload, hashlib.sha256).hexdigest()


async def test_public_call_and_rate_limit_headers(api: FakeApi, make_client) -> None:
    api.add(
        "ticker/price",
        {"market": "BTC-EUR", "price": "50000"},
        headers={"bitvavo-ratelimit-remaining": "998", "bitvavo-ratelimit-resetat": "1700000"},
    )
    async with make_client() as client:
        result = await client.get_price_ticker(Pair("BTC", "EUR"))
        assert result == {"market": "BTC-EUR", "price": "50000"}
        assert client.rate_limit_remaining == 998
        assert client.rate_limit_reset_at == 1700000
    assert api.requests[0].path_qs == "/v2/ticker/price?market=BTC-EUR"
    assert "Bitvavo-Access-Key" not in api.requests[0].headers


async def test_market_string_accepted(api: FakeApi, make_client) -> None:
    api.add("ticker/24h", {"market": "ETH-EUR"})
    async with make_client() as client:
        assert await client.get_24h_price_ticker("ETH-EUR") == {"market": "ETH-EUR"}
    assert api.requests[0].path_qs == "/v2/ticker/24h?market=ETH-EUR"


async def test_signed_get_signature(api: FakeApi, make_client) -> None:
    api.add("balance", [])
    async with make_client("key", "secret") as client:
        assert await client.get_balance("BTC") == []

    headers = api.requests[0].headers
    assert headers["Bitvavo-Access-Key"] == "key"
    assert headers["Bitvavo-Access-Timestamp"] == "1000"
    assert headers["Bitvavo-Access-Signature"] == _sign(b"1000GET/v2/balance?symbol=BTC")


async def test_order_body_is_signed_and_typed(api: FakeApi, make_client) -> None:
    api.add("order", {"orderId": "1"})
    async with make_client("key", "secret") as client:
        await client.create_order(
            Pair("BTC", "EUR"),
            OrderType.LIMIT,
            OrderSide.BUY,
            amount="1",
            price="2",
            time_in_force=TimeInForce.GOOD_TILL_CANCELLED,
            prevent_limit_immediate_fill=True,
            operator_id=1,
        )

    request = api.requests[0]
    assert json.loads(request.body) == {
        "market": "BTC-EUR",
        "side": "buy",
        "orderType": "limit",
        "amount": "1",
        "price": "2",
        "timeInForce": "GTC",
        "postOnly": True,
        "operatorId": 1,
    }
    assert request.headers["Bitvavo-Access-Signature"] == _sign(b"1000POST/v2/order" + request.body)


async def test_order_type_is_camel_case(api: FakeApi, make_client) -> None:
    api.add("order", {"orderId": "1"})
    async with make_client("key", "secret") as client:
        await client.create_order(
            "BTC-EUR", OrderType.STOP_LOSS_LIMIT, OrderSide.SELL, amount="1", operator_id=1
        )
    assert json.loads(api.requests[0].body)["orderType"] == "stopLossLimit"


async def test_get_orders_without_limit(api: FakeApi, make_client) -> None:
    api.add("orders", [])
    async with make_client("key", "secret") as client:
        assert await client.get_orders("BTC-EUR") == []
    assert api.requests[0].path_qs == "/v2/orders?market=BTC-EUR"


async def test_new_account_endpoints(api: FakeApi, make_client) -> None:
    api.add("account/fees", {"tier": "0", "taker": "0.0025", "maker": "0.0015"})
    api.add("stakingBalance", [{"symbol": "ETH", "amount": "1"}])
    api.add("account/history", {"items": [], "currentPage": 1, "totalPages": 1})
    async with make_client("key", "secret") as client:
        assert (await client.get_account_fees(quote="EUR"))["tier"] == "0"
        assert await client.get_staking_balance() == [{"symbol": "ETH", "amount": "1"}]
        assert (await client.get_account_history(max_items=10))["items"] == []
    assert api.requests[2].path_qs == "/v2/account/history?maxItems=10"


async def test_signed_call_requires_credentials(make_client) -> None:
    async with make_client() as client:
        with pytest.raises(BitvavoException):
            await client.get_balance()


@pytest.mark.parametrize(
    ("status", "body", "exc"),
    [
        (403, {"errorCode": 309, "error": "The signature is invalid."}, BitvavoAuthError),
        (403, {"errorCode": 311, "error": "No view permission."}, BitvavoAuthError),
        (429, {"errorCode": 105, "error": "Rate limit exceeded."}, BitvavoRateLimitError),
        (500, {"errorCode": 101, "error": "Unknown error."}, BitvavoException),
    ],
)
async def test_error_mapping(api: FakeApi, make_client, status, body, exc) -> None:
    api.add("balance", body, status=status)
    async with make_client("key", "secret") as client:
        with pytest.raises(exc) as err:
            await client.get_balance()
    assert type(err.value) is exc
    assert err.value.status_code == status
    assert err.value.error_code == body["errorCode"]
    assert err.value.error == body["error"]


async def test_connection_error() -> None:
    client = BitvavoClient()
    client.REST_API_URI = "http://127.0.0.1:1/v2/"
    async with client:
        with pytest.raises(BitvavoConnectionError):
            await client.get_time()


async def test_timeout(api: FakeApi, make_client) -> None:
    api.add("time", {"time": 1})
    api.delay = 1
    async with make_client(timeout=0.1) as client:
        with pytest.raises(BitvavoConnectionError):
            await client.get_time()


async def test_external_session_is_not_closed(api: FakeApi, make_client) -> None:
    api.add("time", {"time": 1})
    async with aiohttp.ClientSession() as session:
        client = make_client(session=session)
        assert await client.get_time() == {"time": 1}
        await client.close()
        assert not session.closed


def test_pair_helpers() -> None:
    assert Pair.from_market("BTC-EUR") == Pair("BTC", "EUR")
    assert BitvavoClient._map_pair(Pair("BTC", "EUR")) == "BTC-EUR"
    assert BitvavoClient._map_pair(None) is None


async def test_candlestick_interval_enum(api: FakeApi, make_client) -> None:
    api.add("BTC-EUR/candles", [])
    async with make_client() as client:
        await client.get_candlesticks("BTC-EUR", CandelstickInterval.I_1W)
    assert api.requests[0].path_qs == "/v2/BTC-EUR/candles?interval=1W"
