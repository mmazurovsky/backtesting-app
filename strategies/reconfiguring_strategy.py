import backtrader as bt

from assets import assets_to_trade
from strategies.functions import calculateRSI, calculateSMA
from strategies.global_functions import notify_order


class ReconfiguringStrategy(bt.Strategy):
    params = (
        ('use_stop_loss', True),
        ('stop_loss', 0.02),
    )

    def __init__(self):
        self.opened_stop_orders: dict = {}

    def next(self):
        assets_with_positions = self.opened_stop_orders.copy()
        available_cash = self.broker.getcash()

        delta_to_asset: dict = {}
        asset_to_delta: dict = {}

        # Calculate deltas for all assets and build mappings
        for asset in assets_to_trade:
            asset_close_last = self.getdatabyname(asset).close[0]
            asset_close_previous = self.getdatabyname(asset).close[-1]  # Use [-1] for the previous close
            if asset_close_previous is not None and asset_close_previous != 0:
                delta = (asset_close_last - asset_close_previous) / asset_close_previous
                delta_to_asset[delta] = asset
                asset_to_delta[asset] = delta

        # Sort deltas from highest to lowest
        sorted_deltas = sorted(delta_to_asset.keys(), reverse=True)
        sorted_assets = [delta_to_asset[delta] for delta in sorted_deltas]

        # Get the top performing assets
        top_assets = set(sorted_assets[:3])

        # First loop: Sell assets that are not among the top performers
        for asset in list(assets_with_positions.keys()):
            asset_data = self.getdatabyname(asset)
            asset_delta = asset_to_delta.get(asset, None)
            if asset_delta < -0.02:
                position = self.getposition(data=asset_data).size
                if position > 0:
                    self.sell(data=asset_data, size=position)

        # Second loop: Buy top-performing assets if not already in a position
        if (len(assets_with_positions.keys()) < 3):
            for asset in assets_to_trade:
                if asset in assets_with_positions:
                    continue  # Skip assets we already have positions in
                if available_cash > 10:
                    asset_ohlcs = self.getdatabyname(asset)
                    asset_delta = asset_to_delta.get(asset, None)

                    # If asset is in the top 2 and has a positive delta
                    if asset in top_assets and asset_delta is not None and asset_delta > 0:
                        latest_price = asset_ohlcs.close[0]
                        size = (available_cash / latest_price) / 3
                        self.buy(data=asset_ohlcs, size=size)

    def notify_order(self, order):
        notify_order(self, order)


