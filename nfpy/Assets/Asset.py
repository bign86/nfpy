#
# Asset class
# Base class for a single asset
#

from typing import Union

import numpy as np
import pandas as pd

from nfpy.Assets.FinancialItem import FinancialItem
from nfpy.Financial.Returns import logret, ret, expct_ret, tot_ret
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Tools.Exceptions import MissingData, CalendarError
from nfpy.Tools.TSUtils import last_valid_index, trim_ts


class Asset(FinancialItem):
    """ Base class to hold information on a single asset """

    _TS_TABLE = ''
    _TS_ROLL_KEY_LIST = []

    def __init__(self, uid: str):
        super().__init__(uid)
        self._currency = None
        self.dtype = -1

        # takes the current calendar. It must have been initialized before!
        c = get_calendar_glob()
        if c:
            self._df = pd.DataFrame(index=c.calendar)
        else:
            raise CalendarError("Calendar not initialized as required!!!")
        self._cal = c

    @property
    def ts_table(self) -> str:
        return self._TS_TABLE

    @property
    def ts_roll_key_list(self) -> list:
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
            self.load_dtype("price")
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
        """ Returns the is_log returns for the asset. If not available calculates
            them from prices.
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

    def last_price(self, dt: pd.Timestamp = None) -> float:
        """ Returns the last valid price at date. """
        if not dt:
            dt = self._cal.t0

        p = self.prices
        ts, date = p.values, p.index.values
        ts, _ = trim_ts(ts, date, end=dt)
        idx = last_valid_index(ts)
        return ts[idx]

    def load_returns(self):
        self.load_dtype("return")

    def load_log_returns(self):
        self.load_dtype("logReturn")

    def load_dtype(self, dt: str):
        """ Fetch from the DB a time series. The content of the column 'datatype'
            of the table containing the time series is given in input.

            Input:
                dt [str]: datatype to be loaded

            Output:
                The method returns no value but the fetched data are merged in
                the main DataFrame accessible from the obj.data property. The new
                series will have the same name as the datatype.

            Exceptions:
                KeyError: if datatype is not recognized in the decoding table
                MissingData: if no data are found in the database
        """
        # this is needed inside the self._get_dati_for_query()
        self.dtype = self._dt.get(dt)

        # Take results and append to the unique dataframe indexed on the calendar
        q = self._qb.select(self.ts_table, fields=['date', 'value'],
                            rolling=self.ts_roll_key_list)
        data = self._get_dati_for_query(self.ts_table, rolling=self.ts_roll_key_list)
        self.dtype = -1

        cal = get_calendar_glob()
        data += (cal.start.to_pydatetime(), cal.end.to_pydatetime())

        conn = self._db.connection
        df = pd.read_sql_query(q, conn, index_col=['date'], params=data)
        if df.empty:
            raise MissingData("{} {} not found in the database!".format(self.uid, dt))

        df = df.rename(columns={"value": str(dt)})
        self._df = self._df.merge(df, how='left', left_index=True, right_index=True)
        self._df.sort_index(inplace=True)

    def calc_returns(self) -> pd.Series:
        """ Calculates the returns from the series of the prices. """
        return ret(self.prices)

    def calc_log_returns(self) -> pd.Series:
        """ Calculates the log returns from the series of the prices. """
        return logret(self.prices)

    def write_dtype(self, dt: str):
        """ Writes a time series to the DB. The content of the column 'datatype'
            of the table containing the time series is given in input.

            Input:
                dt [str]: datatype to be written

            Exceptions:
                KeyError: if datatype is not recognized in the decoding table
        """
        self.dtype = self._dt.get(dt)
        q_del = self._qb.delete(self.ts_table, fields=["uid", "dtype"])
        self._db.execute(q_del, (self.uid, self.dtype))

        # iterate over the index and extracting the dtype value
        def iter_df__():
            for t in self._df.itertuples(index=True):
                val = getattr(t, dt)
                yield (self.uid, self.dtype, t.date, val)

        q_ins = self._qb.insert(self.ts_table)
        self._db.executemany(q_ins, iter_df__)
        del self.dtype

    def expct_return(self, start: pd.Timestamp = None, end: pd.Timestamp = None,
                     is_log: bool = False) -> Union[float, pd.Series]:
        """ Expected return for the asset. It corresponds to the geometric mean
            for standard returns, and to the simple mean for log returns.

            Input:
                start [pd.Timestamp]: start date of the series (default: None)
                end [pd.Timestamp]: end date of the series excluded (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                epct [Union[float, pd.Series]]: expected value for returns
        """
        _ret = self.log_returns if is_log else self.returns
        ts, dt = _ret.values, _ret.index.values
        return expct_ret(ts, dt, start=start, end=end, is_log=is_log)

    def return_volatility(self, start: pd.Timestamp = None,
                          end: pd.Timestamp = None,
                          is_log: bool = False) -> float:
        _ret = self.log_returns if is_log else self.returns
        _ts, _ = trim_ts(_ret.values, _ret.index.values, start=start, end=end)
        return float(np.nanstd(_ts))

    def total_return(self, start: pd.Timestamp = None, end: pd.Timestamp = None,
                     is_log: bool = False) -> Union[float, pd.Series]:
        _ret = self.log_returns if is_log else self.returns
        ts, dt = _ret.values, _ret.index.values
        return tot_ret(ts, dt, start=start, end=end, is_log=is_log)
