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
    closes = data.close

    # Ensure there are enough data points for the SMA calculation
    if len(closes) >= sma_period:
        # Collect the last few closing prices for SMA calculation
        closes = closes.get(size=sma_period)
        prices = pd.Series(closes)

        # Calculate SMA using the `ta` library
        sma = ta.trend.SMAIndicator(prices, window=sma_period).sma_indicator().iloc[-1]

        return sma
    return None
