from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class OhlcEntity:
    _id: Optional[str]
    volume: Optional[float]
    takerBuyBaseAssetVolume: Optional[float]
    numberOfTrades: Optional[int]
    symbol: str
    base: str
    market: str
    exchange: str
    interval: str
    dateTime: datetime
    open: float
    high: float
    low: float
    close: float


class OhlcRequest:
    def __init__(self, asset: str, quote: str, interval: str, market: str, exchange: str,
                 start_time: datetime, end_time: Optional[datetime] = None,):
        self.asset = asset
        self.quote = quote
        self.interval = interval
        self.market = market
        self.exchange = exchange
        self.start_time = start_time
        self.end_time = end_time

    @property
    def ticker(self):
        return f"{self.asset}{self.quote}"
