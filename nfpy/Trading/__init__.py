from . import Strategies
from .Backtesting import backtest
from .Trends import find_ts_extrema, group_extrema


__all__ = [
    'Strategies', 'backtest', 'find_ts_extrema', 'group_extrema'
]
