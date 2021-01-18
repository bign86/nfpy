#
# Class Calendar
# Handle the calendars of the library
#

import datetime
import itertools
import warnings

import numpy as np
import pandas as pd
from typing import Union, Type, Sequence
from pandas.tseries.offsets import Day, BDay, Week, MonthBegin, \
    QuarterEnd, BQuarterEnd, BusinessDay, YearEnd, BYearEnd

from nfpy.Configuration import get_conf_glob
from nfpy.Tools import Singleton

_HOLYDAYS_MASK_ = ((1, 1), (5, 1), (6, 2), (8, 15), (12, 24), (12, 25), (12, 26))
_WEEKEND_MASK_INT_ = (5, 6)
_WEEKEND_MASK_STR_ = ('Sat', 'Sun')
_WEEK_MASK_INT_ = (0, 1, 2, 3, 4)
_WEEK_MASK_STR_ = ('Mon', 'Tue', 'Wen', 'Thu', 'Fri')

_FREQ_LABELS = {'D': ('D', Day),
                'B': ('B', BDay),
                'W': ('W', Week),
                'M': ('M', MonthBegin),
                'Q': ('Q', QuarterEnd),
                'BQ': ('BQ', BQuarterEnd),
                'A': ('A', YearEnd),
                'BA': ('BA', BYearEnd)}


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
        self._t0 = self.end - Day(offset)

        print(' * Calendar dates: {} -> {} : {}'.format(self._start.date(),
                                                        self._end.date(),
                                                        self._t0.date()))
        self._initialized = True

    def get_offset(self, freq: str) -> Type[BusinessDay]:
        """ Get a DateOffset object dependent on the frequency """
        return _FREQ_LABELS[freq][1]

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

    def is_in_calendar(self, dt: Union[str, pd.Timestamp]) -> bool:
        """ Check whether the given date is part of the calendar """
        warnings.warn("Deprecated! Please use the 'in' keyword directly!",
                      DeprecationWarning)
        return self.__contains__(dt)


def date_str_2_dt(dt: Union[Sequence[str], str], fmt: str = '%Y-%m-%d') \
        -> Union[Sequence, datetime.datetime]:
    warnings.warn("Deprecated! use date_2_datetime()!", DeprecationWarning)
    if isinstance(dt, str):
        return datetime.datetime.strptime(dt, fmt)
    elif isinstance(dt, Sequence):
        return [datetime.datetime.strptime(d, fmt) for d in dt]


def date_2_datetime(dt: Union[str, datetime.datetime, pd.Timestamp, Sequence],
                    fmt: str = '%Y-%m-%d') \
        -> Union[datetime.datetime, Sequence[datetime.datetime]]:
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


def today_(string: bool = True, fmt: str = '%Y-%m-%d') \
        -> Union[str, datetime.date, pd.Timestamp]:
    """ Return a string with today date """
    warnings.warn("Deprecated! Please use today()!", DeprecationWarning)
    today__ = datetime.date.today()
    if string:
        today__ = today__.strftime(fmt)
    return today__


def today(mode: str = 'str', fmt: str = '%Y-%m-%d') \
        -> Union[str, datetime.datetime, pd.Timestamp]:
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


def last_business_(offset: int = 1, string: bool = True, fmt: str = '%Y-%m-%d') \
        -> Union[str, datetime.date, pd.Timestamp]:
    """ Return the previous business day. """
    warnings.warn("Deprecated! Please use last_business()!", DeprecationWarning)
    lbd_ = (datetime.datetime.today() - BDay(offset)).date()
    if string:
        lbd_ = lbd_.strftime(fmt)
    return lbd_


def last_business(offset: int = 1, mode: str = 'str', fmt: str = '%Y-%m-%d') \
        -> Union[str, datetime.date, pd.Timestamp]:
    """ Return the previous business day. """
    lbd_ = (datetime.datetime.today() - BDay(offset)).date()
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
        -> Union[str, datetime.datetime]:
    """ Return a string with today date """
    now_ = datetime.datetime.now()
    if string:
        now_ = now_.strftime(fmt)
    return now_


def calc_holidays(start: pd.Timestamp, end: pd.Timestamp) -> np.array:
    """ Calculates an array of holidays """
    years = [y for y in range(start.year, end.year + 1)]
    length = len(_HOLYDAYS_MASK_) * len(years)
    holidays = np.empty(length, dtype=pd.Timestamp)

    def strpad(x):
        return str(x).zfill(2)

    for i, e in enumerate(itertools.product(years, _HOLYDAYS_MASK_)):
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


def get_calendar_glob() -> Calendar:
    """ Returns the pointer to the global DB """
    return Calendar()
