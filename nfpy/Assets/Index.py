#
# Index
# Class for indices
#

import cutils
import numpy as np
import pandas as pd
from typing import Callable

from nfpy.Calendar import Frequency
from nfpy.Tools import (Exceptions as Ex)

from .Asset import Asset

_CALENDAR_TRANSFORM = {
    Frequency.D: 'C',
    Frequency.M: 'BMS',
    Frequency.Y: 'BAS-JAN',
}


class Index(Asset):
    """ Class for indices. """

    _TYPE = 'Index'
    _BASE_TABLE = 'Index'
    _TS_TABLE = 'IndexTS'
    _TS_ROLL_KEY_LIST = ['date']
    _DEF_PRICE_DTYPE = 'Price.Raw.Close'

    def __init__(self, uid: str):
        super(Index, self).__init__(uid)
        self._freq = None

    @property
    def frequency(self) -> Frequency:
        return self._freq

    @frequency.setter
    def frequency(self, v: str) -> None:
        self._freq = Frequency(v)

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
                ('Raw', True, 1),
                ('SplitAdj', True, 1)
            ]
        elif target == 'SplitAdj':
            seq = [
                ('Adj', True, -1),
                ('Raw', False, 1)
            ]
        else:
            seq = [
                ('Adj', True, -1),
                ('SplitAdj', False, -1)]

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
        if success[2] == 1:

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

        # Insert the newly calculated series into the dataframe putting back
        # the original NaNs
        res[nan_mask] = np.nan
        code = self._dt.get(dtype)
        self._df[code] = res
        return True

    def load_dtype_in_df(self, dtype: str) -> bool:
        """ Load the datatype and merge into the dataframe. Takes care to load
            against the appropriate calendar frequency.
        """
        freq = self._df.index.freqstr
        if freq != _CALENDAR_TRANSFORM[self._freq]:
            if self._freq == Frequency.D:
                calendar = self._cal.calendar
            elif self._freq == Frequency.M:
                calendar = self._cal.monthly_calendar
            elif self._freq == Frequency.Y:
                calendar = self._cal.yearly_calendar
            else:
                msg = f'Index(): calendar frequency not recognized for {self._uid}'
                raise Ex.CalendarError(msg)
            self._df = pd.DataFrame(index=calendar)

        success, df = self.load_dtype(dtype)
        if success:
            self._df = self._df.merge(
                df,
                how='left',
                left_index=True,
                right_index=True
            )
            self._df.sort_index(inplace=True)

        return success

    def series(self, dtype: str) -> pd.Series:
        """ Return the requested series. If data are not found an empty series
            is returned unless the  callback throws an exception.

            Input:
                dtype [str]: datatype to load

            Output:
                res [pd.Series]: fetched series
        """
        # Since indexes do not pay dividends and do not split, we transform any
        # price or return request into a request for Raw data to avoid
        # duplications of operations and memory
        # levels = dtype.split('.')
        # if levels[0] in ('Price', 'Return', 'LogReturn'):
        #     dtype = dtype.replace(levels[1], 'Raw')

        code = self._dt.get(dtype)
        if code not in self._df.columns:
            call, args = self.series_callback(dtype)
            if not call(*args):
                return pd.Series(dtype=float)
        return self._df[code]

    def series_callback(self, dtype: str) -> tuple[Callable, tuple]:
        """ Return the callback for converting series. """
        data = dtype.split('.')

        # Volume
        if data[0] == 'Volume':
            return self.load_dtype_in_df, (dtype,)

        # Prices
        elif data[0] == 'Price':
            return self._prices_loader, (dtype, data[1])

        # Returns
        elif data[0] == 'Return':
            return self._calc_returns, (dtype.replace('Return', 'Price'),)
        elif data[0] == 'LogReturn':
            return self._calc_log_returns, (dtype.replace('LogReturn', 'Price'),)

        # Error if datatype is not in the list
        else:
            msg = f'Index(): datatype {dtype} for {self._uid} not recognized!'
            raise Ex.DatatypeError(msg)
