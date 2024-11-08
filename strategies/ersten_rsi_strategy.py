import backtrader as bt
import pandas as pd
import ta

from main import assets_to_trade


class ErstenRsiStrategy(bt.Strategy):
    params = (
        ('rsi_threshold', 70),
        ('rsi_period', 5),
        ('use_stop_loss', False),
        ('stop_loss', 0.015),
        ('trail', True),
    )

    def __init__(self):
        self.opened_long_orders: dict = {}
        self.opened_stop_orders: dict = {}

    def calculateRSI(self, data: bt.feeds.PandasData):
        closes = data.close

        # Ensure there are enough data points for the RSI calculation
        if len(closes) >= self.params.rsi_period:
            # Collect the last few closing prices for RSI calculation
            closes = closes.get(size=self.params.rsi_period)
            # closes.append(data_minute_close[0])  # Add the current close of minute data
            prices = pd.Series(closes)

            # Calculate RSI using the `ta` library
            rsi = ta.momentum.RSIIndicator(prices, window=self.params.rsi_period).rsi()

            return rsi.iloc[-1]
        return None

    def next(self):
        available_cash = self.broker.getcash()
        if (available_cash < 10):
            for asset in self.opened_stop_orders:
                opened_orders_for_asset = self.opened_stop_orders[asset]
                if opened_orders_for_asset is not None and opened_orders_for_asset.size > 0:
                    rsi = self.calculateRSI(self.getdatabyname(f"{asset}_1d"))
                    if (rsi < self.params.rsi_threshold):
                        self.sell

        else:

        for asset in assets_to_trade:
            asset_closes = self.getdatabyname(f"{asset}_1d").close

        # Calculate RSI
        rsi_value = self.__calculateRSI()
        if rsi_value is None:
            return

        # Buy condition: RSI > threshold
        if rsi_value > self.params.rsi_threshold and self.position.size == 0:

            latest_price = self.data_minute.close[0]
            size = int(available_cash / latest_price)
            if size > 0:
                self.buy(data=self.data_minute, size=size)

        # Sell condition: RSI < threshold
        elif rsi_value < self.params.rsi_threshold and self.position.size > 0:
            position_size = self.position.size
            self.sell(data=self.data_minute, size=position_size)

    def notify_order(self, order):
        asset = order.data.symbol
        # Check if the order is completed (filled)
        if order.status == order.Completed:
            if order.isbuy():
                print(f'BUY {asset} at price: {order.executed.price:.5f}')
                # Place a stop loss order if it was a buy order
                if self.p.use_stop_loss is True:
                    if not self.p.trail:
                        stop_price = order.executed.price * (1.0 - self.p.stop_loss)
                        new_sl_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=self.position.size)
                    else:
                        new_sl_order = self.sell(exectype=bt.Order.StopTrail, trailamount=self.p.trail,
                                                 size=self.position.size)
                    if asset in self.opened_stop_orders:
                        self.opened_stop_orders[asset].extend(new_sl_order)
                    else:
                        self.opened_stop_orders[asset] = [new_sl_order]

            elif order.issell():
                if order.exectype in [bt.Order.Stop, bt.Order.StopTrail, bt.Order.StopTrailLimit, bt.Order.StopLimit]:
                    print(f'Stop-loss SELL {asset} order executed @price: {order.executed.price:.5f}')
                    self.cancel_all_stop_orders(asset)
                else:
                    print(f'SELL {asset} order executed @price: {order.executed.price:.5f}')
                    self.cancel_all_stop_orders(asset)

    def cancel_all_stop_orders(self, asset):
        if asset in self.opened_stop_orders:
            opened_stop_orders_for_asset = self.opened_stop_orders[asset]
            for stop_order in opened_stop_orders_for_asset:
                if stop_order.alive():  # Check if the order is still active
                    self.cancel(stop_order)
            self.opened_stop_orders[asset] = []
