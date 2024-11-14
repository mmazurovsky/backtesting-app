import backtrader as bt
import pandas as pd
import ta

from assets import assets_to_trade


class ErstenRsiStrategy(bt.Strategy):
    params = (
        ('rsi_threshold', 70),
        ('rsi_period', 5),
        ('use_stop_loss', True),
        ('stop_loss', 0.015),
        ('trail', True),
    )

    def __init__(self):
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

            rsi = ta.momentum.RSIIndicator(prices, window=self.params.rsi_period).rsi().iloc[-1]

            return rsi
        return None

    def next(self):
        assets_with_positions = self.opened_stop_orders.copy()
        available_cash = self.broker.getcash()


        for asset in assets_with_positions:
            opened_stop_orders_for_asset = self.opened_stop_orders[asset]
            if opened_stop_orders_for_asset is not None and len(opened_stop_orders_for_asset) > 0:
                asset_data = self.getdatabyname(f"{asset}")
                rsi = self.calculateRSI(asset_data)
                if (rsi < self.params.rsi_threshold):
                    position = self.getposition(data=asset_data).size
                    self.sell(data=asset_data, size=position)
                    self.cancel_all_stop_orders(asset)

        for asset in assets_to_trade:
            if (f"{asset}_1d" in assets_with_positions):
                return
            if (available_cash > 10):
                asset_closes = self.getdatabyname(f"{asset}_1d")
                rsi = self.calculateRSI(asset_closes)
                if rsi is not None and rsi > self.params.rsi_threshold:
                    latest_price = asset_closes[0]
                    size = available_cash / latest_price / 3
                    self.buy(data=asset_closes, size=size)

    def notify_order(self, order):
        asset = order.data._name
        # Check if the order is completed (filled)
        if order.status == order.Completed:
            if order.isbuy():
                datetime = self.data.num2date(order.executed.dt)
                print(f'BUY {asset} at price: {order.executed.price:.5f} at {datetime}')
                # Place a stop loss order if it was a buy order
                if self.p.use_stop_loss is True:
                    if not self.p.trail:
                        stop_price = order.executed.price * (1.0 - self.p.stop_loss)
                        new_sl_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=order.size)
                    else:
                        new_sl_order = self.sell(exectype=bt.Order.StopTrail, trailamount=self.p.trail,
                                                 size=order.size)
                    if (new_sl_order is None):
                        print(asset)
                    else:
                        if asset in self.opened_stop_orders:
                            self.opened_stop_orders[asset].append(new_sl_order)
                        else:
                            self.opened_stop_orders[asset] = [new_sl_order]

            elif order.issell():
                datetime = self.data.num2date(order.executed.dt)
                if order.exectype in [bt.Order.Stop, bt.Order.StopTrail, bt.Order.StopTrailLimit, bt.Order.StopLimit]:
                    print(f'Stop-loss SELL {asset} at price: {order.executed.price:.5f} at {datetime}')
                    self.cancel_all_stop_orders(asset)
                else:
                    print(f'SELL {asset} at price: {order.executed.price:.5f} at {datetime}')
                    self.cancel_all_stop_orders(asset)

    def cancel_all_stop_orders(self, asset):
        if asset in self.opened_stop_orders:
            opened_stop_orders_for_asset = self.opened_stop_orders[asset]
            for stop_order in opened_stop_orders_for_asset:
                if stop_order.alive():  # Check if the order is still active
                    self.cancel(stop_order)
            del self.opened_stop_orders[asset]