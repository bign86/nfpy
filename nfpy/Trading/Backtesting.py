#
# Backtesting functions
# Functions to backtest simple strategies
#

from collections import deque
import numpy as np
import os
from typing import (Sequence, Iterable)

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
import nfpy.Financial.Math as Math
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

from .BaseStrategy import (TyStrategy, StrategyResult)
from .BaseSizer import TySizer
from .Enums import *


class Portfolio(object):
    """ Class representing a single-security portfolio for backtesting. """

    def __init__(self, initial: float):
        self._last_sig = None  # Last executed signal
        self._cost_basis = .0  # Average price of the position

        self.cash = float(initial)  # Available cash
        self.final_value = .0  # Final value of the portfolio
        self.initial = float(initial)
        self.num_buy = 0
        self.num_sell = 0
        self.returns = []  # List of returns from closing positions
        self.shares = 0  # Number of shares
        self.total_return = .0
        self.trades = []  # List of executed trades

    def buy(self, dt: np.datetime64, p: float, s: Signal, sz: int):
        """ Buy the position.

            Input:
                dt [np.datetime64]: date
                size [float]: quantity in percentage of the available
                price [float]: price
        """
        paid = sz * p
        self._cost_basis = (self.shares * self._cost_basis + paid) / \
                           (self.shares + sz)
        self.cash -= paid
        self.shares += sz
        assert self.cash >= .0

        trade = (dt, s, p, sz, paid, self._cost_basis, .0)
        self.trades.append(trade)
        self._last_sig = s

    def sell(self, dt: np.datetime64, p: float, s: Signal, sz: int):
        """ Sell the position.

            Input:
                p [float]: price
                t [np.datetime64]: date
                q [float]: quantity in percentage of the invested
        """
        if self.shares == 0:
            return

        received = sz * p
        self.cash += received
        self.shares -= sz
        assert self.cash >= .0

        trade = (dt, s, p, sz, received, self._cost_basis,
                 (p - self._cost_basis) * sz)
        self.trades.append(trade)
        self._last_sig = Signal.SELL

        ret = p / self._cost_basis - 1.
        self.returns.append(ret)

    def statistics(self):
        for t in self.trades:
            if t[1] == Signal.BUY:
                self.num_buy += 1
            else:
                self.num_sell += 1

        self.final_value = self.cash
        self.total_return = self.cash / self.initial - 1.


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

        # Objects to set
        # self._pricer = None
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

    # @property
    # def pricer(self) -> TyPricer:
    #     return self._pricer
    #
    # @pricer.setter
    # def pricer(self, p: TyPricer):
    #     self._pricer = p

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
            try:
                self._backtest(eq)
            except RuntimeError as ex:
                print(ex)

        # Consolidate results
        self._consolidate()

    def _backtest(self, eq):
        """ The backtester applies the strategy to the series and obtains
            signals with their dates and strength.
        """
        # print('>>> {}'.format(eq.uid))

        p = eq.prices.values
        try:
            signals = self._strat(self._dt, p)
        except (IndexError, TypeError) as ex:
            print('Backtest failed for {}\n{}'.format(eq.uid, ex))
            return
        else:
            ptf = self._apply(p, signals, self._initial)
            ptf.statistics()
            self._res[eq.uid] = ptf

    def _apply(self, prices: np.ndarray, signals: StrategyResult,
               initial: float) -> Portfolio:
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
                pricer [Pricer]: pricer that determines the price of the trade
                initial [float]: initial cash value

            Output:
                ptf [Portfolio]: backtested hypothetical portfolio
        """
        ptf = Portfolio(initial=initial)

        # Orders book. Each submitted order is added here
        book = deque()

        # Make sure to have no nans
        prices = Math.ffill_cols(prices)
        # self._pricer.set(prices)
        self._sizer.set(prices, ptf)

        j = 0
        for t in signals:
            idx, dt, sig, strg = t

            # Advance to the following signal applying the orders in the book
            while self._dt[j] < dt:
                n = len(book)
                i = 0
                while i < n:
                    o = book.pop()
                    if not self._execute(ptf, prices, j, o[0], o[1]):
                        book.appendleft(o)
                    i += 1
                j += 1

            # Insert an order into the book. The new order is put in the book
            # after we check whether actionable orders are present
            s = Signal.BUY if sig > 0 else Signal.SELL
            # p = self._pricer(j, s)
            sz = self._sizer(j, s)
            book.appendleft((s, sz))

        # Sell residual securities at the current market price
        ptf.sell(self._dt[-1], prices[-1], Signal.SELL, ptf.shares)

        # Clean up
        self._sizer.clean()
        # self._pricer.clean()

        return ptf

    def _execute(self, ptf: Portfolio, prices: np.ndarray, i: int,
                 s: Signal, sz: int) -> bool:
        """ Tries to execute the input order. """
        dt = self._dt[i]
        if s == Signal.BUY:
            p = max(prices[i-1], prices[i])
            ptf.buy(dt, p, s, sz)
        else:
            p = min(prices[i-1], prices[i])
            ptf.sell(dt, p, s, sz)
        return True

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

    def print(self):
        c0 = self._initial
        for uid in self._uids:
            ptf = self._res[uid]
            print('{} [{}]\t{:.0f}\t{:.1%}'
                  .format(uid, len(ptf.trades), ptf.cash, ptf.cash / c0 - 1.))
            for t in ptf.trades:
                print('{} {}\t{:.2f}\t{}\t{:.2f}\t{:.2f}\t{:.2f}'
                      .format(str(t[0])[:10], *t[1:]))

        ptf = self._res['consolidated']
        print(ptf)

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
    # assets_value = ptf.shares * Fin.last_valid_value(prices)[0]
    # final_value = assets_value + ptf.cash
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
    # print('{:.2f}'.format(earned + assets_value - ptf.shares * ptf._cost_basis))
    # print('{:.2f} {:.1%}'.format(final_value, final_value / 10000. - 1.))
    # print('{:.2f} + {:.2f} = {:.2f}'.format(op, assets_value, op + assets_value))
    #
