#
# Asset class
# Base class for a single asset
#

import numpy as np
import pandas as pd
from typing import (TypeVar, Optional)

import nfpy.Calendar as Cal
import nfpy.Math as Math
from nfpy.Tools import (Exceptions as Ex, Utilities as Ut)

from .FinancialItem import FinancialItem


class Asset(FinancialItem):
    """ Base class to hold information on a single asset. """

    _TS_TABLE = ''
    _TS_ROLL_KEY_LIST = ()

    def __init__(self, uid: str):
        super().__init__(uid)
        self._currency = None
        self.dtype = -1

        # takes the current calendar. It must have been initialized before!
        c = Cal.get_calendar_glob()
        if c:
            self._df = pd.DataFrame(index=c.calendar)
        else:
            raise Ex.CalendarError("Calendar not initialized as required!!!")
        self._cal = c
        # self._df = None
        # self._cal = Cal.get_calendar_glob()
        # self.new_df()

    # def reset_df(self):
    #     if self._cal is None:
    #         raise Ex.CalendarError("Calendar not initialized as required!!!")
    #     self._df = pd.DataFrame(index=self._cal.calendar)

    @property
    def ts_table(self) -> str:
        return self._TS_TABLE

    @property
    def ts_roll_key_list(self) -> tuple:
        return self._TS_ROLL_KEY_LIST

    @property
    def currency(self) -> str:
        return self._currency

    @currency.setter
    def currency(self, v: str):
        self._currency = v

    @property
    def prices(self) -> pd.Series:
        """ Loads the price series for the asset. """
        try:
            res = self._df["price"]
        except KeyError:
            self.load_dtype_in_df("price")
            res = self._df["price"]
        return res

    @property
    def returns(self) -> pd.Series:
        """ Returns the returns for the asset. If not available calculates
            them from prices.
        """
        try:
            res = self._df["return"]
        except KeyError:
            res = self.calc_returns()
            self._df["return"] = res
        return res

    @property
    def log_returns(self) -> pd.Series:
        """ Returns the is_log returns for the asset. If not available
            calculates them from prices.
        """
        try:
            res = self._df["logReturn"]
        except KeyError:
            res = self.calc_log_returns()
            self._df["logReturn"] = res
        return res

    @property
    def data(self) -> pd.DataFrame:
        """ Returns the full DataFrame for the asset. """
        return self._df

    def last_price(self, dt: Optional[Cal.TyDate] = None) -> tuple:
        """ Returns the last valid price at date.

            Input:
                dt [TyDate]: reference date (default: None)

            Output:
                v [flaot]: last valid price
                date [pd.Timestamp]: date of the last valid price
                idx [int]: index of the last valid price
        """
        ts = self.prices.values
        date = self.prices.index.values

        pos = None
        if dt:
            dt = Cal.pd_2_np64(dt)
            pos = np.searchsorted(date, [dt])[0]
        idx = Math.last_valid_index(ts, pos)

        return ts[idx], date[idx], idx

    def load_returns(self):
        self.load_dtype_in_df("return")

    def load_log_returns(self):
        self.load_dtype_in_df("logReturn")

    def load_dtype(self, dt: str) -> pd.DataFrame:
        """ Fetch from the DB a time series. The content of the column 'datatype'
            of the table containing the time series is given in input.

            Input:
                dt [str]: datatype to be loaded

            Output:
                The method returns no value but the fetched data are merged in
                the main DataFrame accessible from the obj.data property. The
                new series will have the same name as the datatype.

            Exceptions:
                KeyError: if datatype is not recognized in the decoding table
                MissingData: if no data are found in the database
        """
        # this is needed inside the self._get_dati_for_query()
        self.dtype = self._dt.get(dt)

        # Take results and append to the unique dataframe indexed on the calendar
        data = (
            *self._get_dati_for_query(
                self.ts_table,
                rolling=self.ts_roll_key_list
            ),
            self._cal.start.to_pydatetime(),
            self._cal.end.to_pydatetime()
        )
        self.dtype = -1

        try:
            df = pd.read_sql_query(
                self._qb.select(
                    self.ts_table,
                    fields=('date', 'value'),
                    rolling=self.ts_roll_key_list
                ),
                self._db.connection,
                index_col=['date'],
                params=data,
                parse_dates=['date']
            )
        except KeyError as ex:
            Ut.print_exc(ex)
            raise ex

        if df.empty:
            raise Ex.MissingData(f"{self.uid} {dt} not found in the database!")

        # df.index = pd.to_datetime(df.index)
        df.rename(columns={"value": str(dt)}, inplace=True)
        return df

    def load_dtype_in_df(self, dt: str) -> None:
        self._df = self._df.merge(
            self.load_dtype(dt),
            how='left',
            left_index=True,
            right_index=True
        )
        self._df.sort_index(inplace=True)

    def calc_returns(self) -> pd.Series:
        """ Calculates the returns from the series of the prices. """
        return self.prices \
            .pct_change(1, fill_method='pad')

    def calc_log_returns(self) -> pd.Series:
        """ Calculates the log returns from the series of the prices. """
        return self.prices \
            .pct_change(1, fill_method='pad') \
            .add(1.) \
            .log()

    def write_dtype(self, dt: str) -> None:
        """ Writes a time series to the DB. The content of the column 'datatype'
            of the table containing the time series is given in input.

            Input:
                dt [str]: datatype to be written

            Exceptions:
                KeyError: if datatype is not recognized in the decoding table
        """
        dtype = self._dt.get(dt)
        self._db.execute(
            self._qb.delete(
                self.ts_table,
                fields=("uid", "dtype")
            ),
            (self.uid, dtype)
        )

        # iterate over the index and extracting the dtype value
        def iter_df__():
            for t in self._df.itertuples(index=True):
                val = getattr(t, dt)
                yield self.uid, dtype, t.date, val

        self._db.executemany(
            self._qb.insert(self.ts_table),
            iter_df__
        )

    def expct_return(self, start: Optional[Cal.TyDate] = None,
                     end: Optional[Cal.TyDate] = None,
                     is_log: bool = False) -> float:
        """ Expected return for the asset. It corresponds to the geometric mean
            for standard returns, and to the simple mean for log returns.

            Input:
                start [TyDate]: start date of the series (default: None)
                end [TyDate]: end date of the series excluded (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                mean_ret [float]: expected value for returns
        """
        _ret = self.log_returns if is_log else self.returns
        slc = Math.search_trim_pos(
            _ret.index.values,
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
        )
        return Math.e_ret(
            _ret.values[slc],
            is_log=is_log
        )

    def return_volatility(self, start: Optional[Cal.TyDate] = None,
                          end: Optional[Cal.TyDate] = None,
                          is_log: bool = False) -> float:
        """ Volatility of asset returns.

            Input:
                start [TyDate]: start date of the series (default: None)
                end [TyDate]: end date of the series excluded (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                vola_ret [float]: expected value for returns
        """
        _ret = self.log_returns if is_log else self.returns
        slc = Math.search_trim_pos(
            _ret.index.values,
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end)
        )
        return float(np.nanstd(_ret.values[slc]))

    def total_return(self, start: Optional[Cal.TyDate] = None,
                     end: Optional[Cal.TyDate] = None,
                     is_log: bool = False) -> float:
        """ Total return over the period for the asset.

            Input:
                start [TyDate]: start date of the series (default: None)
                end [TyDate]: end date of the series excluded (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                tot_ret [float]: expected value for returns
        """
        _ret = self.log_returns if is_log else self.returns
        slc = Math.search_trim_pos(
            _ret.index.values,
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
        )
        return Math.tot_ret(
            _ret.values[slc],
            is_log=is_log
        )

    def performance(self, start: Optional[Cal.TyDate] = None,
                    end: Optional[Cal.TyDate] = None,
                    is_log: bool = False, base: float = 1.) -> pd.Series:
        """ Compounded returns of the asset from a base value.

            Input:
                start [TyDate]: start date of the series (default: None)
                end [TyDate]: end date of the series excluded (default: None)
                is_log [bool]: if True uses log returns (default: False)
                base [float]: base value (default: 1.)

            Output:
                perf [pd.Series]: Compounded returns series
        """
        r = self.returns
        dt = r.index.values
        slc = Math.search_trim_pos(
            dt,
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
        )
        p = Math.comp_ret(
            r.values[slc],
            is_log=is_log
        )
        return pd.Series(p * base, index=dt[slc])


TyAsset = TypeVar('TyAsset', bound=Asset)
