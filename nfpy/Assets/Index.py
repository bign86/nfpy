#
# Index
# Class for indices
#

import pandas as pd
from typing import Callable

from nfpy.Tools import (Exceptions as Ex)

from .Asset import Asset

_CALENDAR_TRANSFORM = {
    'D': 'C',
    'M': 'BMS',
    'Y': 'BAS-JAN',
}


class Index(Asset):
    """ Class for indices. """

    _TYPE = 'Index'
    _BASE_TABLE = 'Index'
    _TS_TABLE = 'IndexTS'
    _TS_ROLL_KEY_LIST = ['date']
    _DEF_PRICE_DTYPE = 'Price.Raw.Close'

    @property
    def frequency(self) -> str:
        return self._freq

    @frequency.setter
    def frequency(self, v: str) -> None:
        self._freq = v

    def _prices_loader(self, dtype: str, level: str) -> bool:
        """ Load the prices and, if missing, try sequentially to calculate them
            from other price data available in the database.
        """
        # Try all possibilities
        success = None
        for part in ('Raw', 'SplitAdj', 'Adj'):
            other_dtype = dtype.replace(level, part)
            if self.load_dtype_in_df(other_dtype):
                success = other_dtype
                break
            else:
                continue

        # Raise error if data are missing
        if not success:
            raise Ex.MissingData(f"Index(): {self.uid} {dtype} not found in the database!")

        code = self._dt.get(dtype)
        other_code = self._dt.get(other_dtype)
        self._df[code] = self._df[other_code].copy()
        return True

    def load_dtype_in_df(self, dtype: str) -> bool:
        """ Load the datatype and merge into the dataframe. Takes care to load
            against the appropriate calendar frequency.
        """
        freq = self._df.index.freqstr
        if freq != _CALENDAR_TRANSFORM[self._freq]:
            if self._freq == 'M':
                calendar = self._cal.monthly_calendar
            elif self._freq == 'Y':
                calendar = self._cal.yearly_calendar
            else:
                msg = f'Rate(): calendar frequency not recognized for {self._uid}'
                raise ValueError(msg)
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
        levels = dtype.split('.')
        if levels[0] in ('Price', 'Return', 'LogReturn'):
            dtype = dtype.replace(levels[1], 'Raw')

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
