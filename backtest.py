from typing import Dict, List

import backtrader as bt
import backtrader.feeds
import pandas as pd

from data import AssetAndIntervalData


def run_multiasset_backtest(asset_data: List[AssetAndIntervalData], strategy_class):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class)
    for data in asset_data:
        cerebro.adddata(data.intervalToData.get("1d"), name = f"{data.asset}_1d")

    # Set initial cash
    initial_cash = 1000  # Set consistent initial cash
    cerebro.broker.set_cash(initial_cash)

    # Add analyzers with names for easy access
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, riskfreerate=0.01, _name='sharperatio')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')

    # Run the backtest
    results = cerebro.run()
    strat = results[0]
    #
    # # Retrieve analyzers' results
    # sharpe_ratio = strat.analyzers.sharperatio.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trade_analysis = strat.analyzers.tradeanalyzer.get_analysis()

    # Extract total number of trades
    total_trades = trade_analysis.total.closed if 'total' in trade_analysis and 'closed' in trade_analysis.total else 0

    # Extract net profit
    total_pnl = trade_analysis.pnl.net.total if 'pnl' in trade_analysis and 'net' in trade_analysis.pnl and 'total' in trade_analysis.pnl.net else 0

    # Display results for the strategy
    print(f'===============================\nResults for {strategy_class.__name__}:\n-------------------------------')
    print(f'Starting Value: ${initial_cash:.2f}')
    print(f'Ending Value: ${cerebro.broker.getvalue():.2f}')
    print(f'Total Trades: {total_trades}')
    print(f'Total Profit: ${cerebro.broker.getvalue() - initial_cash:.2f}')
    print(f'Net profit: ${total_pnl:.2f}')
    print(f'Max Drawdown: {drawdown["max"]["drawdown"]:.2f}%')
    print(f'Max Drawdown Duration: {drawdown["max"]["len"]} bars')

    print('===============================')
