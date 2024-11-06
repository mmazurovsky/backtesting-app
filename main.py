import os
from datetime import datetime, timezone, timedelta

import backtrader as bt
import pandas as pd
import numpy as np
import ta
from typing import List, Dict

from backtest import run_backtest
from data import OhlcRequest
from repo import MongoConnector


class BuyAndHold(bt.Strategy):
    def __init__(self):
        self.initialized = False  # To track if the initial allocation has been done

    def next(self):
        # Execute only on the first bar
        if not self.initialized:
            # Calculate cash to allocate per asset
            cash_per_asset = self.broker.get_cash() / len(self.datas)

            # Allocate cash to each asset
            for data in self.datas:
                # Calculate size based on cash per asset and current price
                size = cash_per_asset / data.close[0]
                self.buy(data=data, size=size)  # Buy the calculated amount for each asset

            # Mark as initialized to avoid further buying
            self.initialized = True


import backtrader as bt
from datetime import datetime, timedelta


# class RsiStrategy(bt.Strategy):
#     params = (
#         ('rsi_threshold', 70),  # RSI threshold for buy/sell
#         ('rsi_period', 5),  # RSI calculation period in days
#     )
#
#     def __init__(self):
#         self.order = None  # Track pending orders
#
#     def calculate_rsi(self):
#         """
#         Calculate the RSI based on the last 4 days' close prices.
#         """
#         # Get the close prices for the last rsi_period days
#
#         prev_closes = self.getdatabyname("daily_tf").close
#         if len(prev_closes) >= self.params.rsi_period:
#             closes: list = prev_closes.get(size=4)
#             closes.append(self.getdatabyname("minute_tf").close[0])
#             prices = pd.Series(closes)
#             rsi_value = ta.wrapper.RSIIndicator(prices, window=self.params.rsi_period).rsi().values[-1]
#             return rsi_value
#         else:
#             return

# def next(self):
#     # Calculate RSI value
#     rsi_value = self.calculate_rsi()
#
#     # Buy condition: RSI > threshold
#     if not rsi_value is None:
#         if rsi_value > self.params.rsi_threshold and not self.position:
#             size = int(self.broker.getcash() / self.datas[0].close[0])
#             if size > 0:
#                 self.order = self.buy(size=size)
#         # Sell condition: RSI < threshold
#         elif rsi_value < self.params.rsi_threshold and self.position:
#             self.order = self.sell(size=self.position.size)


class RsiStrategy(bt.Strategy):
    params = (
        ('rsi_threshold', 70),
        ('rsi_period', 5),
    )

    def __init__(self):
        self.order = None
        # Access data feeds by name
        self.data_minute = self.getdatabyname("minute_tf")
        self.data_daily = self.getdatabyname("daily_tf")

    def __calculateRSI(self):
        data_minute_close = self.data_minute.close
        data_daily_close = self.data_daily.close

        # Ensure there are enough data points for the RSI calculation
        if len(data_daily_close) >= self.params.rsi_period:
            # Collect the last few closing prices for RSI calculation
            closes = data_daily_close.get(size=self.params.rsi_period)
            closes.append(data_minute_close[0])  # Add the current close of minute data
            prices = pd.Series(closes)

            # Calculate RSI using the `ta` library
            rsi = ta.momentum.RSIIndicator(prices, window=self.params.rsi_period).rsi().iloc[-1]
            return rsi
        return None

    def next(self):
        # Calculate RSI
        rsi_value = self.__calculateRSI()
        if rsi_value is None:
            return

        # Buy condition: RSI > threshold
        if rsi_value > self.params.rsi_threshold and not self.position:
            size = int(self.broker.getcash() / self.data_minute.close[0])
            if size > 0:
                self.order = self.buy(data=self.data_minute, size=size)

        # Sell condition: RSI < threshold
        elif rsi_value < self.params.rsi_threshold and self.position:
            self.order = self.sell(data=self.data_minute, size=self.position.size)


def main():
    # Initialize Cerebro engine
    mongo_connector = MongoConnector()

    # Define the assets and date range
    assets = ["ape"]  # Replace with desired assets
    quote = "usdt"
    interval = "1m"
    market = "spot"
    exchange = "binance"
    start_time = datetime(2024, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

    assetToData: Dict[str, pd.DataFrame] = {}
    for asset in assets:
        ohlc_request = OhlcRequest(
            asset=asset,
            quote=quote,
            interval=interval,
            market=market,
            exchange=exchange,
            start_time=start_time
        )
        # Fetch data from MongoDB and convert to DataFrame
        data_list = mongo_connector.find_all_ohlc_data(ohlc_request)
        data_df = pd.DataFrame([{
            'datetime': data.dateTime,
            'open': data.open,
            'high': data.high,
            'low': data.low,
            'close': data.close,
            'volume': data.volume
        } for data in data_list])

        # 1. Convert 'datetime' column to datetime objects
        data_df['datetime'] = pd.to_datetime(data_df['datetime'], errors='coerce')

        # 2. Check for NaT values and handle them if necessary
        if data_df['datetime'].isna().any():
            print("Found NaT values in 'datetime' column. Inspecting and dropping these rows.")
            # Optionally, drop rows with NaT in 'datetime' column
            data_df = data_df.dropna(subset=['datetime'])

        # 3. Set 'datetime' as the index
        # data_df.set_index('datetime', inplace=True)

        # Ensure data_df is sorted by datetime
        # data_df.sort_index(inplace=True)

        assetToData[asset] = data_df

        # Ensure the directory exists
        output_dir = './files'
        os.makedirs(output_dir, exist_ok=True)
        now = datetime.now()
        data_df.to_csv(os.path.join(output_dir, f'{now}.csv'), sep=" ")

        # Prepare data feed for Cerebro
        run_backtest(asset, data_df, RsiStrategy)
        # run_backtest(asset, data_df, BuyAndHold)


if __name__ == "__main__":
    main()
