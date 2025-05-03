#
# Index
# Class for indices
#

import cutils
import numpy as np
import pandas as pd
from typing import Callable

import nfpy.Calendar as Cal
from nfpy.Tools import (Exceptions as Ex)

from .Asset import Asset

_CALENDAR_TRANSFORM = {
    Cal.Frequency.B: 'C',
    Cal.Frequency.D: 'C',
    Cal.Frequency.M: 'BMS',
    Cal.Frequency.Y: 'BAS-JAN',
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
    def frequency(self) -> Cal.Frequency:
        return self._freq

    @frequency.setter
    def frequency(self, v: str) -> None:
        self._freq = Cal.Frequency(v)

    def _prices_loader(
        self,
        dtype: str,
        target: str,
        start: Cal.TyDate | None = None,
        end: Cal.TyDate | None = None
    ) -> pd.Series:
        """ Load the prices and, if missing, try sequentially to calculate them
            from other price data available in the database.
        """
        # If the price series is available, load it and exit
        sr = self.load_dtype_in_df(dtype, start, end)
        if not sr.empty:
            return sr

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

        to_exec = ()
        while len(seq) > 0:
            operation = seq.pop()
            other_dtype = dtype.replace(target, operation[0])
            other_code = self._dt.get(other_dtype)

            # If session and data is available, take the series
            if self._s:
                if other_code in self._df.columns:
                    to_exec = (other_code,) + operation[1:]
                    sr = self._df[other_code]
                    break

            # If so session or data not available, search for it
            sr = self.load_dtype_in_df(other_dtype, start, end)
            if not sr.empty:
                to_exec = (other_code,) + operation[1:]
                break
            else:
                continue

        # Raise exception if no prices are available in general
        if not to_exec:
            raise Ex.MissingData(f'Equity(): no prices found for {self._uid}')

        # Take the available series
        #other_values = self._df[to_exec[0]].values
        other_values = sr.values
        nan_mask = np.isnan(other_values)
        res = cutils.ffill(other_values.copy())

        # If we apply the adjustments
        if to_exec[2] == 1:

            # Build factor from dividends if needed
            if to_exec[1]:
                dividends = self.series('Dividend.SplitAdj.Regular', start, end)
                if not dividends.empty:
                    dividends = cutils.fillna(dividends.to_numpy().copy(), 0.)

                    div_adj = 1. - dividends[1:] / res[:-1]
                    div_adj = np.cumprod(div_adj[::-1])[::-1]
                    res[:-1] *= div_adj

        # If we remove the adjustments
        else:

            # Build factor from dividends if needed
            if to_exec[1]:
                dividends = self.series('Dividend.SplitAdj.Regular', start, end)
                if not dividends.empty:
                    dividends = cutils.fillna(dividends.to_numpy().copy(), 0.)

                    div_adj = res[:-1] / (res[:-1] + dividends[1:])
                    div_adj = np.cumprod(div_adj[::-1])[::-1]
                    res[:-1] /= div_adj

        res[nan_mask] = np.nan
        code = self._dt.get(dtype)

        # If session is available, insert the newly calculated series into the
        # dataframe putting back the original NaNs
        if self._s:
            self._df[code] = res
            out_sr = self._df[code]

        # Otherwise just create the out series index by the calendar of the
        # fetched data.
        else:
            out_sr = pd.Series(res, index=sr.index, name=code)

        return out_sr

    def _dividends_loader(
        self,
        dtype: str,
        target: str,
        start: Cal.TyDate | None = None,
        end: Cal.TyDate | None = None
    ) -> pd.Series:
        """ Dummy as we do not have these data. """
        return pd.Series([])

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
                if self._freq == Cal.Frequency.D:
                    calendar = self._s.calendar.calendar
                elif self._freq == Cal.Frequency.M:
                    calendar = self._s.calendar.monthly_calendar
                elif self._freq == Cal.Frequency.Y:
                    calendar = self._s.calendar.yearly_calendar
                else:
                    msg = f'Index(): calendar frequency not recognized for {self._uid}'
                    raise Ex.CalendarError(msg)
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
            return self._prices_loader, (dtype, data[1], start, end)

        # Dividends
        elif data[0] == 'Dividends':
            return self._dividends_loader, (dtype, data[1], start, end)

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
            msg = f'Index(): datatype {dtype} for {self._uid} not recognized!'
            raise Ex.DatatypeError(msg)
