import os
from datetime import datetime, timezone

import backtrader as bt
import pandas as pd
import numpy as np
from pandas.core.interchange.dataframe_protocol import DataFrame

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


def rsi_tradingview(close_prices, period=14, round_rsi=True):
    """
    Implements the RSI indicator as defined by TradingView.

    :param close_prices: List or array of close prices
    :param period: RSI period (default is 14)
    :param round_rsi: Boolean flag to indicate whether to round the RSI value
    :return: RSI value (float)
    """
    # Ensure close_prices is a Pandas Series
    if not isinstance(close_prices, pd.Series):
        close_prices = pd.Series(close_prices)

    # Calculate price changes (delta)
    delta = close_prices.diff()

    # Separate gains and losses
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)

    # Calculate Exponential Moving Averages (RMA)
    alpha = 1 / period
    up_ewm = up.ewm(alpha=alpha, adjust=False).mean()
    down_ewm = down.ewm(alpha=alpha, adjust=False).mean()

    # Compute RSI according to TradingView's formula
    rs = up_ewm / down_ewm
    rsi = np.where(
        down_ewm == 0,
        100,
        np.where(
            up_ewm == 0,
            0,
            100 - (100 / (1 + rs))
        )
    )

    # Get the last RSI value using indexing
    rsi_value = rsi[-1]

    # Round the RSI value if requested
    if round_rsi:
        rsi_value = round(rsi_value, 2)

    return rsi_value


def main():
    # Initialize Cerebro engine
    mongo_connector = MongoConnector()
    cerebro = bt.Cerebro()

    # Define the assets and date range
    assets = ["btc"]  # Replace with desired assets
    quote = "usdt"
    interval = "1m"
    market = "spot"
    exchange = "binance"
    start_time = datetime(2024, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

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

        # 4. Confirm the index type
        print("Index type:", type(data_df.index))

        # Ensure data_df is sorted by datetime
        data_df.sort_index(inplace=True)

        # Create 'date' column
        data_df['date'] = data_df.index.date

        # Compute daily close prices
        daily_close_prices = data_df.groupby('date')['close'].last()
        daily_close_prices = daily_close_prices.to_frame()

        # Shift daily close prices to get previous days' close prices
        daily_close_prices['close_D1'] = daily_close_prices['close'].shift(1)
        daily_close_prices['close_D2'] = daily_close_prices['close'].shift(2)
        daily_close_prices['close_D3'] = daily_close_prices['close'].shift(3)
        daily_close_prices['close_D4'] = daily_close_prices['close'].shift(4)

        # Merge shifted close prices into data_df
        data_df = data_df.merge(
            daily_close_prices[['close_D1', 'close_D2', 'close_D3', 'close_D4']],
            how='left',
            left_on='date',
            right_index=True
        )

        # Define the rsi_tradingview function
        def rsi_tradingview(ohlc, period, round_rsi: bool = True):
            """ Implements the RSI indicator as defined by TradingView on March 15, 2021.
                The TradingView code is as follows:
                //@version=4
                study(title="Relative Strength Index", shorttitle="RSI", format=format.price, precision=2, resolution="")
                len = input(14, minval=1, title="Length")
                src = input(close, "Source", type = input.source)
                up = rma(max(change(src), 0), len)
                down = rma(-min(change(src), 0), len)
                rsi = down == 0 ? 100 : up == 0 ? 0 : 100 - (100 / (1 + up / down))
                plot(rsi, "RSI", color=#8E1599)
                band1 = hline(70, "Upper Band", color=#C0C0C0)
                band0 = hline(30, "Lower Band", color=#C0C0C0)
                fill(band1, band0, color=#9915FF, transp=90, title="Background")

            :param ohlc:
            :param period:
            :param round_rsi:
            :return: an array with the RSI indicator values
            """

            delta = ohlc.diff()

            up = delta.copy()
            up[up < 0] = 0
            up = pd.Series.ewm(up, alpha=1 / period).mean()

            down = delta.copy()
            down[down > 0] = 0
            down *= -1
            down = pd.Series.ewm(down, alpha=1 / period).mean()

            rsi = np.where(up == 0, 0, np.where(down == 0, 100, 100 - (100 / (1 + up / down))))

            rsis = np.round(rsi, 2) if round_rsi else rsi
            result = rsis[-1]
            return result

        # Compute RSI for each row
        def compute_rsi(row):
            close_prices = [
                row['close_D4'],
                row['close_D3'],
                row['close_D2'],
                row['close_D1'],
                row['close']
            ]

            if any(pd.isnull(close_prices)):
                return np.nan
            else:
                close_prices = pd.Series(close_prices)
                rsi_value = rsi_tradingview(close_prices, period=5)
                return rsi_value

        data_df['rsi'] = data_df.apply(compute_rsi, axis=1)

        # Ensure the directory exists
        output_dir = './files'
        os.makedirs(output_dir, exist_ok=True)

        now = datetime.now()

        # Save the DataFrame to CSV
        data_df.to_csv(os.path.join(output_dir, f'{now}.csv'), sep=" ")
        # Prepare data feed for Cerebro
        # data_feed = bt.feeds.PandasData(dataname=data_df)
        # cerebro.adddata(data_feed, name=asset)

    # cerebro.broker.setcash(1000)

    # cerebro.addstrategy(MyStrategy)  # Custom strategy
    # cerebro.addstrategy(BuyAndHold)  # Buy-and-hold benchmark
    #
    # print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())
    # cerebro.run()
    # print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())
    #
    # cerebro.plot()


if __name__ == "__main__":
    main()
