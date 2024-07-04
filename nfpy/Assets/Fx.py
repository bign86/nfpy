#
# Fx
# Class for exchange rates
#

import pandas as pd
from typing import Callable

from nfpy.Tools import (Exceptions as Ex)

from .Asset import Asset


class Fx(Asset):
    """ Class for exchange rates. """

    _TYPE = 'Fx'
    _BASE_TABLE = 'Fx'
    _TS_TABLE = 'FxTS'
    _TS_ROLL_KEY_LIST = ['date']
    _DEF_PRICE_DTYPE = 'Price.Raw.Close'

    def series(self, dtype: str) -> pd.Series:
        """ Return the requested series. """

        # Since fx do not pay dividends and do not split, we transform any
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
            return self.load_dtype_in_df, (dtype,)

        # Returns
        elif data[0] == 'Return':
            return self._calc_returns, (dtype.replace('Return', 'Price'),)
        elif data[0] == 'LogReturn':
            return self._calc_log_returns, (dtype.replace('LogReturn', 'Price'),)

        # Error if datatype is not in the list
        else:
            msg = f'Fx(): datatype {dtype} for {self._uid} not recognized!'
            raise Ex.DatatypeError(msg)
