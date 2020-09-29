#
# Backtesting functions
# Functions to backtest simple strategies
#

import numpy as np
import pandas as pd

from nfpy.Trading.Strategies import *


def backtest(price: pd.Series, signals: pd.Series, nominal: float = 1.) -> tuple:
    """ Perform the backtesting of a simple strategy. Assumptions:
            1. No short selling allowed. The first valid signal must be 'BUY'
            2. No transaction costs
            3. Fractional ownership of stocks allowed
            4. Any stock available at the end of the time period is converted
               to cash at the last available price

        Input:
            price [pd.Series]: price series of the instrument
            signals [pd.Series]: signals to backtest
            nominal [float]: nominal value of the portfolio (default: 1.)

        Output:
            value [float]: final value of the portfolio
            ret [float]: final return of the strategy
            trades [pd.Dataframe]: trades information
    """
    sig = signals.copy()
    p = price.copy()
    p.ffill(inplace=True)

    # no short selling allowed, therefore we start with a buy
    if sig.iat[0] < 0:
        sig.drop(sig.index[0], inplace=True)
    if sig.iat[-1] > 0:
        sig.at[p.index[-1]] = -1.
        p = p[sig.index]

    cols = ['tr_start', 'tr_end', 'p_buy', 'p_sell', 'days', 'total_ret', 'daily_ret']
    df = pd.DataFrame(index=range(len(sig[sig > 0.])), columns=cols)

    cash = nominal
    stocks = 0.
    trade = 0
    for idx, row in sig.iteritems():
        if row > 0:
            p_idx = p[idx]
            spent = row * cash
            stocks = stocks + spent / p_idx
            cash = cash - spent
            df.iat[trade, 0] = idx
            df.iat[trade, 2] = p_idx
        else:
            p_idx = p[idx]
            cash = cash + abs(row) * stocks * p_idx
            stocks = (1. + row) * stocks
            df.iat[trade, 1] = idx
            df.iat[trade, 3] = p_idx
            trade = trade + 1

    df['total_ret'] = df['p_sell'] / df['p_buy'] - 1.
    df['days'] = (df['tr_end'] - df['tr_start']).dt.days
    df['daily_ret'] = np.power(df['total_ret'] + 1., 1./df['days']) - 1.

    value = cash + stocks * p.iat[-1]
    ret = value / nominal - 1.

    return value, ret, df
