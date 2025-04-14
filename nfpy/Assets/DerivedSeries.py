#
# Equity class
# Base class for simple equity stock
#

import pandas as pd
from typing import Callable

import nfpy.Calendar as Cal

from .Asset import Asset

_CALENDAR_TRANSFORM = {
    Cal.Frequency.B: 'C',
    Cal.Frequency.D: 'C',
    Cal.Frequency.M: 'BMS',
    Cal.Frequency.Y: 'BAS-JAN',
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
    def frequency(self) -> Cal.Frequency:
        return self._freq

    @frequency.setter
    def frequency(self, v: str) -> None:
        self._freq = Cal.Frequency(v)

    @property
    def horizon(self) -> str:
        return self._horizon

    @horizon.setter
    def horizon(self, v: str) -> None:
        self._horizon = v

    def _series_callback(
        self,
        dtype: str,
        start: Cal.TyDate | None = None,
        end: Cal.TyDate | None = None
    ) -> tuple[Callable, tuple]:
        """ Return the callback for converting series. The callback must return
            a bool indicating success/failure.
        """
        return self.load_dtype_in_df, (dtype, start, end)

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
