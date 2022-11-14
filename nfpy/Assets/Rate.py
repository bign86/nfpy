#
# Equity class
# Base class for simple equity stock
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


class Rate(Asset):
    """ Base class for interest rates """

    _TYPE = 'Rate'
    _BASE_TABLE = 'Rate'
    _TS_TABLE = 'RateTS'
    _TS_ROLL_KEY_LIST = ['date']
    _DEF_PRICE_DTYPE = 'Price.Raw.Close'

    def __init__(self, uid: str):
        super(Rate, self).__init__(uid)
        self._freq = None

    @property
    def frequency(self) -> str:
        return self._freq

    @frequency.setter
    def frequency(self, v: str) -> None:
        self._freq = v

    def load_dtype_in_df(self, dtype: str) -> bool:
        """ Load the datatype and merge into the dataframe. Takes care to load
            aganst the appropriate calendar frequency.
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
            df.index = df.index + 0*pd.offsets.BDay()

            self._df = self._df.merge(
                df,
                how='left',
                left_index=True,
                right_index=True
            )
            self._df.sort_index(inplace=True)

            if dtype.split('.')[0] == 'Price':
                code = self._dt.get(dtype)
                # The value from the database is in annual percentage points
                self._df.loc[:, code] *= .01

        return success

    def series_callback(self, dtype: str) -> tuple[Callable, tuple]:
        """ Return the callback for converting series. """

        # Since rates do not pay dividends and do not split, we transform any
        # price or return request into a request for Raw data to avoid
        # duplications of operations and memory
        levels = dtype.split('.')
        if levels[0] in ('Price', 'Return', 'LogReturn'):
            dtype = dtype.replace(levels[1], 'Raw')
            return self.load_dtype_in_df, (dtype,)

        # Error if datatype is not in the list
        else:
            msg = f'Rate(): datatype {dtype} for {self._uid} not recognized!'
            raise Ex.DatatypeError(msg)
