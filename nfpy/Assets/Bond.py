#
# Equity class
# Base class for simple equity stock
#

import warnings
from datetime import timedelta, datetime
from typing import Union, Iterable

import numpy as np
import pandas as pd

from nfpy.Assets.Curve import Curve
from nfpy.Assets.Asset import Asset
from nfpy.Financial.BondMath import ytm, duration, convexity
from nfpy.Financial.EquityMath import fv
from nfpy.Handlers.Calendar import get_calendar_glob, date_str_2_dt
from nfpy.Tools.Constants import DAY_COUNT
from nfpy.Tools.Exceptions import MissingData, UnsupportedWarning, \
    ToBeImplementedWarning, IsNoneError


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

    def _prepare_cashflow(self, date: pd.Timestamp = None, p0: float = None) -> tuple:
        """ Auxilliary function to prepare the date, p0 and cash flow for the
            calculation of duration and convexity.
        """
        # No date given, we use the calendar t0
        if not date:
            date = get_calendar_glob().t0
            pf = self.cf[self.cf['period'] > 0.]

        # Date is given
        else:
            # Error if above maturity
            if date >= self.maturity:
                raise ValueError('Maturity for {} is in the past'.format(self.uid))
            if date < self.inception_date:
                raise ValueError('Inception date for {} is in the future'.format(self.uid))
            # Recalculate periods on the new date
            else:
                pf = self.cf[self.cf.index > date].copy(deep=True)
                pf['period'] = (pf.index - date) / timedelta(days=365)

        # Check price value
        if p0 is None:
            p0 = float(self.prices.loc[date])
            if np.isnan(p0):
                raise IsNoneError('p0 is np.nan')

        # Take into account accrued interest
        # Position of the oldest future cash flow
        start_idx = self.cf.index.get_loc(pf.index[0])

        if start_idx == 0:
            # We are accruing since inception date
            accrue_date = self.inception_date
        else:
            # We are accruing since last coupon
            accrue_date = self.cf.index[start_idx - 1]

        # Adjustment to the first cash flow due to accrued interest
        accrue_per = (pf.index[0] - date) / timedelta(days=365)
        delta_time = (pf.index[0] - accrue_date) / timedelta(days=365)
        pf.loc[pf.index[0], 'value'] *= accrue_per / delta_time

        pf = pf[['period', 'value']].values
        return date, p0, pf

    @staticmethod
    def _date_stream(date: Union[Iterable, datetime, pd.Timestamp, pd.DatetimeIndex]) \
            -> tuple:
        """ Takes as input one or a list of dates in datetime and ensures that
            dates are converted into datetime. In output dates are always in a
            list, even if a single date is passed.

            Input:
                date [Union[Iterable[...], datetime, pd.Timestamp,
                    pd.DatetimeIndex]: input

            Output:
                stream [Iterable[pd.Datetime]]: output dates list
                len [int]: length of the list
        """
        if date is None:
            return [get_calendar_glob().t0], 1

        if not isinstance(date, Iterable) or isinstance(date, str):
            date = [date]

        _stream = []
        for d in date:
            if isinstance(d, str):
                d = date_str_2_dt(d)
            _stream.append(d)

        return _stream, len(_stream)

    def fv(self, r: Union[float, Curve], spread: Union[float, Curve] = 0.,
           date: Union[datetime, pd.Timestamp, pd.DatetimeIndex] = None) -> pd.Series:
        """ Return the Fair Value at the given date. A single rate or a curve may
            may be given to discount the cash flows.

            Input:
                r [Union[float, Curve]]: interest rate for discounting
                spread [Union[float, str]]: spread applied to the rate (default 0%)
                date Union[pd.Timestamp, pd.DatetimeIndex]: evaluation date
                    for discounting, by default the t0 of the calendar

            Output:
                fv [float]: Fair Value
        """
        # Handle input date
        date, n = self._date_stream(date)

        # Calculate spread
        if spread is None:
            raise ValueError('Spread cannot be None')
        elif spread == 'ytm':
            spread = self.ytm(date[-1])
        else:
            spread = float(spread)

        # Calculated the array of rates and dates adding spread if required
        v = np.zeros(n)
        for i, dt in enumerate(date):
            # Find the interest rate
            if isinstance(r, Curve):
                ts = r.term_struct(date)
                r_ = ts.values[0, :] + spread
                t_ = ts.columns
            else:
                r_ = r + spread
                t_ = None

            try:
                _, _, pf = self._prepare_cashflow(dt)
                v[i] = fv(pf, r_, t_)
            except IsNoneError:
                v[i] = pd.np.nan
        return pd.Series(data=v, index=date)

    def ytm(self, date: Union[datetime, pd.Timestamp, pd.DatetimeIndex] = None,
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
        date, n = self._date_stream(date)

        v = np.zeros(n)
        for i, dt in enumerate(date):
            try:
                _, p, pf = self._prepare_cashflow(dt, p0)
                v[i] = ytm(pf, p)
            except IsNoneError:
                v[i] = pd.np.nan
        return pd.Series(data=v, index=date)

    def duration(self, date: Union[datetime, pd.Timestamp, pd.DatetimeIndex] = None) \
            -> pd.Series:
        """ Return the Duration at the given date.
        
            Input:
                date Union[pd.Timestamp, pd.DatetimeIndex]: evaluation date
                    for discounting, by default the t0 of the calendar
            
            Output:
                duration [float]: duration value
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

        date, n = self._date_stream(date)

        v = np.zeros(n)
        for i, dt in enumerate(date):
            try:
                _, p, pf = self._prepare_cashflow(dt, None)
                v[i] = duration(pf, p)
            except IsNoneError:
                v[i] = pd.np.nan
        return pd.Series(data=v, index=date)

    def convexity(self, date: Union[datetime, pd.Timestamp, pd.DatetimeIndex] = None) \
            -> pd.Series:
        """ Return the Convexity at the given date.
        
            Input:
                date Union[pd.Timestamp, pd.DatetimeIndex]: evaluation date
                    for discounting, by default the t0 of the calendar
            
            Output:
                convexity [float]: convexity value
        """
        # quick exit for floating rate bonds
        if self.rate_type == 'float':
            warnings.warn("{}: duration not supported for floating rates"
                          .format(self.uid), UnsupportedWarning)
            return np.nan

        elif self.callable:
            warnings.warn("{}: callability not considered in duration"
                          .format(self.uid), ToBeImplementedWarning)

        date, n = self._date_stream(date)

        v = np.zeros(n)
        for i, dt in enumerate(date):
            try:
                _, p, pf = self._prepare_cashflow(dt, None)
                v[i] = convexity(pf, p)
            except IsNoneError:
                v[i] = pd.np.nan
        return pd.Series(data=v, index=date)
