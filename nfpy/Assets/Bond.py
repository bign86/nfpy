#
# Bond class
# Base class for simple bonds
#

import warnings
from datetime import timedelta
from typing import Union

import numpy as np
import pandas as pd

from nfpy.Assets.Curve import Curve
from nfpy.Assets.Asset import Asset
from nfpy.Financial.BondMath import calc_ytm, calc_fv, \
    calc_duration, calc_convexity
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Tools.Constants import DAY_COUNT
from nfpy.Tools.Exceptions import MissingData, UnsupportedWarning, \
    ToBeImplementedWarning
from nfpy.Tools.TSUtils import last_valid_value


class AccConv(object):
    def __init__(self, s: str, d: int, y: int):
        self.name = s
        self.day = d
        self.year = y


class Bond(Asset):
    """ Base class for bonds. """

    _TYPE = 'Bond'
    _BASE_TABLE = 'Bond'
    _TS_TABLE = 'BondTS'
    _TS_ROLL_KEY_LIST = ['date']

    def __init__(self, uid: str):
        super().__init__(uid)
        self._maturity = None
        self._rate = None
        self._callable = None
        self._inception_date = None
        self._day_count = None
        self._cf = pd.DataFrame()

    @property
    def maturity(self) -> pd.Timestamp:
        return self._maturity

    @maturity.setter
    def maturity(self, v: str):
        self._maturity = pd.Timestamp(v)

    @property
    def rate_type(self) -> str:
        return self._rate

    @rate_type.setter
    def rate_type(self, v: str):
        self._rate = str(v)

    @property
    def callable(self) -> bool:
        return self._callable

    @callable.setter
    def callable(self, v: Union[str, bool]):
        self._callable = bool(v)

    @property
    def inception_date(self) -> pd.Timestamp:
        return self._inception_date

    @inception_date.setter
    def inception_date(self, v: str):
        self._inception_date = pd.Timestamp(v)

    @property
    def day_count(self) -> AccConv:
        return self._day_count

    @day_count.setter
    def day_count(self, s):
        d, y = DAY_COUNT[s]
        self._day_count = AccConv(s, d, y)

    @property
    def cf(self) -> pd.DataFrame:
        if self._cf.empty:
            self._load_cf()
        return self._cf

    def _load_cf(self):
        """ Load the cash flows from the database. """
        cols = ['date', 'dtype', 'value']
        dtype_list = ",".join([str(self._dt.get(t)) for t in ('cfP', 'cfC', 'cfS')])
        where = " dtype in (" + dtype_list + ")"
        q = self._qb.select(self.ts_table, fields=cols, keys=('uid',), where=where)

        r = self._db.execute(q, (self.uid,)).fetchall()
        if not r:
            raise MissingData('Cash flows not available for {}'.format(self.uid))

        cf = pd.DataFrame(data=r, columns=cols)
        cf['date'] = cf['date'].astype(np.datetime64)
        cf['period'] = (cf['date'] - get_calendar_glob().t0) / timedelta(days=365)
        cf = cf.set_index(['date'])
        cf.sort_index(inplace=True)

        self._cf = cf

    def ytm(self, date: Union[pd.Timestamp, pd.DatetimeIndex] = None,
            p0: float = None) -> pd.Series:
        """ Return the Yield To Maturity at the given date.

            Input:
                date Union[pd.Timestamp, pd.DatetimeIndex]: evaluation date
                    for discounting, by default the t0 of the calendar
                p0 [float]: market price of the bond, by default the price
                    available at t0 of the calendar

            Output:
                ytm [float]: Yield to Maturity
        """
        # Clean dates
        if date is None:
            date = get_calendar_glob().t0

        # Set prices series
        if p0 is None:
            p0 = self.prices.loc[date]

        try:
            p0 = p0.values
            date = date.values
        except AttributeError:
            date = np.array([date.asm8])

        v, date = calc_ytm(date, self._inception_date.asm8,
                           self._maturity.asm8, p0, self.cf['value'].values,
                           self.cf.index.values, self.cf['dtype'].values, .0)
        return pd.Series(data=v, index=date)

    def fv(self, rate: Union[float, Curve],
           date: Union[pd.Timestamp, pd.DatetimeIndex] = None) -> pd.Series:
        """ Return the Fair Value at the given date. A single rate or a curve may
            may be given to discount the cash flows.

            Input:
                r [Union[float, Curve]]: interest rate for discounting
                date Union[pd.Timestamp, pd.DatetimeIndex]: evaluation date
                    for discounting, by default the t0 of the calendar

            Output:
                fv [pd.Series]: Fair Value
        """
        # Handle input date
        if date is None:
            dates = get_calendar_glob().t0.asm8
        elif isinstance(date, pd.Timestamp):
            dates = date.asm8
        elif isinstance(date, pd.DatetimeIndex):
            dates = date.values
        else:
            raise TypeError('Wrong date type supplied to bond.fv()')

        v, dates = calc_fv(dates, self._inception_date.asm8,
                           self._maturity.asm8, .0, self.cf['value'].values,
                           self.cf.index.values, self.cf['dtype'].values, rate)
        return pd.Series(data=v, index=dates)

    def duration(self, date: Union[pd.Timestamp, pd.DatetimeIndex] = None) \
            -> pd.Series:
        """ Return the Duration at the given date.
        
            Input:
                date Union[pd.Timestamp, pd.DatetimeIndex]: evaluation date
                    for discounting, by default the t0 of the calendar
            
            Output:
                duration [pd.Series]: duration value
        """
        # quick exit for zero coupons
        if self.type == 'zero':
            return self.maturity - date

        # quick exit for floating rate bonds
        elif self.rate_type == 'float':
            warnings.warn("{}: duration not supported for floating rates"
                          .format(self.uid), UnsupportedWarning)
            return np.nan

        elif self.callable:
            warnings.warn("{}: callability not considered in duration"
                          .format(self.uid), ToBeImplementedWarning)

        # Handle missing input date
        if date is None:
            date = get_calendar_glob().t0

        # Set prices series
        p = self.prices.loc[date]
        try:
            p0 = p.values
        except AttributeError:
            if np.isnan(p):
                v = self.prices.values
                dt = self.prices.index.values
                p, _ = last_valid_value(v, dt, date.asm8)
            p0 = p

        # Transform to the right format prices and dates
        if isinstance(date, pd.Timestamp):
            dates = date.asm8
        elif isinstance(date, pd.DatetimeIndex):
            dates = date.values
        else:
            raise TypeError('Wrong date type supplied to bond.fv()')

        v, dates = calc_duration(dates, self._inception_date.asm8,
                                 self._maturity.asm8, p0, self.cf['value'].values,
                                 self.cf.index.values, self.cf['dtype'].values, .0)
        return pd.Series(data=v, index=dates)

    def convexity(self, date: Union[pd.Timestamp, pd.DatetimeIndex] = None) \
            -> pd.Series:
        """ Return the Convexity at the given date.
        
            Input:
                date Union[pd.Timestamp, pd.DatetimeIndex]: evaluation date
                    for discounting, by default the t0 of the calendar
            
            Output:
                convexity [pd.Series]: convexity value
        """
        # quick exit for floating rate bonds
        if self.rate_type == 'float':
            warnings.warn("{}: duration not supported for floating rates"
                          .format(self.uid), UnsupportedWarning)
            return np.nan

        elif self.callable:
            warnings.warn("{}: callability not considered in duration"
                          .format(self.uid), ToBeImplementedWarning)

        # Handle input date
        if date is None:
            date = get_calendar_glob().t0

        # Set prices series
        p = self.prices.loc[date]
        try:
            p0 = p.values
        except AttributeError:
            if np.isnan(p):
                v = self.prices.values
                dt = self.prices.index.values
                p, _ = last_valid_value(v, dt, date.asm8)
            p0 = p

        if isinstance(date, pd.Timestamp):
            dates = date.asm8
        elif isinstance(date, pd.DatetimeIndex):
            dates = date.values
        else:
            raise TypeError('Wrong date type supplied to bond.fv()')

        v, dates = calc_convexity(dates, self._inception_date.asm8,
                                  self._maturity.asm8, p0, self.cf['value'].values,
                                  self.cf.index.values, self.cf['dtype'].values, .0)
        return pd.Series(data=v, index=dates)
