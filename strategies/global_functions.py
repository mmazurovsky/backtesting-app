import backtrader as bt

def _cancel_all_orders(strategy: bt.Strategy, asset):
    if asset in strategy.opened_stop_orders:
        opened_stop_orders_for_asset = strategy.opened_stop_orders[asset]
        for stop_order in opened_stop_orders_for_asset:
            if stop_order.alive():  # Check if the order is still active
                strategy.cancel(stop_order)
        del strategy.opened_stop_orders[asset]
        del strategy.opened_long_orders[asset]


def notify_order(strategy: bt.Strategy, order):
    asset = order.data._name
    datetime = strategy.data.num2date(order.executed.dt)
    # Check if the order is completed (filled)
    if order.status in [order.Canceled, order.Expired, order.Rejected]:
        print(f"Not executed order for {asset} at {datetime}")
    if order.status == order.Completed:
        if order.isbuy():
            print(f'BUY {asset} at price: {order.executed.price:.5f} at {datetime}')
            strategy.opened_long_orders.setdefault(asset, []).append(order)
            # Place a stop loss order if it was a buy order
            if strategy.p.use_stop_loss is True:
                stop_price = order.executed.price * (1.0 - strategy.p.stop_loss)
                new_sl_order = strategy.sell(exectype=bt.Order.Stop, price=stop_price, size=order.size)
                if (new_sl_order is None):
                    print(asset)
                else:
                    strategy.opened_stop_orders.setdefault(asset, []).append(new_sl_order)

        elif order.issell():
            _cancel_all_orders(strategy, asset)
            if order.exectype in [bt.Order.Stop, bt.Order.StopTrail, bt.Order.StopTrailLimit, bt.Order.StopLimit]:
                print(f'Stop-loss SELL {asset} at price: {order.executed.price:.5f} at {datetime}')
            else:
                print(f'SELL {asset} at price: {order.executed.price:.5f} at {datetime}')
        else:
            print("Unidentified order")
