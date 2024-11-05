import os
from datetime import datetime, timezone

import backtrader as bt
import pandas as pd
import numpy as np
import ta
from typing import List, Dict

import calculations
from backtest import run_backtest
from data import OhlcRequest
from repo import MongoConnector


# class RSIOverboughtStrategy(bt.Strategy):
#
#     def __init__(self):
#         self.rsi_period: int = 5
#         self.rsi_threshold: int = 70
#
#     def next(self):
#         if self.position:
#             asset_with_position = self.position.data
#
#             if data.rsi[0] < self.params.rsi_threshold:
#                 # Sell all holdings
#                 self.sell(size=self.position.size)
#         else:
#             for data in self.datas:
#                 if data.rsi[0] > self.params.rsi_threshold:
#                     # Buy with all available balance
#                     size = self.broker.get_cash() / data.close[0]
#                     self.buy(size=size, data=data)


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



class RsiStrategy(bt.Strategy):
    params = (
        ('rsi_threshold', 70),  # RSI threshold for buy/sell
        ('rsi_period', 5),     # RSI calculation period
    )

    def __init__(self):
        self.order = None  # Track pending orders

    def calculate_rsi_n_days(self, data, n: int):
        """
        Calculate the RSI based on the latest close and the last N days' open prices.
        """
        # Create a DataFrame from the data feed
        data_length = len(data)
        df = pd.DataFrame(
            {
                'datetime': [data.num2date(i) for i in range(-data_length + 1, 1)],
                'close': [data.close[i] for i in range(-data_length + 1, 1)],
                'open': [data.open[i] for i in range(-data_length + 1, 1)],
            }
        )
        df.set_index('datetime', inplace=True)

        # Resample to get the opening price at 00:00 for each day
        daily_opens = df['open'].resample('D').first().dropna()

        # Ensure there are enough days to calculate RSI
        if len(daily_opens) < n - 1:
            return np.nan  # Not enough data to calculate RSI

        # Combine the last N-1 days' opens with the latest close price
        relevant_prices = pd.concat(
            [daily_opens.tail(n - 1), pd.Series(df['close'].iloc[-1], index=[df.index[-1]])]
        )

        # Calculate RSI using the ta library
        rsi_series = ta.wrapper.RSIIndicator(relevant_prices, window=n).rsi()
        return rsi_series.iloc[-1]

    def next(self):
        # Calculate RSI value
        rsi_value = self.calculate_rsi_n_days(self.data, self.params.rsi_period)

        # Check if RSI value is valid
        if np.isnan(rsi_value):
            return  # Not enough data to proceed

        # Buy condition: RSI > threshold
        if rsi_value > self.params.rsi_threshold and not self.position:
            size = int(self.broker.getcash() / self.data.close[0])
            if size > 0:
                self.order = self.buy(size=size)

        # Sell condition: RSI < threshold
        elif rsi_value < self.params.rsi_threshold and self.position:
            self.order = self.sell(size=self.position.size)





def main():
    # Initialize Cerebro engine
    mongo_connector = MongoConnector()

    # Define the assets and date range
    assets = ["ape"]  # Replace with desired assets
    quote = "usdt"
    interval = "1m"
    market = "spot"
    exchange = "binance"
    start_time = datetime(2024, 9, 1, 0, 0, 0, tzinfo=timezone.utc)


    assetToData: Dict[str, bt.feeds.PandasData] = {}
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
        data_df.set_index('datetime', inplace=True)

        # Ensure data_df is sorted by datetime
        data_df.sort_index(inplace=True)

        data_feed = bt.feeds.PandasData(dataname=data_df)

        assetToData[asset] = data_feed

        # Ensure the directory exists
        output_dir = './files'
        os.makedirs(output_dir, exist_ok=True)

        now = datetime.now()

        # Save the DataFrame to CSV
        data_df.to_csv(os.path.join(output_dir, f'{now}.csv'), sep=" ")
        # Prepare data feed for Cerebro



    run_backtest(assetToData, RsiStrategy)
    run_backtest(assetToData, BuyAndHold)




if __name__ == "__main__":
    main()
