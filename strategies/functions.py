import backtrader as bt
import pandas as pd
import ta

def calculateRSI(data: bt.feeds.PandasData, rsi_period: int):
    closes = data.close

    # Ensure there are enough data points for the RSI calculation
    if len(closes) >= rsi_period:
        # Collect the last few closing prices for RSI calculation
        closes = closes.get(size=rsi_period)
        # closes.append(data_minute_close[0])  # Add the current close of minute data
        prices = pd.Series(closes)

        # Calculate RSI using the `ta` library

        rsi = ta.momentum.RSIIndicator(prices, window=rsi_period).rsi().iloc[-1]

        return rsi
    return None

def calculateSMA(data: bt.feeds.PandasData, sma_period: int):
    if len(data.close) >= sma_period:
        # Extract the close prices from the data feed
        close_prices = list(data.close.get(size=len(data.close)))

        # Create a pandas Series from the list of close prices
        prices = pd.Series(close_prices)

        # Now you can calculate the SMA using pandas
        sma = prices.rolling(window=sma_period).mean()

        # Return the latest SMA value
        return sma.iloc[-1]
    else:
        # Not enough data points to calculate SMA
        return None
