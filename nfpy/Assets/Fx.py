#
# Fx
# Class for exchange rates
#

import pandas as pd
from typing import Callable

import nfpy.Calendar as Cal
from nfpy.Tools import (Exceptions as Ex)

from .Asset import Asset


class Fx(Asset):
    """ Class for exchange rates. """

    _TYPE = 'Fx'
    _BASE_TABLE = 'Fx'
    _TS_TABLE = 'FxTS'
    _TS_ROLL_KEY_LIST = ['date']
    _DEF_PRICE_DTYPE = 'Price.Raw.Close'

    def series(
        self,
        dtype: str,
        start: Cal.TyDate | None = None,
        end: Cal.TyDate | None = None
    ) -> pd.Series:
        """ Return the requested series. """

        # Since fx do not pay dividends and do not split, we transform any
        # price or return request into a request for Raw data to avoid
        # duplications of operations and memory
        levels = dtype.split('.')
        if levels[0] in ('Price', 'Return', 'LogReturn'):
            dtype = dtype.replace(levels[1], 'Raw')

        return super(Fx, self).series(
            dtype,
            start=start,
            end=end
        )

    def _series_callback(
        self,
        dtype: str,
        start: Cal.TyDate | None = None,
        end: Cal.TyDate | None = None
    ) -> tuple[Callable, tuple]:
        """ Return the callback for converting series. """
        data = dtype.split('.')

        # Volume
        if data[0] == 'Volume':
            return self.load_dtype_in_df, (dtype, start, end)

        # Prices
        elif data[0] == 'Price':
            return self.load_dtype_in_df, (dtype, start, end)

        # Returns
        elif data[0] == 'Return':
            return self._calc_returns, (
                dtype.replace('Return', 'Price'),
                start, end
            )
        elif data[0] == 'LogReturn':
            return self._calc_log_returns, (
                dtype.replace('LogReturn', 'Price'),
                start, end
            )

        # Error if datatype is not in the list
        else:
            msg = f'Fx(): datatype {dtype} for {self._uid} not recognized!'
            raise Ex.DatatypeError(msg)
