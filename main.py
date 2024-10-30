from datetime import datetime, timezone

import backtrader as bt
import pandas as pd

from data import OhlcRequest
from repo import MongoConnector


class MyStrategy(bt.Strategy):
    def __init__(self):
        self.sma = bt.indicators.MovingAverageSimple(self.data.close)

    def next(self):
        pass
        # if self.data.close[0] > self.sma[0]:
        #     self.buy()
        # elif self.data.close[0] < self.sma[0]:
        #     self.sell()


def main():
    # Initialize Cerebro engine

    mongo_connector = MongoConnector()

    # Create OHLC request
    ohlc_request = OhlcRequest(
        asset="btc",
        quote="usdt",
        interval="1m",
        market="spot",
        exchange="binance",
        start_time=datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    )

    # Fetch data from MongoDB and convert it to a list of dictionaries
    data_list = mongo_connector.find_all_ohlc_data(ohlc_request)

    # Convert the list of OhlcEntity objects to a Pandas DataFrame
    data_df = pd.DataFrame([{
        'baseQuote': f"{data.symbol}{data.base}",
        'datetime': data.dateTime,
        'open': data.open,
        'high': data.high,
        'low': data.low,
        'close': data.close,
        'volume': data.volume
    } for data in data_list])

    # Set the datetime column as the index and ensure it's in datetime format
    data_df['datetime'] = pd.to_datetime(data_df['datetime'])
    data_df.set_index('datetime', inplace=True)

    # Prepare Backtrader data feed from the DataFrame
    data_feed = bt.feeds.PandasData(dataname=data_df)

    # Initialize Cerebro engine
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MyStrategy)

    # Load data into Cerebro
    cerebro.adddata(data_feed)

    # Set initial capital
    cerebro.broker.setcash(100000)

    # Run the backtest
    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())
    cerebro.run()
    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # Plot the results
    cerebro.plot()


if __name__ == "__main__":
    main()
