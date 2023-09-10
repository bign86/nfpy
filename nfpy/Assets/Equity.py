#
# Equity class
# Base class for simple equity stock
#

import cutils
import numpy as np
import pandas as pd
from typing import (Callable, Optional)

import nfpy.Calendar as Cal
import nfpy.Math as Math
from nfpy.Tools import (Exceptions as Ex)

from . import get_af_glob
from .Asset import (Asset, TyAsset)


class Equity(Asset):
    """ Base class for equities """

    _TYPE = 'Equity'
    _BASE_TABLE = 'Equity'
    _TS_TABLE = 'EquityTS'
    _TS_ROLL_KEY_LIST = ['date']
    _DEF_PRICE_DTYPE = 'Price.Adj.Close'

    def __init__(self, uid: str):
        super().__init__(uid)
        self._index = None
        self._ticker = None

    @property
    def index(self) -> str:
        return self._index

    @index.setter
    def index(self, v: str):
        self._index = v

    @property
    def ticker(self) -> str:
        return self._ticker

    @ticker.setter
    def ticker(self, v: str):
        self._ticker = v

    def _dividends_loader(self, dtype: str, target: str) -> bool:
        """ Load the dividends and, if missing, try sequentially to calculate
            them from other price data available in the database.
        """
        if self.load_dtype_in_df(dtype):
            return True

        # The series is not available, take the other one and (un-)adjust it.
        operation = ('Raw', 1) if target == 'SplitAdj' else ('SplitAdj', -1)
        other_dtype = dtype.replace(target, operation[0])
        other_code = self._dt.get(other_dtype)
        if other_code not in self._df.columns:
            if not self.load_dtype_in_df(other_dtype):
                return False

        # We take the splits and create the series of the adjustment factors
        split = self.splits
        if split.empty:
            split_adj = 1.
        else:
            split = cutils.fillna(split.to_numpy(), 1.)
            split_adj = np.cumprod(split[::-1])[::-1]

        # We apply the adjusting factors to the loaded series
        other_values = self._df[other_code].values
        if operation[1] == 1:
            res = other_values * split_adj
        else:
            res = other_values / split_adj

        # Add target series to dataframe
        code = self._dt.get(dtype)
        self._df[code] = res
        return True

    def _prices_loader(self, dtype: str, target: str) -> bool:
        """ Load the prices and, if missing, try sequentially to calculate them
            from other price data available in the database.
        """
        # If the price series is available, load it and exit
        if self.load_dtype_in_df(dtype):
            return True

        # The series is not available, search for another that can be used to
        # calculate it. The tuple is:
        #   <start_data>, <adj_for_dividends>, <adj_for_splits>, <direction>
        # where direction is:
        #    1: sum/multiply
        #   -1: subtract/divide
        if target == 'Adj':
            seq = [
                ('Raw', True, True, 1),
                ('SplitAdj', True, False, 1)
            ]
        elif target == 'SplitAdj':
            seq = [
                ('Adj', True, False, -1),
                ('Raw', False, True, 1)
            ]
        else:
            seq = [
                ('Adj', True, True, -1),
                ('SplitAdj', False, True, -1)]

        success = ()
        while len(seq) > 0:
            operation = seq.pop()
            other_dtype = dtype.replace(target, operation[0])
            other_code = self._dt.get(other_dtype)
            if other_code not in self._df.columns:
                if self.load_dtype_in_df(other_dtype):
                    success = (other_code,) + operation[1:]
                    break
                else:
                    continue
            else:
                success = (other_code,) + operation[1:]
                break

        # Raise exception if no prices are available in general
        if not success:
            raise Ex.MissingData(f'Equity(): no prices found for {self._uid}')

        # Take the available series
        other_values = self._df[success[0]].values
        nan_mask = np.isnan(other_values)
        res = cutils.ffill(other_values.copy())

        # If we apply the adjustments
        if success[3] == 1:

            # Build factor from splits if needed
            if success[2] != 0:
                split = self.splits
                if not split.empty:
                    split = cutils.fillna(split.to_numpy().copy(), 1.)

                    split_adj = np.cumprod(split[::-1])[::-1]
                    res *= split_adj

            # Build factor from dividends if needed
            if success[1] != 0:
                dividends = self.series('Dividend.SplitAdj.Regular')
                if not dividends.empty:
                    dividends = cutils.fillna(dividends.to_numpy().copy(), 0.)

                    div_adj = 1. - dividends[1:] / res[:-1]
                    div_adj = np.cumprod(div_adj[::-1])[::-1]
                    res[:-1] *= div_adj

        # If we remove the adjustments
        else:

            # Build factor from dividends if needed
            if success[1] != 0:
                dividends = self.series('Dividend.SplitAdj.Regular')
                if not dividends.empty:
                    dividends = cutils.fillna(dividends.to_numpy().copy(), 0.)

                    div_adj = res[:-1] / (res[:-1] + dividends[1:])
                    div_adj = np.cumprod(div_adj[::-1])[::-1]
                    res[:-1] /= div_adj

            # Build factor from splits if needed
            if success[2] != 0:
                split = self.splits
                if not split.empty:
                    split = cutils.fillna(split.to_numpy().copy(), 1.)

                    split_adj = np.cumprod(split[::-1])[::-1]
                    res /= split_adj

        # Insert the newly calculated series into the dataframe putting back
        # the original NaNs
        res[nan_mask] = np.nan
        code = self._dt.get(dtype)
        self._df[code] = res
        return True

    def beta(self, benchmark: Optional[TyAsset] = None,
             start: Optional[Cal.TyDate] = None,
             end: Optional[Cal.TyDate] = None,
             w: Optional[int] = None, is_log: bool = False) -> tuple:
        """ Returns the beta between the equity and the benchmark index given
            as input. If dates are specified, the beta is calculated on the
            resulting interval (end date excluded). If a window is given, beta
            is calculated rolling.

            Input:
                benchmark [TyAsset]: usually an index (default: reference index)
                start [TyDate]: start date of the series (default: None)
                end [TyDate]: end date of the series (default: None)
                w [int]: window size for rolling calculation (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                beta [pd.Series]: beta of the regression
                adj_beta [pd.Series]: adjusted beta
                intercept [pd.Series]: intercept of the regression
        """
        if benchmark is None:
            benchmark = get_af_glob().get(self.index)
        elif not isinstance(benchmark, Asset):
            ty = type(benchmark).__name__
            raise TypeError(f'Objects of type {ty} cannot be used as benchmarks')

        eq_ret = self.log_returns if is_log else self.returns
        index_ret = benchmark.log_returns if is_log else benchmark.returns

        end = self._cal.t0 if end is None else end
        dts, beta, adj_b, itc = Math.beta(
            eq_ret.index.to_numpy(),
            eq_ret.to_numpy(),
            index_ret.to_numpy(),
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
            w=w
        )
        return (
            pd.Series(beta, index=dts),
            pd.Series(adj_b, index=dts),
            pd.Series(itc, index=dts)
        )

    def correlation(self, benchmark: Optional[TyAsset] = None,
                    start: Optional[Cal.TyDate] = None,
                    end: Optional[Cal.TyDate] = None,
                    is_log: bool = False) -> float:
        """ Returns the correlation between the equity and the benchmark given
            as input. If dates are specified, the correlation is calculated on
            the resulting interval (end date excluded).

            Input:
                benchmark [TyAsset]: usually an index (default: reference index)
                start [TyDate]: start date of the series (default: None)
                end [TyDate]: end date of the series excluded (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                corcoeff [float]: correlation coefficient
        """
        if benchmark is None:
            benchmark = get_af_glob().get(self.index)
        elif not isinstance(benchmark, Asset):
            ty = type(benchmark).__name__
            raise TypeError(f'Objects of type {ty} cannot be used as benchmarks')

        eq = self.log_returns if is_log else self.returns
        idx = benchmark.log_returns if is_log else benchmark.returns

        end = self._cal.t0 if end is None else end
        return Math.correlation(
            eq.index.to_numpy(),
            eq.to_numpy(),
            idx.to_numpy(),
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
        )[0, 1]

    @property
    def dividends(self) -> pd.Series:
        """ Loads the regular dividends series for the equity. The dividends are
            first converted in the base currency.
        """
        return self.series('Dividend.Raw.Regular')

    @property
    def dividends_special(self) -> pd.Series:
        """ Loads the special dividends series for the equity. The dividends are
            first converted in the base currency.
        """
        return self.series('Dividend.Raw.Special')

    @property
    def raw_prices(self) -> pd.Series:
        """ Returns the raw price series for the equity. """
        return self.series('Price.Raw.Close')

    def series_callback(self, dtype: str) -> tuple[Callable, tuple]:
        """ Return the callback for converting series. The callback must return
            a bool indicating success/failure.
        """
        if dtype in ('Split', 'Volume'):
            return self.load_dtype_in_df, (dtype,)

        data = dtype.split('.')

        # Prices
        if data[0] == 'Price':
            return self._prices_loader, (dtype, data[1])

        # Dividends
        elif data[0] == 'Dividend':
            return self._dividends_loader, (dtype, data[1])

        # Returns
        elif data[0] == 'Return':
            return self._calc_returns, (dtype.replace('Return', 'Price'),)
        elif data[0] == 'LogReturn':
            return self._calc_log_returns, (dtype.replace('LogReturn', 'Price'),)

        # Error if datatype is not in the list
        else:
            msg = f'Equity(): datatype {dtype} for {self._uid} not recognized!'
            raise Ex.DatatypeError(msg)

    @property
    def splits(self) -> pd.Series:
        """ Loads the splits series for the equity. """
        return self.series('Split')
