#
# Backtesting functions
# Functions to backtest simple strategies
#

import os
from math import floor

import numpy as np
from typing import (Sequence, Iterable)

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
import nfpy.Financial.Math as Math
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

from .BaseStrategy import (TyStrategy, StrategyResult)
from .BaseSizer import TySizer


class Portfolio(object):
    """ Class representing a single-security portfolio for backtesting. """

    def __init__(self, initial: float):
        self._avail = float(initial)    # Available cash
        self._shares = 0                # Number of shares
        self._last_sig = None           # Last executed signal
        self._avg_pos = .0              # Average price of the position

        self.initial = float(initial)
        self.trades = []                # List of executed trades
        self.returns = []               # List of returns from closing positions
        self.num_buy = 0
        self.num_sell = 0
        self.final_value = .0           # Final value of the portfolio
        self.total_return = .0

    def buy(self, p: float, t: np.datetime64, q: float):
        """ Buy the position.

            Input:
                p [float]: price
                t [np.datetime64]: date
                q [float]: quantity in percentage of the available
        """
        to_invest = q * self._avail
        shares = int(to_invest // p)
        paid = shares * p
        self._avg_pos = (self._shares * self._avg_pos + paid) / \
                        (self._shares + shares)
        self._avail -= paid
        self._shares += shares
        assert self._avail >= .0

        trade = (t, 'BUY', p, shares, paid, self._avg_pos, .0)
        self.trades.append(trade)
        self._last_sig = 'BUY'

    def sell(self, p: float, t: np.datetime64, q: float):
        """ Sell the position.

            Input:
                p [float]: price
                t [np.datetime64]: date
                q [float]: quantity in percentage of the invested
        """
        if self._shares == 0:
            return

        to_cash = int(floor(q * self._shares))
        received = to_cash * p
        self._avail += received
        self._shares -= to_cash
        assert self._avail >= .0

        trade = (t, 'SELL', p, to_cash, received, self._avg_pos,
                 (p - self._avg_pos) * to_cash)
        self.trades.append(trade)
        self._last_sig = 'SELL'

        ret = p / self._avg_pos - 1.
        self.returns.append(ret)

    def statistics(self):
        for t in self.trades:
            if t[1] == 'BUY':
                self.num_buy += 1
            else:
                self.num_sell += 1

        self.final_value = self._avail
        self.total_return = self._avail / self.initial - 1.


class ConsolidatedResults(Ut.AttributizedDict):

    def __init__(self):
        super().__init__()
        self.total_ret = []
        self.final_value = []
        self.total_ret = []
        self.trade_rets = []
        self.trades_number = []
        self.buy_number = []
        self.sell_number = []


class Backtesting(object):
    _DT_FMT = '%Y%m%d'

    def __init__(self, uids: Sequence, initial: float, short: bool,
                 full_out: bool, debug: bool):
        # Handlers
        self._af = Ast.get_af_glob()
        self._cal = Cal.get_calendar_glob()
        self._conf = get_conf_glob()

        # Input variables
        self._debug = bool(debug)
        self._full_out = bool(full_out)
        self._initial = initial
        self._short = bool(short)
        self._uids = tuple(uids)

        # Strategy
        self._sizer = None
        self._strat = None

        # Working variables
        self._backtest_dir = ''
        self._dt = self._cal.calendar.values
        self._q = ""

        # Output variables
        self._res = {}

    @property
    def results(self) -> dict:
        return self._res

    @property
    def strategy(self) -> TyStrategy:
        return self._strat

    @strategy.setter
    def strategy(self, s: TyStrategy):
        self._strat = s

    @property
    def sizer(self) -> TySizer:
        return self._sizer

    @sizer.setter
    def sizer(self, s: TySizer):
        self._sizer = s

    def _gen_sample(self) -> Iterable:
        for uid in self._uids:
            yield self._af.get(uid)

    def _create_new_directory(self):
        """ Create a new directory for the current backtest. """
        backtest_path = self._conf.backtest_path
        new_folder = 'Backtest_' + self._cal.end.strftime(self._DT_FMT)
        path = os.path.join(backtest_path, new_folder)
        self._backtest_dir = path

        # If directory exists exit
        if os.path.exists(path):
            return

        try:
            os.makedirs(path)
        except OSError as ex:
            print('Creation of the directory {} failed'.format(path))
            raise ex
        else:
            print('Successfully created the directory {}'.format(path))

    def run(self) -> None:
        # Initializations
        self._create_new_directory()

        # Backtest strategy
        for eq in self._gen_sample():
            self._backtest(eq)

        # Consolidate results
        self._consolidate()

    def _backtest(self, eq):
        """ The backtester applies the strategy to the series and obtains
            signals with their dates and strength.

            TODO: it is possible to collect also the list of indices wrt the
                  original series to spare the additional np.searchsorted()
                  computation when they are applied
        """
        # print('>>> {}'.format(eq.uid))

        p = eq.prices.values
        try:
            signals = self._strat.f(self._dt, p)
        except (IndexError, TypeError) as ex:
            print('Backtest failed for {}\n{}'.format(eq.uid, ex))
            return
        else:
            ptf = self._apply(self._dt, p, signals, self._sizer, self._initial)
            ptf.statistics()
            self._res[eq.uid] = ptf

    @staticmethod
    def _apply(dates: np.ndarray, prices: np.ndarray, res: StrategyResult,
               sizer: TySizer, initial: float) -> Portfolio:
        """ Perform the backtesting of a simple strategy. Assumptions:
                1. No short selling, the first valid signal must be 'BUY'
                2. No transaction costs
                3. Fractional ownership of stocks allowed
                4. Any stock available at the end of the time period is
                   converted to cash at the last available price

            Input:
                dates [np.ndarray]: dates series
                price [np.ndarray]: price series of the instrument
                signals [StrategyResult]: signals to backtest
                sizer [Sizer]: sizer that determines the size of the trade
                initial [float]: initial cash value

            Output:
                ptf [Portfolio]: backtested hypothetical portfolio
        """
        prices = Math.ffill_cols(prices)

        ptf = Portfolio(initial=initial)
        j = 0

        for t in res:
            idx, dt, sig, strg = t
            # Advance up to t_signal
            while dates[j] < dt:
                j += 1

            if sig > 0:
                ptf.buy(prices[j], dates[j], sizer.s())
            else:
                ptf.sell(prices[j], dates[j], sizer.s())

        # Sell residual securities at the current market price
        ptf.sell(prices[-1], dates[-1], 1.)
        return ptf

    def _consolidate(self):
        """ Creates consolidated results objects by grouping equities by some
            given logic. A consolidated result of all backtested equities is
            always generated.
        """
        csd = ConsolidatedResults()
        for uid, bt in self._res.items():
            csd.total_ret.append(bt.total_return)
            csd.final_value.append(bt.final_value)
            csd.trade_rets.extend(bt.returns)
            csd.trades_number.append(len(bt.trades))
            csd.buy_number.append(bt.num_buy)
            csd.sell_number.append(bt.num_sell)

        self._res['consolidated'] = csd

    # @@@ RESULTS TO SAVE/SHOW @@@
    # + ptf final value and total return
    # + number of trades w/ % of buys and % of sells
    # - number of winning bets vs number of losing bets (only closing trades)
    # - average P&L on winning vs average P&L on losing (w/ returns)
    # - distribution of P&L for trades
    # - average life expectancy of a position
    # - distribution of trade life expectancies
    # - time series of ptf value
    # - time series of cash position
    #
    # +++ FORMULAS +++
    # - assets_final_value = owned_shares * last_price
    # - ptf_final_value = cash_available + assets_final_value
    # - ptf_final_return = ptf_final_value / ptf_initial_cash - 1
    # - owned_share_final_p&l = owned_shares * (last_price - average_cost)
    # - total_p&l = sum(trade_p&l) + owned_shares_final_p&l
    #
    # ++++++++++++++++++
    #
    # assets_value = ptf._shares * Fin.last_valid_value(prices)[0]
    # final_value = assets_value + ptf._avail
    #
    # op = 10000.
    # earned = .0
    # for t in ptf._trades:
    #     if t[1] == 'BUY':
    #         op -= t[4]
    #     else:
    #         op += t[4]
    #     earned += t[6]
    #     print('{}\t{}\t{:.2f}\t{:d}\t{:.2f}\t{:.2f}\t{:.2f}'
    #           .format(str(t[0])[:10], t[1], t[2], t[3], t[4], t[5], t[6]))
    #
    # print('{:.2f}'.format(earned + assets_value - ptf._shares * ptf._avg_pos))
    # print('{:.2f} {:.1%}'.format(final_value, final_value / 10000. - 1.))
    # print('{:.2f} + {:.2f} = {:.2f}'.format(op, assets_value, op + assets_value))
    #
