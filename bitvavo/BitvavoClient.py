""" Bitvavo REST API Client code """
import hmac
import hashlib
import logging
import datetime
import json
import ssl
from typing import Optional
import aiohttp

from bitvavo.Pair import Pair
from bitvavo.enums import (
    RestCallType,
    OrderType,
    OrderSide,
    TimeInForce,
    SelfTradePrevention,
)
from bitvavo.Timer import Timer
from bitvavo.BitvavoExceptions import BitvavoException

LOG = logging.getLogger(__name__)


class BitvavoClient:
    """ Client Object """

    REST_API_URI = "https://api.bitvavo.com/v2/"
    VALIDITY_WINDOW_MS = 5000

    def __init__(
        self, api_key: str = None, sec_key: str = None, api_trace_log: bool = False
    ) -> None:
        """ Initialize """

        self.api_key = api_key
        self.sec_key = sec_key

        self.rest_session = None
        self.ssl_context = ssl.create_default_context()

        self.api_trace_log = api_trace_log

    def _get_rest_api_uri(self) -> str:
        """ Return api url """
        return self.REST_API_URI

    def _sign_payload(
        self,
        rest_call_type: RestCallType,
        resource: str,
        data: dict = None,
        params: dict = None,
        headers: dict = None,
    ) -> None:
        """ Create signature payload """
        timestamp = self._get_current_timestamp_ms()

        resource_string = resource

        if params is not None and len(params) > 0:
            params_string = "&".join([f"{key}={val}" for key, val in params.items()])
            if "?" in resource:
                resource_string += "&"
            else:
                resource_string += "?"
            resource_string += params_string

        signature_string = (
            str(timestamp) + rest_call_type.value + "/v2/" + resource_string
        )
        if data is not None:
            signature_string += json.dumps(data, separators=(",", ":"))

        LOG.debug(f"Signature input string: {signature_string}")
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
    def _preprocess_rest_response(status_code: int, body: Optional[dict]) -> None:
        """ Trigger exception if needed """
        if str(status_code)[0] != "2":
            raise BitvavoException(status_code, body)

    async def _create_get(
        self,
        resource: str,
        params: dict = None,
        headers: dict = None,
        signed: bool = False,
    ) -> dict:
        """ Create get request """
        return await self._create_rest_call(
            RestCallType.GET, resource, None, params, headers, signed
        )

    async def _create_post(
        self,
        resource: str,
        data: dict = None,
        params: dict = None,
        headers: dict = None,
        signed: bool = False,
    ) -> dict:
        """ Create post request """
        return await self._create_rest_call(
            RestCallType.POST, resource, data, params, headers, signed
        )

    async def _create_delete(
        self,
        resource: str,
        params: dict = None,
        headers: dict = None,
        signed: bool = False,
    ) -> dict:
        """ Create delete request """
        return await self._create_rest_call(
            RestCallType.DELETE, resource, None, params, headers, signed
        )

    async def _create_put(
        self,
        resource: str,
        params: dict = None,
        headers: dict = None,
        signed: bool = False,
    ) -> dict:
        """ Create put request """
        return await self._create_rest_call(
            RestCallType.PUT, resource, None, params, headers, signed
        )

    async def _create_rest_call(
        self,
        rest_call_type: RestCallType,
        resource: str,
        data: dict = None,
        params: dict = None,
        headers: dict = None,
        signed: bool = False,
        api_variable_path: str = None,
    ) -> dict:
        """ Create rest call """
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

            if rest_call_type == RestCallType.GET:
                rest_call = self._get_rest_session().get(
                    resource_uri,
                    json=data,
                    params=params,
                    headers=headers,
                    ssl=self.ssl_context,
                )
            elif rest_call_type == RestCallType.POST:
                rest_call = self._get_rest_session().post(
                    resource_uri,
                    json=data,
                    params=params,
                    headers=headers,
                    ssl=self.ssl_context,
                )
            elif rest_call_type == RestCallType.DELETE:
                rest_call = self._get_rest_session().delete(
                    resource_uri,
                    json=data,
                    params=params,
                    headers=headers,
                    ssl=self.ssl_context,
                )
            elif rest_call_type == RestCallType.PUT:
                rest_call = self._get_rest_session().put(
                    resource_uri,
                    json=data,
                    params=params,
                    headers=headers,
                    ssl=self.ssl_context,
                )
            else:
                raise Exception(f"Unsupported REST call type {rest_call_type}.")

            LOG.debug(
                f"> rest type [{rest_call_type.name}], "
                "resource [{resource}], params [{params}], headers [{headers}], data [{data}]"
            )
            async with rest_call as response:
                status_code = response.status
                body = await response.text()

                LOG.debug(f"<: status [{status_code}], response [{body}]")

                if len(body) > 0:
                    try:
                        body = json.loads(body)
                    except json.JSONDecodeError:
                        body = {"raw": body}

                self._preprocess_rest_response(status_code, body)

                return body

    def _get_rest_session(self) -> aiohttp.ClientSession:
        """ Get rest session """
        if self.rest_session is not None:
            return self.rest_session

        if self.api_trace_log:
            trace_config = aiohttp.TraceConfig()
            trace_config.on_request_start.append(BitvavoClient._on_request_start)
            trace_config.on_request_end.append(BitvavoClient._on_request_end)
            trace_configs = [trace_config]
        else:
            trace_configs = None

        self.rest_session = aiohttp.ClientSession(trace_configs=trace_configs)

        return self.rest_session

    @staticmethod
    def _clean_request_params(params: dict) -> dict:
        """ Create clean parameters """
        clean_params = {}
        for key, value in params.items():
            if value is not None:
                clean_params[key] = str(value)

        return clean_params

    async def _on_request_start(self, trace_config_ctx, params) -> None:
        """ Log request start """
        LOG.debug(f"> Context: {trace_config_ctx}")
        LOG.debug(f"> Params: {params}")

    async def _on_request_end(self, trace_config_ctx, params) -> None:
        """ Log request end """
        LOG.debug(f"< Context: {trace_config_ctx}")
        LOG.debug(f"< Params: {params}")

    @staticmethod
    def _get_current_timestamp_ms() -> int:
        """ Return timestamp """
        return int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp() * 1000)

    def _get_signature(self, params: dict, data: dict) -> str:
        """ Return signature """
        params_string = ""
        data_string = ""

        if params is not None:
            params_string = "&".join([f"{key}={val}" for key, val in params.items()])

        if data is not None:
            data_string = "&".join(
                ["{}={}".format(param[0], param[1]) for param in data]
            )

        hmacstr = hmac.new(
            self.sec_key.encode("utf-8"),
            (params_string + data_string).encode("utf-8"),
            hashlib.sha256,
        )
        return hmacstr.hexdigest()

    @staticmethod
    def _map_pair(pair: Pair) -> str:
        """ Return pair string """
        return f"{pair.base}-{pair.quote}"

    async def close(self) -> None:
        """ Close session """
        session = self._get_rest_session()
        if session is not None:
            await session.close()

    async def get_time(self) -> dict:
        """ Get time API call """
        return await self._create_get("time")

    async def get_markets(self, pair: Pair = None) -> dict:
        """ Get markets API call """
        params = self._clean_request_params({})

        if pair:
            params["market"] = self._map_pair(pair)

        return await self._create_get("markets", params=params)

    async def get_assets(self, symbol: str = None) -> dict:
        """ Get assets API call """
        params = self._clean_request_params({"symbol": symbol})

        return await self._create_get("assets", params=params)

    async def get_orderbook(self, pair: Optional[Pair], limit: int = None) -> dict:
        """ Get orderbook API call """
        params = self._clean_request_params({})

        if limit:
            params["depth"] = limit

        return await self._create_get(f"{self._map_pair(pair)}/book", params=params)

    async def get_trades(self, pair: Pair, limit: int = None) -> dict:
        """ Get trades API call """
        params = self._clean_request_params({})

        if limit:
            params["limit"] = limit

        return await self._create_get(f"{self._map_pair(pair)}/trades", params=params)

    async def get_price_ticker(self, pair: Optional[Pair] = None) -> dict:
        """ Get price ticker API call """
        params = self._clean_request_params({})

        if pair:
            params["market"] = self._map_pair(pair)

        return await self._create_get("ticker/price", params=params)

    async def get_best_orderbook_ticker(self, pair: Optional[Pair] = None) -> dict:
        """ Get orderbook API call """
        params = self._clean_request_params({})

        if pair:
            params["market"] = self._map_pair(pair)

        return await self._create_get("ticker/book", params=params)

    async def get_24h_price_ticker(self, pair: Optional[Pair] = None) -> dict:
        """ Get 24h ticker API call """
        params = self._clean_request_params({})

        if pair:
            params["market"] = self._map_pair(pair)

        return await self._create_get("ticker/24h", params=params)

    async def get_open_orders(self, pair: Optional[Pair] = None) -> dict:
        """ Get open orders API call """
        params = self._clean_request_params({})

        if pair:
            params["market"] = self._map_pair(pair)

        return await self._create_get("ordersOpen", params=params, signed=True)

    async def get_orders(self, pair: Pair = None) -> dict:
        """ Get orders API call """
        params = self._clean_request_params({"market": self._map_pair(pair)})

        return await self._create_get("orders", params=params, signed=True)

    async def get_historical_trades(self, pair: Pair = None, limit: int = None) -> dict:
        """ Get trades history API call """
        params = self._clean_request_params({"market": self._map_pair(pair)})

        if limit:
            params["limit"] = limit

        return await self._create_get("trades", params=params, signed=True)

    async def get_account(self) -> dict:
        """ Get account API call """
        return await self._create_get("account", signed=True)

    async def get_balance(self, symbol: str = None) -> dict:
        """ Get balance API call """
        params = self._clean_request_params({"symbol": symbol})

        return await self._create_get("balance", params=params, signed=True)

    async def get_deposit(self, symbol: str = None) -> dict:
        """ Get deposito API call """
        params = self._clean_request_params({"symbol": symbol})

        return await self._create_get("deposit", params=params, signed=True)

    async def get_deposit_history(self, symbol: str = None, limit: int = None) -> dict:
        """ Get deposito history API call """
        params = self._clean_request_params({"symbol": symbol})

        if limit:
            params["limit"] = limit

        return await self._create_get("depositHistory", params=params, signed=True)

    async def get_withdrawal_history(
        self, symbol: str = None, limit: int = None
    ) -> dict:
        """ Get withdrawal history API call """
        params = self._clean_request_params({"symbol": symbol})

        if limit:
            params["limit"] = limit

        return await self._create_get("withdrawalHistory", params=params, signed=True)

    async def create_order(
        self,
        pair: Pair,
        type: OrderType,
        side: OrderSide,
        amount: str = None,
        price: str = None,
        amount_quote: str = None,
        time_in_force: TimeInForce = None,
        self_trade_prevention: SelfTradePrevention = None,
        prevent_limit_immediate_fill: bool = None,
        disable_market_protection: bool = None,
        full_response: bool = None,
    ) -> dict:
        """ Get create order API call """
        data = self._clean_request_params(
            {
                "market": self._map_pair(pair),
                "side": side.value,
                "orderType": type.value,
                "amount": amount,
                "price": price,
                "amountQuote": amount_quote,
                "postOnly": prevent_limit_immediate_fill,
                "disableMarketProtection": disable_market_protection,
                "responseRequired": full_response,
            }
        )

        if time_in_force is not None:
            data["timeInForce"] = time_in_force.value

        if time_in_force is not None:
            data["selfTradePrevention"] = self_trade_prevention.value

        return await self._create_post("order", data=data, signed=True)

    async def cancel_order(self, pair: Pair, order_id: str) -> dict:
        """ Get cancel order API call """
        params = self._clean_request_params(
            {"market": self._map_pair(pair), "orderId": order_id}
        )

        return await self._create_delete("order", params=params, signed=True)

    async def cancel_orders(self, pair: Pair) -> dict:
        """ Get cancel orders API call """
        params = self._clean_request_params({"market": self._map_pair(pair)})

        return await self._create_delete("orders", params=params, signed=True)

    async def get_order(self, pair: Pair, order_id: str) -> dict:
        """ Get get order API call """
        params = self._clean_request_params(
            {"market": self._map_pair(pair), "orderId": order_id}
        )

        return await self._create_get("order", params=params, signed=True)

    async def get_candelsticks(
        self, pair: Pair, interval: str = "1m", limit: int = None
    ) -> dict:
        """ Get candelsticks API call """
        params = self._clean_request_params({"interval": interval})

        if limit:
            params["limit"] = limit

        return await self._create_get(f"{self._map_pair(pair)}/candles", params=params)
