#
# Backtester class
# Class to backtest simple strategies
#

import numpy as np
import os
from typing import (Any, MutableSequence)

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
import nfpy.Math as Math
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

from .BaseStrategy import TyStrategy
from .BaseSizer import TySizer
from .Enums import *


class Portfolio(object):
    """ Class representing a single-security portfolio for backtesting. """

    def __init__(self, initial: float):
        self._last_sig = None  # Last executed signal
        self._cost_basis = .0  # Average price of the position

        self.cash = float(initial)  # Available cash
        self.initial = float(initial)
        self.final_value = .0  # Final value of the portfolio
        self.num_buy = 0
        self.num_sell = 0
        self.shares = 0  # Number of shares
        self.total_return = .0
        self.trades = []  # List of executed trades

    def buy(self, dt: np.datetime64, p: float, s: int, sz: int) -> None:
        """ Buy the position.

            Input:
                dt [np.datetime64]: date
                price [float]: price
                signal [int]: signal
                size [float]: quantity in percentage of the available
        """
        paid = sz * p
        self._cost_basis = (self.shares * self._cost_basis + paid) / \
                           (self.shares + sz)
        self.cash -= paid
        self.shares += sz
        assert self.cash >= .0

        trade = (dt, s, p, sz, paid, self._cost_basis, .0, .0)
        self.trades.append(trade)
        self._last_sig = s
        self.num_buy += 1

    def sell(self, dt: np.datetime64, p: float, s: int, sz: int) -> None:
        """ Sell the position.

            Input:
                dt [np.datetime64]: date
                price [float]: price
                signal [int]: signal
                size [float]: quantity in percentage of the available
        """
        if self.shares == 0:
            return

        received = sz * p
        self.cash += received
        self.shares -= sz
        assert self.cash >= .0

        ret = p / self._cost_basis - 1.
        trade = (dt, s, p, sz, received, self._cost_basis,
                 (p - self._cost_basis) * sz, ret)
        self.trades.append(trade)

        self._last_sig = -1
        self.num_sell += 1

    def statistics(self) -> None:
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


class Backtester(object):
    _DT_FMT = '%Y%m%d'

    def __init__(self, uids: MutableSequence[str], initial: float, debug: bool):
        # Handlers
        self._af = Ast.get_af_glob()
        self._conf = get_conf_glob()

        # Input variables
        self._debug = bool(debug)
        self._initial = float(initial)
        self._uids = tuple(uids)

        # Objects to set
        self._sizer = None
        self._strat = None
        self._params = {}

        # Working variables
        self._backtest_dir = ''
        self._q = ''

        # Output variables
        self._res = {}

    @property
    def results(self) -> dict[str, Portfolio]:
        if not self._res:
            self.run()
        return self._res

    @results.deleter
    def results(self) -> None:
        self._res = {}

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
    def sizer(self, s: TySizer) -> None:
        self._sizer = s

    @property
    def parameters(self) -> dict[str, Any]:
        return self._params

    @parameters.setter
    def parameters(self, p: dict[str, Any]) -> None:
        self._params = p

    def _create_new_directory(self) -> None:
        """ Create a new directory for the current backtest. """
        end = Cal.get_calendar_glob() \
            .end \
            .strftime(self._DT_FMT)
        path = os.path.join(
            self._conf.backtest_path,
            f'Backtest_{end}'
        )
        self._backtest_dir = path

        # If directory exists exit
        if os.path.exists(path):
            return

        try:
            os.makedirs(path)
        except OSError as ex:
            print(f'Creation of the directory {path} failed')
            raise ex
        else:
            print(f'Successfully created the directory {path}')

    def run(self) -> None:
        # Initializations
        self._create_new_directory()

        # Backtest strategy
        for uid in self._uids:
            eq = self._af.get(uid)
            try:
                self._backtest(eq)
            except RuntimeError as ex:
                print(ex)

        # Consolidate results
        # self._consolidate()

    def _backtest(self, eq: Ast.TyAsset) -> None:
        """ The backtester applies the strategy to the series and obtains
            signals with their dates and strength.
        """
        print(f'>>> {eq.uid}')

        p = eq.prices.values
        dt = eq.prices.index.values
        try:
            strat = self._strat(dt, p, **self._params)
            ptf = self._apply(dt, p, strat, self._initial)
        except (IndexError, TypeError) as ex:
            print(f'Backtest failed for {eq.uid}\n{ex}')
            return
        else:
            ptf.statistics()
            self._res[eq.uid] = ptf

    def _apply(self, dates: np.ndarray, prices: np.ndarray,
               strat: TyStrategy, initial: float) -> Portfolio:
        """ Perform the backtesting of a simple strategy. Assumptions:

            Input:
                dates [np.ndarray]: dates series
                price [np.ndarray]: price series of the instrument
                signals [StrategyResult]: signals to backtest
                initial [float]: initial cash value

            Output:
                ptf [Portfolio]: backtested hypothetical portfolio

            TODOs: The following assumptions are valid and must be relaxed:
                1. No short selling
                2. No transaction costs
                3. Fractional ownership of stocks allowed
                4. Any stock available at the end of the time period is
                   converted to cash at the last available price
        """
        # Make sure to have no nans in prices
        ptf = Portfolio(initial=initial)
        prices = Math.ffill_cols(prices)
        self._sizer.set(prices, ptf)

        signals = strat.bulk_exec()
        if len(signals) == 0:
            return ptf

        # Initialize working variables
        pending = []
        t = 0
        sig_iterator = signals.__iter__()
        next_signal = next(sig_iterator)

        # Cycle until time is over
        while t < strat.max_length:

            # No pending orders => move time to next signal and append order
            if len(pending) > 0:
                orders_sublist = []

                # Cycle through pending orders
                while pending:
                    # Pop the first order
                    order = pending.pop(0)

                    # Check what action to take with the order
                    action = strat.check_order_validity(order)

                    # If the order is marketable apply it
                    if action == 'execute':
                        # Calculate order size
                        signal = order[3]
                        dt = dates[t]
                        sz = self._sizer(t, signal)
                        if sz > 0:
                            # If size is greater than zero buy/sell
                            if order[3] == 1:  # BUY
                                # Calculate buy price and apply
                                p = max(prices[t], prices[t - 1])
                                ptf.buy(dt, p, signal, sz)
                            else:
                                # Calculate sell price and apply
                                p = min(prices[t], prices[t - 1])
                                ptf.sell(dt, p, signal, sz)

                    # If the order is to be kept do it
                    elif action == 'keep':
                        orders_sublist.append(order)

                # After cycling all orders update the pending list
                pending = orders_sublist

                if next_signal is None:
                    t = strat.max_length
                elif next_signal[0] == t:
                    pending.append([Order.MKT, *next_signal])
                    try:
                        next_signal = sig_iterator.__next__()
                    except StopIteration:
                        next_signal = None

            else:
                t = next_signal[0]
                pending.append([Order.MKT, *next_signal])
                try:
                    next_signal = sig_iterator.__next__()
                except StopIteration:
                    next_signal = None

            # Update the time
            t += 1

        # Sell any residual security at the current market price at the end of
        # the backtesting period to get the final portfolio value
        ptf.sell(dates[-1], prices[-1], -1, ptf.shares)

        # Clean up
        self._sizer.clean()

        return ptf

    # def _consolidate(self):
    #     """ Creates consolidated results objects by grouping equities by some
    #         given logic. A consolidated result of all backtested equities is
    #         always generated.
    #     """
    #     csd = ConsolidatedResults()
    #     for uid, bt in self._res.items():
    #         csd.total_ret.append(bt.total_return)
    #         csd.final_value.append(bt.final_value)
    #         csd.trade_rets.extend(bt.returns)
    #         csd.trades_number.append(len(bt.trades))
    #         csd.buy_number.append(bt.num_buy)
    #         csd.sell_number.append(bt.num_sell)
    #
    #     self._res['consolidated'] = csd

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
