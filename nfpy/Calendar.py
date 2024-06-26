#
# Class Calendar
# Handle the calendars of the library
#

from copy import deepcopy
import datetime
from enum import Enum
import itertools

import numpy as np
import pandas as pd
from pandas.core.tools.datetimes import DatetimeScalar
import pandas.tseries.offsets as off
from typing import (Optional, Sequence, TypeVar, Union)

from nfpy.Tools import (Exceptions as Ex, Singleton)

#
# Types
#

TyDatetime = TypeVar('TyDatetime', bound=Union[
    str, pd.Timestamp, datetime.datetime, np.datetime64
])
TyDate = TypeVar('TyDate', bound=Union[str, datetime.date])
TyTime = Union[TyDate, TyDatetime, DatetimeScalar]
TyTimeSequence = Union[pd.DatetimeIndex, Sequence[TyTime]]


#
# Constants
#

_HOLIDAYS_MASK_ = ((1, 1), (5, 1), (12, 25))
_WEEKEND_MASK_INT_ = (5, 6)
_WEEKEND_MASK_STR_ = ('Sat', 'Sun')
_WEEK_MASK_INT_ = (0, 1, 2, 3, 4)
_WEEK_MASK_STR_ = ('Mon', 'Tue', 'Wen', 'Thu', 'Fri')

_OFFSET_LABELS = {
    'D': ('D', off.Day),
    'B': ('B', off.BDay),
    'W': ('W', off.Week),
    'MS': ('MS', off.MonthBegin),
    'BMS': ('AMS', off.BMonthBegin),
    'M': ('M', off.MonthEnd),
    'Q': ('Q', off.QuarterEnd),
    'BQ': ('BQ', off.BQuarterEnd),
    'AS': ('AS', off.YearBegin),
    'BAS': ('BAS', off.BYearBegin),
    'A': ('A', off.YearEnd),
    'Y': ('Y', off.YearEnd),
    'BA': ('BA', off.BYearEnd),
    'BY': ('BY', off.BYearEnd)
}

# Daily periods in larger time frames
DAYS_IN_1W = 7
DAYS_IN_1M = 30
DAYS_IN_1Q = 90
DAYS_IN_1Y = 365
DAYS = {'D': 1, 'W': DAYS_IN_1W, 'M': DAYS_IN_1M, 'Q': DAYS_IN_1Q, 'Y': DAYS_IN_1Y}

# Business daily periods in larger time frames
BDAYS_IN_1W = 5
BDAYS_IN_1M = 21
BDAYS_IN_1Q = 63
BDAYS_IN_1Y = 252
BDAYS = {'D': 1, 'B': 1, 'W': BDAYS_IN_1W, 'M': BDAYS_IN_1M, 'Q': BDAYS_IN_1Q, 'Y': BDAYS_IN_1Y}

# Weekly periods in larger time frames
WEEKS_IN_1M = 4
WEEKS_IN_1Q = 12
WEEKS_IN_1Y = 52
WEEKS = {'W': 1, 'M': WEEKS_IN_1M, 'Q': WEEKS_IN_1Q, 'Y': WEEKS_IN_1Y}

# Monthly periods in larger time frames
MONTHS_IN_1Q = 3
MONTHS_IN_1Y = 12
MONTHS = {'M': 1, 'Q': MONTHS_IN_1Q, 'Y': MONTHS_IN_1Y}

# Quarterly periods in larger time frames
QUARTERS_IN_1Y = 4
QUARTERS = {'Y': QUARTERS_IN_1Y}

# Frequency to dict
FREQ_2_D = {
    'D': DAYS,
    'B': BDAYS,
    'W': WEEKS,
    'M': MONTHS,
    'Q': QUARTERS,
}


class Frequency(Enum):
    D = 'D'
    W = 'W'
    M = 'M'
    Q = 'Q'
    Y = 'Y'


class Calendar(metaclass=Singleton):
    """ Universal calendar class to initialize dataframes. """

    def __init__(self):
        """ Creates a new calendar with given frequency. """
        self.fmt = None

        # Daily
        self._start = None
        self._end = None
        self._t0 = None
        self._fft0 = None
        self._xt0 = None
        self._calendar = None

        # Monthly
        self._t0m = None
        self._xt0m = None
        self._monthly_calendar = None

        # Yearly
        self._t0y = None
        self._xt0y = None
        self._yearly_calendar = None

        self._initialized = False

    @property
    def calendar(self) -> TyTimeSequence:
        """ Return the instantiated calendar if initialized else None. """
        if not self._initialized:
            return pd.DatetimeIndex([], Frequency.D.value)
        return self._calendar

    @property
    def monthly_calendar(self) -> TyTimeSequence:
        """ Return the instantiated monthly calendar if initialized else None. """
        if not self._initialized:
            return pd.DatetimeIndex([], Frequency.M.value)
        return self._monthly_calendar

    @property
    def yearly_calendar(self) -> TyTimeSequence:
        """ Return the instantiated yearly calendar if initialized else None. """
        if not self._initialized:
            return pd.DatetimeIndex([], Frequency.Y.value)
        return self._yearly_calendar

    # Starting (oldest) date in the calendar
    @property
    def start(self) -> pd.Timestamp:
        return self._start

    # Ending (latest) date in the calendar
    @property
    def end(self) -> pd.Timestamp:
        return self._end

    # Elaboration date, by default the most recent date for which a data point
    # is potentially available (last business date).
    @property
    def t0(self) -> pd.Timestamp:
        return self._t0

    # Offset between end and t0
    @property
    def fft0(self) -> int:
        return self._fft0

    # t0 index
    @property
    def xt0(self) -> int:
        return self._xt0

    @t0.setter
    def t0(self, v: pd.Timestamp) -> None:
        if (v < self._start) or (v > self._end):
            raise Ex.CalendarError(f'Calendar(): {v} outside the calendar range')

        self._t0 = v

        i = 1
        while self._t0 != self._calendar[-i]:
            i += 1
        self._fft0 = i
        self._xt0 = self._calendar.shape[0] - i

    # Monthly elaboration date
    @property
    def t0m(self) -> pd.Timestamp:
        return self._t0m

    # Offset between end and t0
    @property
    def xt0m(self) -> int:
        return self._xt0m

    @t0m.setter
    def t0m(self, v: pd.Timestamp) -> None:
        v = deepcopy(v)
        v.day = 1

        if (v < self._monthly_calendar[0]) or (v > self._monthly_calendar[-1]):
            raise Ex.CalendarError(f'Calendar(): {v} outside the monthly calendar range')

        self._t0m = v

        i = 1
        while self._t0m != self._monthly_calendar[-i]:
            i += 1
        self._xt0m = self._monthly_calendar.shape[0] - i

    # Yearly elaboration date
    @property
    def t0y(self) -> pd.Timestamp:
        return self._t0y

    # Offset between end and t0
    @property
    def xt0y(self) -> int:
        return self._xt0y

    @t0y.setter
    def t0y(self, v: pd.Timestamp) -> None:
        v = deepcopy(v)
        v.day = 1
        v.month = 1

        if (v < self._yearly_calendar[0]) or (v > self._yearly_calendar[-1]):
            raise Ex.CalendarError(f'Calendar(): {v} outside the yearly calendar range')

        self._t0y = v

        i = 1
        while self._t0y != self._yearly_calendar[-i]:
            i += 1
        self._xt0y = self._yearly_calendar.shape[0] - i

    @property
    def is_initialized(self) -> bool:
        return self.__bool__()

    @property
    def holidays(self) -> np.array:
        return calc_holidays(self.start, self.end)

    def __len__(self) -> int:
        return self._calendar.__len__()

    def __bool__(self) -> bool:
        return self._initialized

    def __contains__(self, dt: TyDate) -> bool:
        return pd.Timestamp(dt) in self._calendar

    def initialize(
            self,
            end: TyDate,
            start: Optional[TyDate] = None,
            periods: Optional[int] = None,
            monthly_start: Optional[TyDate] = None,
            monthly_periods: Optional[int] = None,
            yearly_start: Optional[TyDate] = None,
            yearly_periods: Optional[int] = None,
            fmt: str = '%Y-%m-%d'
    ) -> None:
        if self._initialized:
            return

        # Errors check
        if (start is None) & (periods is None):
            raise ValueError(
                f"Either one of daily starting time and number of periods (daily)"
                f" are required to initialize the calendar"
            )

        # Set the format string
        self.fmt = str(fmt)

        #
        # DAILY
        #
        # Set start and end dates
        if isinstance(end, pd.Timestamp):
            self._end = end
        else:
            self._end = pd.to_datetime(end, format=fmt)
        if not start:
            self._start = self.shift(self._end, -periods, 'B')
        else:
            if isinstance(start, pd.Timestamp):
                self._start = start
            else:
                self._start = pd.to_datetime(start, format=fmt)

        if self._end < self._start:
            self._start, self._end = self._end, self._start

        # Business daily calendar
        holidays = calc_holidays(self.start, self.end)
        self._calendar = pd.bdate_range(
            start=self._start, end=self._end, freq='C',
            normalize=True, holidays=holidays
        )

        # if self._end.dayofweek > 4:
        t0 = self.end - off.BDay(1)
        while t0 not in self._calendar:
            t0 -= off.BDay(1)
        # else:
        #     self._t0 = self.end
        # offset = max(0, self._end.weekday() - 4)
        # self._t0 = self.end - off.BDay(offset)

        i = 1
        while t0 != self._calendar[-i]:
            i += 1

        self._t0 = t0
        self._fft0 = i
        self._xt0 = self._calendar.shape[0] - i
        assert self._t0 == self._calendar[-self._fft0]
        assert self._t0 == self._calendar[self._xt0]

        #
        # MONTHLY
        #
        # Calculate start and end dates
        if monthly_start:
            if not isinstance(monthly_start, pd.Timestamp):
                monthly_start = pd.to_datetime(monthly_start, format=fmt)
            monthly_start = pd.Timestamp(monthly_start.asm8.astype('datetime64[M]'))
        else:
            if monthly_periods is not None:
                monthly_start = self._end - off.MonthBegin(monthly_periods)
            else:
                # n = 0 if self._start.day == 1 else 1
                # monthly_start = self._start - off.MonthBegin(n)
                monthly_start = pd.Timestamp(self._start.asm8.astype('datetime64[M]'))

        if monthly_start.month == self._start.month:
            if monthly_start.year == self._start.year:
                monthly_start -= off.MonthBegin(1)

        # Generate the monthly calendar
        self._monthly_calendar = pd.bdate_range(
            start=monthly_start, end=self._end, freq='MS'
        )
        self._t0m = self._monthly_calendar[-2]
        self._xt0m = self._monthly_calendar.shape[0] - 2

        #
        # YEARLY
        #
        # Calculate start and end dates
        if yearly_start:
            if not isinstance(yearly_start, pd.Timestamp):
                yearly_start = pd.to_datetime(yearly_start, format=fmt)
            yearly_start = pd.Timestamp(yearly_start.asm8.astype('datetime64[Y]'))
        else:
            if yearly_periods is not None:
                yearly_start = self._end - off.YearBegin(yearly_periods)
            else:
                # n = 0 if self._start.month == 1 else 1
                # yearly_start.day = self._start - off.YearBegin(n)
                yearly_start = pd.Timestamp(self._start.asm8.astype('datetime64[Y]'))

        if yearly_start.year == self._start.year:
            yearly_start -= off.YearBegin(1)

        # Generate the yearly calendar
        self._yearly_calendar = pd.bdate_range(
            start=yearly_start, end=self._end, freq='AS'
        )
        self._t0y = self._yearly_calendar[-2]
        self._xt0y = self._yearly_calendar.shape[0] - 2

        # Print the results
        print(' *** Calendar')
        print(
            f'   Daily:   {self._start.date()} -> {self._end.date()} | t0  = {self._t0.date()}\n'
            f'   Monthly: {self._monthly_calendar[0].date()} -> {self._monthly_calendar[-1].date()} | t0m = {self._monthly_calendar[self._xt0m].date()}\n'
            f'   Yearly:  {self._yearly_calendar[0].date()} -> {self._yearly_calendar[-1].date()} | t0y = {self._yearly_calendar[self._xt0y].date()}',
            end='\n\n'
        )

        self._initialized = True

    @staticmethod
    def get_offset(freq: Union[str, Frequency]) -> off:
        """ Get a DateOffset object dependent on the frequency """
        if isinstance(freq, Frequency):
            freq = freq.value
        return _OFFSET_LABELS[freq][1]

    def run_len(self, start: TyDatetime, end: TyDatetime) -> int:
        """ Returns the number of periods between the two datetimes in input. """
        s_idx = self._calendar.get_loc(start, method='nearest')
        e_idx = self._calendar.get_loc(end, method='nearest')
        return e_idx - s_idx

    def shift(self, dt: pd.Timestamp, n: int, freq: str,
              method: str = 'nearest') -> pd.Timestamp:
        """ Shift the <end> date by <n> periods forward or backwards.

            Input:
                dt [pd.Timestamp]: initial date
                n [int]: number of periods forward (if positive) or backwards
                        (if negative)
                freq [str]: frequency of the periods of the movement
                method [str]: method for finding the calendar date (default
                        'nearest')

            Output:
                target [pd.Timestamp]: target calendar date
        """
        if freq in ('B', 'D'):
            cal = self._calendar
        elif freq in ('M', 'BMS'):
            cal = self._monthly_calendar
        elif freq in ('Y', 'BAS'):
            cal = self._yearly_calendar
        else:
            raise ValueError(f'Calendar.shift(): frequency {freq} not recognized')

        offset = _OFFSET_LABELS[freq][1]
        shifted = dt + offset(int(n))
        target = cal.get_indexer([shifted], method=method)[0]
        return cal[target]


#
# Transformation functions
#

# From string
def str2pd(v, fmt: str) -> pd.Timestamp:
    return pd.to_datetime(v, format=fmt)


def str2np(v, fmt: str) -> np.datetime64:
    return pd.to_datetime(v, format=fmt).asm8


def str2dt(v, fmt: str) -> datetime.datetime:
    return datetime.datetime.strptime(v, fmt)


def str2d(v, fmt: str) -> datetime.date:
    return datetime.datetime.strptime(v, fmt).date()


# Pandas to numpy
def pd2np(dt: Optional[TyDate]) -> Optional[np.datetime64]:
    return dt.asm8 if isinstance(dt, pd.Timestamp) else dt


#
# Other functions
#

def today(mode: str = 'date', fmt: str = '%Y-%m-%d') -> TyDate:
    """ Return a string with today date. Per default returns a datetime.date
        object. The return type depends on the mode attribute:
          1. date (default): datetime.date
          2. str: string
          3. timestamp: pandas.Timestamp
          4. datetime: datetime.datetime
        This function does not include the time in the return object, only the
        date. Therefore, time is set to 00:00:00.000000. The format attribute is
        used only if applicable to the mode.
    """
    t = datetime.date.today()
    if mode == 'str':
        t = t.strftime(fmt)
    elif mode == 'timestamp':
        t = pd.to_datetime(t)
    elif mode == 'datetime':
        t = datetime.datetime(t.year, t.month, t.day)
    elif mode == 'date':
        pass
    else:
        raise ValueError(f'today(): Mode {mode} not recognized!')
    return t


def last_business(offset: int = 1, mode: str = 'str',
                  fmt: str = '%Y-%m-%d') -> TyDate:
    """ Return the previous business day. """
    lbd_ = (datetime.datetime.today() - off.BDay(offset)).date()
    if mode == 'str':
        lbd_ = lbd_.strftime(fmt)
    elif mode == 'timestamp':
        lbd_ = pd.to_datetime(lbd_)
    elif mode == 'datetime':
        pass
    else:
        raise ValueError(f'last_business(): Mode {mode} not recognized!')
    return lbd_


def ensure_business_day(dt: TyDate) -> TyDate:
    """ Return the previous business day if the given date is not a
        business day.
    """
    if not isinstance(dt, pd.Timestamp):
        dt = pd.Timestamp(dt)
    ldb = dt - 0 * off.BDay(1)
    if dt != ldb:
        dt = dt - off.BDay(1)
    return dt.date()


def now(mode: str = 'datetime', fmt: str = '%Y-%m-%d %H:%M') -> TyDate:
    """ Return a string with current date and time. By default, returns a
        datetime.datetime object. The return type depends on the mode attribute:
          1. datetime (default): datetime.datetime
          2. str: string
          3. timestamp: pandas.Timestamp
        The format attribute is
        used only if applicable to the mode.
    """
    if mode == 'timestamp':
        now_ = pd.Timestamp.now()
    elif mode == 'datetime':
        now_ = datetime.datetime.now()
    elif mode == 'str':
        now_ = datetime.datetime.now().strftime(fmt)
    else:
        raise ValueError(f'Mode {mode} in calendar.now() not recognized!')
    return now_


def calc_holidays(start: pd.Timestamp, end: pd.Timestamp) -> np.array:
    """ Calculates an array of holidays """
    years = [y for y in range(start.year, end.year + 1)]
    length = len(_HOLIDAYS_MASK_) * len(years)
    holidays = np.empty(length, dtype=pd.Timestamp)

    def strpad(x):
        return str(x).zfill(2)

    for i, e in enumerate(itertools.product(years, _HOLIDAYS_MASK_)):
        dt = '-'.join(map(strpad, [e[0], e[1][0], e[1][1]]))
        holidays[i] = pd.to_datetime(dt, format='%Y-%m-%d')

    return holidays


def shift(dt: pd.Timestamp, n: int, freq: str) -> pd.Timestamp:
    """ Shift the <dt> date by <n> periods forward or backwards.

        Input:
            dt [pd.Timestamp]: initial date
            n [int]: number of periods forward (if positive) or backwards
                    (if negative)
            freq [str]: frequency of the periods of the movement

        Output:
            target [pd.Timestamp]: target calendar date
    """
    offset = _OFFSET_LABELS[freq][1]
    return dt + offset(int(n))


def get_calendar_glob() -> Calendar:
    """ Returns the pointer to the global DB """
    return Calendar()
