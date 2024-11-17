import os
from datetime import datetime, timezone, timedelta
import backtrader as bt
import pandas as pd
import numpy as np
from typing import List, Dict

from assets import assets_to_trade
from backtest import run_multiasset_backtest
from data import OhlcRequest, AssetAndIntervalData
from repo import MongoConnector
from strategies.ersten_rsi_strategy import ErstenRsiStrategy
from strategies.reconfiguring_strategy import ReconfiguringStrategy


def main():
    # Initialize Cerebro engine
    mongo_connector = MongoConnector()

    quote = "usdt"
    interval = "15m"
    interval_for_trading = "1d"
    market = "spot"
    exchange = "binance"
    start_time = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)

    asset_to_data: List[AssetAndIntervalData] = []
    for asset in assets_to_trade:
        ohlc_request = OhlcRequest(
            asset=asset,
            quote=quote,
            interval=interval,
            market=market,
            exchange=exchange,
            start_time=start_time
        )
        # Fetch data from MongoDB and convert to DataFrame
        data_list = mongo_connector.find_ohlc_data(ohlc_request)
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

        data_df['datetime'] = pd.to_datetime(data_df['datetime'])
        data_df.set_index('datetime', inplace=True)

        if (interval_for_trading == "1d"):
            data_df = data_df.resample('D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })

        data_feed = bt.feeds.PandasData(
            dataname=data_df,
            name=asset
        )

        asset_to_data.append(AssetAndIntervalData(asset=asset, intervalToData={interval_for_trading: data_feed}))

        # Ensure the directory exists
        output_dir = './files'
        os.makedirs(output_dir, exist_ok=True)
        now = datetime.now()
        data_df.to_csv(os.path.join(output_dir, f'{asset}_{now}.csv'), sep=" ")

        # Prepare data feed for Cerebro
    run_multiasset_backtest(asset_data=asset_to_data, interval=interval_for_trading, strategy_class=ErstenRsiStrategy)
    # run_backtest(asset, data_df, BuyAndHold)


if __name__ == "__main__":
    main()
