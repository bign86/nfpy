#
# Equity class
# Base class for simple equity stock
#

import pandas as pd
from typing import Callable

from nfpy.Calendar import Frequency

from .Asset import Asset

_CALENDAR_TRANSFORM = {
    Frequency.D: 'C',
    Frequency.M: 'BMS',
    Frequency.Y: 'BAS-JAN',
}


class DerivedSeries(Asset):
    """ Base class for derived series """

    _TYPE = 'DerivedSeries'
    _BASE_TABLE = 'DerivedSeries'
    _TS_TABLE = 'DerivedSeriesTS'
    _TS_ROLL_KEY_LIST = ['date']

    def __init__(self, uid: str):
        super(DerivedSeries, self).__init__(uid)
        self._freq = None
        self._horizon = None

    @property
    def frequency(self) -> Frequency:
        return self._freq

    @frequency.setter
    def frequency(self, v: str) -> None:
        self._freq = Frequency(v)

    @property
    def horizon(self) -> str:
        return self._horizon

    @horizon.setter
    def horizon(self, v: str) -> None:
        self._horizon = v

    def series_callback(self, dtype: str) -> tuple[Callable, tuple]:
        """ Return the callback for converting series. The callback must return
            a bool indicating success/failure.
        """
        return self.load_dtype_in_df, (dtype,)

    def load_dtype_in_df(self, dtype: str) -> bool:
        """ Load the datatype and merge into the dataframe. Takes care to load
            against the appropriate calendar frequency.
        """
        freq = self._df.index.freqstr
        if freq != _CALENDAR_TRANSFORM[self._freq]:
            if self._freq == Frequency('M'):
                calendar = self._cal.monthly_calendar
            elif self._freq == Frequency('Y'):
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
