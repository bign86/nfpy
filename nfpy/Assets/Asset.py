#
# Asset class
# Base class for a single asset
#

import abc
import cutils
from datetime import timedelta
import numpy as np
import pandas as pd
from typing import (Callable, Optional, TypeVar)

import nfpy.Calendar as Cal
import nfpy.Math as Math
from nfpy.Tools import (Exceptions as Ex, Utilities as Ut)

from .FinancialItem import FinancialItem


class Asset(FinancialItem):
    """ Base class to hold information on a single asset. """

    _TS_TABLE = ''
    _TS_ROLL_KEY_LIST = ()
    _DEF_PRICE_DTYPE = ''

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
        """ Loads the default price series for the asset. """
        return self.series(self._DEF_PRICE_DTYPE)

    @property
    def returns(self) -> pd.Series:
        """ Returns the default returns :) series for the asset.
            This function does not use Asset._calc_returns() to avoid going
            through the Asset.series() call.
        """
        code = self._dt.get(
            self._DEF_PRICE_DTYPE.replace('Price', 'Return')
        )
        if code not in self._df.columns:
            self._calc_returns(self._DEF_PRICE_DTYPE, code)

        return self._df[code]

    @property
    def log_returns(self) -> pd.Series:
        """ Returns the default log returns :) series for the asset.
            This function does not use Asset._calc_log_returns() to avoid going
            through the Asset.series() call.
        """
        code = self._dt.get(
            self._DEF_PRICE_DTYPE.replace('Price', 'LogReturn')
        )
        if code not in self._df.columns:
            self._calc_log_returns(self._DEF_PRICE_DTYPE, code)

        return self._df[code]

    @abc.abstractmethod
    def series_callback(self, dtype: str) -> tuple[Callable, tuple]:
        """ Return the callback for converting series. The callback must return
            a bool indicating success/failure.
        """

    def series(self, dtype: str) -> pd.Series:
        """ Return the requested series. If data are not found an empty series
            is returned unless the  callback throws an exception.

            Input:
                dtype [str]: datatype to load

            Output:
                res [pd.Series]: fetched series
        """
        code = self._dt.get(dtype)
        if code not in self._df.columns:
            call, args = self.series_callback(dtype)
            if not call(*args):
                return pd.Series(dtype=float)
        return self._df[code]

    @property
    def data(self) -> pd.DataFrame:
        """ Returns the full DataFrame for the asset. """
        return self._df

    def last_price(self, dt: Optional[Cal.TyDate] = None) \
            -> tuple[float, pd.Timestamp, int]:
        """ Returns the last valid daily raw close price at date.

            Input:
                dt [TyDate]: reference date (default: None)

            Output:
                v [float]: last valid price
                date [pd.Timestamp]: date of the last valid price
                idx [int]: index of the last valid price
        """
        prices = self.prices
        ts = prices.to_numpy()[:-self._cal.fft0]
        date = prices.index.to_numpy()[:-self._cal.fft0]

        pos = None
        if dt:
            dt = Cal.pd_2_np64(dt)
            pos = np.searchsorted(date, [dt])[0]

        pos = ts.shape[0] - 1 if pos is None else int(pos)
        idx = cutils.last_valid_index(ts, 0, 0, pos)

        return ts[idx], date[idx], idx

    def load_dtype(self, dtype: str) -> tuple[bool, pd.DataFrame]:
        """ Fetch from the DB a time series. The content of the column 'datatype'
            of the table containing the time series is given in input.

            Input:
                dt [str]: datatype to be loaded

            Output:
                success [bool]: success/failure
                df [pd.DataFrame]: fetched data

            Exceptions:
                KeyError: if datatype is not recognized in the decoding table
        """
        # this is needed inside the self._get_dati_for_query()
        dtype_code = self._dt.get(dtype)
        self.dtype = dtype_code

        # Take results and append to the unique dataframe indexed on the calendar
        data = [
            *self._get_dati_for_query(
                self.ts_table,
                rolling=self.ts_roll_key_list
            ),
            self._df.index[0].to_pydatetime() - timedelta(days=1),
            self._df.index[-1].to_pydatetime()
        ]
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
            return False, df
        else:
            df.rename(columns={"value": dtype_code}, inplace=True)
            return True, df

    def load_dtype_in_df(self, dtype: str) -> bool:
        """ Load the datatype and merge into the dataframe. """
        success, df = self.load_dtype(dtype)
        if success:
            self._df = self._df.merge(
                df, how='left',
                left_index=True,
                right_index=True
            )
            self._df.sort_index(inplace=True)
        return success

    def _calc_returns(self, dtype: str, code: Optional[int] = None) -> None:
        """ Calculates the returns from the series of the prices. """
        if code is None:
            code = self._dt.get(dtype.replace('Price', 'Return'))

        self._df[code] = cutils.ret_nans(
            self.series(dtype).to_numpy(),
            False
        )

    def _calc_log_returns(self, dtype: str, code: Optional[int] = None) -> None:
        """ Calculates the log returns from the series of the prices. """
        if code is None:
            code = self._dt.get(dtype.replace('Price', 'LogReturn'))

        self._df[code] = cutils.ret_nans(
            self.series(dtype).to_numpy(),
            True
        )

    # TODO: This has NOT been TESTED!!!
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

        df = self._df.reset_index(drop=False, inplace=False)
        data = df.values[:, [0, 3, 1, 2]]

        self._db.executemany(
            self._qb.insert(self.ts_table),
            map(tuple, data)
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

        end = self._cal.t0 if end is None else end
        slc = Math.search_trim_pos(
            _ret.index.to_numpy(),
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
        )
        return float(np.nanmean(_ret.to_numpy()[slc]))

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

        end = self._cal.t0 if end is None else end
        slc = Math.search_trim_pos(
            _ret.index.to_numpy(),
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end)
        )
        return float(np.nanstd(_ret.to_numpy()[slc]))

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
        _p = self.prices

        end = self._cal.t0 if end is None else end
        slc = Math.search_trim_pos(
            _p.index.to_numpy(),
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
        )
        return Math.tot_ret(
            _p.to_numpy()[slc],
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
        dt = r.index.to_numpy()

        end = self._cal.t0 if end is None else end
        slc = Math.search_trim_pos(
            dt,
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
        )
        p = Math.comp_ret(
            r.to_numpy()[slc],
            is_log=is_log
        )
        return pd.Series(p * base, index=dt[slc])


TyAsset = TypeVar('TyAsset', bound=Asset)
