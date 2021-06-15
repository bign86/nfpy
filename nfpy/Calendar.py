#
# Class Calendar
# Handle the calendars of the library
#

import datetime
import itertools

import numpy as np
import pandas as pd
import pandas.tseries.offsets as off
from typing import (Union, Sequence, TypeVar)

from nfpy.Tools import (get_conf_glob, Singleton)

TyDate = TypeVar('TyDate',
                 bound=Union[str, pd.Timestamp,
                             datetime.datetime, np.datetime64])
TyDateSequence = TypeVar('TyDateSequence',
                         bound=Union[pd.DatetimeIndex, Sequence])

_HOLIDAYS_MASK_ = ((1, 1), (5, 1), (6, 2), (8, 15), (12, 24), (12, 25), (12, 26))
_WEEKEND_MASK_INT_ = (5, 6)
_WEEKEND_MASK_STR_ = ('Sat', 'Sun')
_WEEK_MASK_INT_ = (0, 1, 2, 3, 4)
_WEEK_MASK_STR_ = ('Mon', 'Tue', 'Wen', 'Thu', 'Fri')

_FREQ_LABELS = {'D': ('D', off.Day),
                'B': ('B', off.BDay),
                'W': ('W', off.Week),
                'M': ('M', off.MonthBegin),
                'Q': ('Q', off.QuarterEnd),
                'BQ': ('BQ', off.BQuarterEnd),
                'A': ('A', off.YearEnd),
                'BA': ('BA', off.BYearEnd)}


# Calendar class
class Calendar(metaclass=Singleton):
    """ Universal calendar class to initialize dataframes. """

    def __init__(self):
        """ Creates a new calendar with given frequency. """
        self._frequency = None
        self.fmt = None
        self._start = None
        self._end = None
        self._t0 = None
        self._calendar = None
        self._initialized = False

    @property
    def calendar(self) -> pd.DatetimeIndex:
        """ Return the instantiated calendar if initialized else None. """
        if not self._initialized:
            return pd.DatetimeIndex([], self._frequency)
        return self._calendar

    # Starting (oldest) date in the calendar
    @property
    def start(self) -> pd.Timestamp:
        return self._start

    # Ending (latest) date in the calendar
    @property
    def end(self) -> pd.Timestamp:
        return self._end

    # Elaboration date, by default the most recent one.
    @property
    def t0(self) -> pd.Timestamp:
        return self._t0

    @t0.setter
    def t0(self, v: pd.Timestamp):
        self._t0 = v

    @property
    def is_initialized(self) -> bool:
        # return self._initialized
        return self.__bool__()

    @property
    def frequency(self) -> str:
        return self._frequency

    @property
    def holidays(self) -> np.array:
        return calc_holidays(self.start, self.end)

    def __len__(self) -> int:
        return self._calendar.__len__()

    def __bool__(self) -> bool:
        return self._initialized

    def __contains__(self, dt: Union[str, pd.Timestamp]) -> bool:
        return dt in self._calendar

    def initialize(self, end: Union[pd.Timestamp, str],
                   start: Union[pd.Timestamp, str] = None,
                   periods: int = None, fmt: str = '%Y-%m-%d'):
        if self._initialized:
            return

        # Errors check
        if (start is None) & (periods is None):
            raise ValueError('Either start time or number of periods are required')

        # Set the format string
        self.fmt = str(fmt)

        # Set start and end dates
        if isinstance(end, pd.Timestamp):
            self._end = end
        else:
            self._end = pd.to_datetime(end, format=fmt)
        if not start:
            self._start = self.shift(self._end, -periods)
        else:
            if isinstance(start, pd.Timestamp):
                self._start = start
            else:
                self._start = pd.to_datetime(start, format=fmt)

        if self._end < self._start:
            self._start, self._end = self._end, self._start

        # Get the calendar
        freq = get_conf_glob().calendar_frequency
        if freq == 'B':
            calcf = pd.bdate_range
            holidays = calc_holidays(self.start, self.end)
            f = 'C'
        else:
            calcf = pd.date_range
            holidays = None
            f = freq

        self._calendar = calcf(start=self._start, end=self._end,
                               freq=f, normalize=True, holidays=holidays)
        self._frequency = freq

        offset = max(0, self._end.weekday() - 4)
        # offset = min(2, max(0, (self.end.weekday() + 6) % 7 - 3))
        self._t0 = self.end - off.Day(offset)

        print(' * Calendar dates: {} -> {} : {}'
              .format(self._start.date(), self._end.date(), self._t0.date()),
              end='\n\n')
        self._initialized = True

    @staticmethod
    def get_offset(freq: str) -> off.BusinessDay:
        """ Get a DateOffset object dependent on the frequency """
        return _FREQ_LABELS[freq][1]

    def run_len(self, start: pd.Timestamp, end: pd.Timestamp) -> int:
        s_idx = self._calendar.get_loc(start, method='nearest')
        e_idx = self._calendar.get_loc(end, method='nearest')
        return e_idx - s_idx

    def shift(self, dt: pd.Timestamp, n: int, freq: str = None,
              method: str = 'nearest') -> pd.Timestamp:
        """ Shift the <end> date by <n> periods forward or backwards.

            Input:
                dt [pd.Timestamp]: initial date
                n [int]: number of periods forward (if positive) or backwards
                        (if negative)
                freq [str]: frequency of the periods of the movement (defaults
                        to the calendar frequency)
                method [str]: method for finding the calendar date (default
                        'nearest')

            Output:
                target [pd.Timestamp]: target calendar date
        """
        freq = self._frequency if freq is None else freq
        offset = _FREQ_LABELS[freq][1]
        shifted = dt + offset(int(n))
        target = self._calendar.get_loc(shifted, method=method)
        return self._calendar[target]


def date_2_datetime(dt: Union[TyDate, TyDateSequence],
                    fmt: str = '%Y-%m-%d') -> Union[TyDate, TyDateSequence]:
    if isinstance(dt, (list, tuple)):
        if isinstance(dt[0], str):
            dt = [datetime.datetime.strptime(d, fmt) for d in dt]
        elif isinstance(dt[0], pd.Timestamp):
            dt = [d.to_pydatetime() for d in dt]
        elif isinstance(dt[0], datetime.datetime):
            pass
        else:
            raise TypeError('Date type ({}) not accepted'.format(type(dt)))
        return dt
    else:
        if isinstance(dt, str):
            dt = datetime.datetime.strptime(dt, fmt)
        elif isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()
        elif isinstance(dt, datetime.datetime):
            pass
        else:
            raise TypeError('Date type ({}) not accepted'.format(type(dt)))
        return dt


def today(mode: str = 'str', fmt: str = '%Y-%m-%d') \
        -> TyDate:
    """ Return a string with today date """
    t = datetime.date.today()
    if mode == 'str':
        today__ = t.strftime(fmt)
    elif mode == 'timestamp':
        today__ = pd.to_datetime(t, format=fmt)
    elif mode in ('datetime', 'date'):
        today__ = datetime.datetime(t.year, t.month, t.day)
    else:
        raise ValueError('Mode {} not recognized!'.format(mode))
    return today__


def last_business(offset: int = 1, mode: str = 'str', fmt: str = '%Y-%m-%d') \
        -> TyDate:
    """ Return the previous business day. """
    lbd_ = (datetime.datetime.today() - off.BDay(offset)).date()
    if mode == 'str':
        lbd_ = lbd_.strftime(fmt)
    elif mode == 'timestamp':
        lbd_ = pd.to_datetime(lbd_, format=fmt)
    elif mode == 'datetime':
        pass
    else:
        raise ValueError('Mode {} not recognized!'.format(mode))
    return lbd_


def now(string: bool = True, fmt: str = '%Y-%m-%d %H:%M') \
        -> TyDate:
    """ Return a string with today date """
    now_ = datetime.datetime.now()
    if string:
        now_ = now_.strftime(fmt)
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
    offset = _FREQ_LABELS[freq][1]
    return dt + offset(int(n))


def pd_2_np64(dt: Union[np.datetime64, pd.Timestamp]) \
        -> Union[None, np.datetime64]:
    return dt.asm8 if isinstance(dt, pd.Timestamp) else dt


def get_calendar_glob() -> Calendar:
    """ Returns the pointer to the global DB """
    return Calendar()
