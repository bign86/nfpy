#
# Equity class
# Base class for simple equity stock
#

import pandas as pd
from typing import Callable

import nfpy.Calendar as Cal
from nfpy.Tools import Exceptions as Ex

from .Asset import Asset

_CALENDAR_TRANSFORM = {
    Cal.Frequency.B: 'C',
    Cal.Frequency.D: 'C',
    Cal.Frequency.M: 'BMS',
    Cal.Frequency.Y: 'BAS-JAN',
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
    def frequency(self) -> Cal.Frequency:
        return self._freq

    @frequency.setter
    def frequency(self, v: str) -> None:
        self._freq = Cal.Frequency(v)

    def load_dtype_in_df(
        self,
        dtype: str,
        start: Cal.TyDate | None = None,
        end: Cal.TyDate | None = None
    ) -> pd.Series:
        """ Load the datatype and merge into the dataframe. Takes care to load
            against the appropriate calendar frequency.
        """
        if self._s:
            freq = self._df.index.freqstr
            if freq != _CALENDAR_TRANSFORM[self._freq]:
                if self._freq == Cal.Frequency.M:
                    calendar = self._s.calendar.monthly_calendar
                elif self._freq == Cal.Frequency.Y:
                    calendar = self._s.calendar.yearly_calendar
                else:
                    msg = f'Rate(): calendar frequency not recognized for {self._uid}'
                    raise ValueError(msg)
                self._df = pd.DataFrame(index=calendar)

        dtype_code = self._dt.get(dtype)
        sr = self._load_dtype(dtype_code, start, end)

        # Adjust the values as they are  in annual percentage points
        adjust = False
        if dtype.split('.')[0] == 'Price':
            adjust = True
            sr *= .01

        if not sr.empty:
            if self._s:
                self._df = self._df.merge(
                    sr,
                    how='left',
                    left_index=True,
                    right_index=True
                )
                self._df.sort_index(inplace=True)
                sr = self._df[sr.name]
                # Replicate the adjustment inside the dataframe
                #if adjust:
                #    self._df.loc[:, dtype_code] *= .01
            else:
                start = start if start else sr.index[0].to_pydatetime()
                end = end if end else sr.index[-1].to_pydatetime()
                sr = sr.reindex(
                    Cal.create_calendar(
                        Cal.Frequency(self._freq),
                        end=end, start=start
                    )
                )
        return sr

    def _series_callback(
        self,
        dtype: str,
        start: Cal.TyDate | None = None,
        end: Cal.TyDate | None = None
    ) -> tuple[Callable, tuple]:
        """ Return the callback for converting series. """

        # Since rates do not pay dividends and do not split, we transform any
        # price or return request into a request for Raw data to avoid
        # duplications of operations and memory
        levels = dtype.split('.')
        if levels[0] in ('Price', 'Return', 'LogReturn'):
            dtype = dtype.replace(levels[1], 'Raw')
            return self.load_dtype_in_df, (dtype, start, end)

        # Error if datatype is not in the list
        else:
            msg = f'Rate(): datatype {dtype} for {self._uid} not recognized!'
            raise Ex.DatatypeError(msg)
