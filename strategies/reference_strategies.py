import backtrader as bt


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
