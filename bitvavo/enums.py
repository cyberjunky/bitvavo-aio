""" Enumerations """

import enum


class RestCallType(enum.Enum):
    """ REST CallTypes """
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PUT = "PUT"


class OrderSide(enum.Enum):
    """ Order Side """
    BUY = "BUY"
    SELL = "SELL"


class OrderType(enum.Enum):
    """ Order Types """
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"


class CandelstickInterval(enum.Enum):
    """ CandelStick Intervals """
    I_1MIN = "1m"
    I_3MIN = "3m"
    I_5MIN = "5m"
    I_15MIN = "15m"
    I_30MIN = "30m"
    I_1H = "1h"
    I_2H = "2h"
    I_4H = "4h"
    I_6H = "6h"
    I_8H = "8h"
    I_12H = "12h"
    I_1D = "1d"
    I_3D = "3d"
    I_1W = "1w"
    I_1MONTH = "1M"


class OrderResponseType(enum.Enum):
    """ Order Response Type """
    ACT = "ACK"
    RESULT = "RESULT"
    FULL = "FULL"


class TimeInForce(enum.Enum):
    """ Time Settings """
    GOOD_TILL_CANCELLED = "GTC"
    IMMEDIATE_OR_CANCELLED = "IOC"
    FILL_OR_KILL = "FOK"


class SelfTradePrevention(enum.Enum):
    """ Trade Preventions """
    DECREMENT_AND_CANCEL = "decrementAndCancel"
    CANCEL_OLDEST = "cancelOldest"
    CANCEL_NEWEST = "cancelNewest"
    CANCEL_BOTH = "cancelBoth"
