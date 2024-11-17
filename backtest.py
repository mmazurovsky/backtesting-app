from typing import Dict, List

import backtrader as bt
import backtrader.feeds
import pandas as pd

from data import AssetAndIntervalData


def run_multiasset_backtest(asset_data: List[AssetAndIntervalData], interval: str, strategy_class):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class)
    for data in asset_data:
        cerebro.adddata(data.intervalToData.get(interval), name=data.asset)

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

    # Retrieve analyzers' results
    sharpe_ratio = strat.analyzers.sharperatio.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trade_analysis = strat.analyzers.tradeanalyzer.get_analysis()

    # Extract basic metrics
    total_trades = trade_analysis.total.closed if 'total' in trade_analysis and 'closed' in trade_analysis.total else 0
    total_pnl = trade_analysis.pnl.net.total if 'pnl' in trade_analysis and 'net' in trade_analysis.pnl and 'total' in trade_analysis.pnl.net else 0

    # Calculate additional metrics
    winning_trades = trade_analysis.won.total if 'won' in trade_analysis and 'total' in trade_analysis.won else 0
    losing_trades = trade_analysis.lost.total if 'lost' in trade_analysis and 'total' in trade_analysis.lost else 0
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

    gross_profit = trade_analysis.pnl.gross.total if 'pnl' in trade_analysis and 'gross' in trade_analysis.pnl and 'total' in trade_analysis.pnl.gross else 0
    gross_loss = trade_analysis.pnl.gross.loss if 'pnl' in trade_analysis and 'gross' in trade_analysis.pnl and 'loss' in trade_analysis.pnl.gross else 0
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else float('inf')

    avg_profit_per_trade = (total_pnl / total_trades) if total_trades > 0 else 0
    avg_trade_duration = trade_analysis.len.average if 'len' in trade_analysis and 'average' in trade_analysis.len else 0

    # Display results for the strategy
    print(f'===============================\nResults for {strategy_class.__name__}:\n-------------------------------')
    print(f'Starting Value: ${initial_cash:.2f}')
    print(f'Ending Value: ${cerebro.broker.getvalue():.2f}')
    print(f'Total Trades: {total_trades}')
    print(f'Win Rate: {win_rate:.2f}%')
    print(f'Total Profit: ${cerebro.broker.getvalue() - initial_cash:.2f}')
    print(f'Net Profit: ${total_pnl:.2f}')
    print(f'Average Profit per Trade: ${avg_profit_per_trade:.2f}')
    print(f'Profit Factor: {profit_factor:.2f}')
    print(f'Max Drawdown: {drawdown["max"]["drawdown"]:.2f}%')
    print(f'Max Drawdown Duration: {drawdown["max"]["len"]} bars')
    print(f'Average Trade Duration: {avg_trade_duration:.2f} bars')
    print('===============================')
