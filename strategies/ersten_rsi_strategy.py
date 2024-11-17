import backtrader as bt

from assets import assets_to_trade
from strategies.functions import calculateRSI, calculateSMA
from strategies.global_functions import notify_order


class ErstenRsiStrategy(bt.Strategy):
    params = (
        ('rsi_threshold', 70),
        ('rsi_period', 3),
        ('use_stop_loss', False),
        ('stop_loss', 0.03),
    )

    def __init__(self):
        self.opened_long_orders: dict = {}
        self.opened_stop_orders: dict = {}

    def next(self):
        assets_with_positions = self.opened_long_orders.copy()
        available_cash = self.broker.getcash()

        for asset in assets_with_positions:
            opened_orders_for_asset = self.opened_long_orders[asset]
            if opened_orders_for_asset is not None:
                asset_data = self.getdatabyname(asset)
                rsi = calculateRSI(asset_data, self.params.rsi_period)
                if (rsi < self.params.rsi_threshold):
                    position = self.getposition(data=asset_data).size
                    self.sell(data=asset_data, size=position)

        for asset in assets_to_trade:
            if (asset in assets_with_positions or len(assets_with_positions.keys()) > 3):
                return
            else:
                asset_ohlcs = self.getdatabyname(asset)
                rsi = calculateRSI(asset_ohlcs, self.params.rsi_period)
                price = asset_ohlcs.close[0]
                sma = calculateSMA(asset_ohlcs, 100)
                if rsi is not None and rsi > self.params.rsi_threshold and sma is not None and price > sma:
                    print(f"{asset} {sma}")
                    size = available_cash
                    self.buy(data=asset_ohlcs, size=size)

    def notify_order(self, order):
        notify_order(self, order)
