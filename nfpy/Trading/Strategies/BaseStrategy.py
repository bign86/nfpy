#
# Base Strategy
# Base strategy structure
#

from abc import (ABCMeta, abstractmethod)
import numpy as np
from typing import (Optional, TypeVar, Union)

import nfpy.Math as Math
import nfpy.Tools.Exceptions as Ex
import nfpy.Tools.Utilities as Ut


class StrategyResult(Ut.AttributizedDict):

    def __init__(self, idx: np.ndarray, dt: np.ndarray, sig: np.ndarray):
        super().__init__()
        self._indices = idx
        self._dates = dt
        self._signals = sig

    @property
    def indices(self) -> np.ndarray:
        return self._indices

    @property
    def dates(self) -> np.ndarray:
        return self._dates

    @property
    def signals(self) -> np.ndarray:
        return self._signals

    def __iter__(self):
        return StrategyResIterator(self).__iter__()


class StrategyResIterator(object):

    def __init__(self, strat: StrategyResult):
        self._idx = strat.indices
        self._dt = strat.dates
        self._s = strat.signals
        self._i = 0
        self._max = len(self._idx)

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        i = self._i
        if i < self._max:
            self._i += 1
            return (
                self._idx[i],
                self._dt[i],
                self._s[i],
            )
        else:
            raise StopIteration


class BaseStrategy(metaclass=ABCMeta):
    """ Base class for strategies. The input may differ for every strategy but
        parameter names should be standardized as much as possible. The main
        output of a strategy are a series of buy/sell signals. Other outputs
        for analysis purposes may be recorded as well.

        Input:
            dt [np.ndarray]: dates array
            p [np.ndarray]: values array
            npc [int]: number of days to go back in time for the check

        Output:
            result [StrategyResult]: strategy results
            data [Optional[dict]]: optional dictionary of debug data
    """

    _LABEL = ''
    NAME = ''
    DESCRIPTION = ''

    def __init__(self, dt: np.ndarray, ts: np.ndarray, npc: Optional[int] = 0):
        self._dt = dt

        if len(ts.shape) == 1:
            self._ts = ts[None, :]
        elif len(ts.shape) == 2:
            self._ts = ts
        else:
            msg = 'BaseStrategy(): time series must be either 1D or 2D arrays.'
            raise Ex.ShapeError(msg)

        # Number of periods to confirm a signal
        self._num_p_conf = npc

        # Variables for the on-line version of the strategy
        self._is_timer_set = False
        self._start_time = None
        self._curr_time = None
        self._i = None
        self._max_i = len(dt)

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        i = self._i
        if i < self._max_i:
            self._i += 1
            return self._f(i)
        else:
            raise StopIteration

    def _set_min_timer(self) -> None:
        """ Set the timer to start at the latest date that makes still possible
            to generate a single evaluation.
        """
        self._i = self._ts.shape[1] - self.min_length
        self._start_time = self._dt[self._i]
        self._is_timer_set = True

    def bulk_exec(self) -> StrategyResult:
        """ Apply the strategy to the whole time series in bulk. """
        self.check_length()
        return self._bulk()

    def check_length(self) -> None:
        useful_len = self._ts.shape[1] - self.min_length

        if useful_len < 0:
            msg = f'{self._LABEL}: The series is {-useful_len} periods too short'
            raise ValueError(msg)

        if useful_len - Math.next_valid_index(self._ts) < 0:
            msg = f'{self._LABEL}: The are too many nans at the beginning'
            raise ValueError(msg)

    @property
    def max_length(self) -> int:
        """ Returns the max time series index. """
        return self._max_i

    def set_timer(self, start: Optional[Union[int, np.datetime64]] = None) \
            -> None:
        """ Set the timer to <dt> for the period-by-period execution. """
        if isinstance(start, np.datetime64):
            self._i = max(
                np.searchsorted(self._dt, [start])[0],
                self.min_length
            )
        elif isinstance(start, int):
            self._i = max(start, self.min_length)
        else:
            raise TypeError('The <date> in Strategy.set_timer() is not correct')

        self._start_time = self._dt[self._i]
        self._is_timer_set = True

    def start(self) -> None:
        self.check_length()
        if not self._is_timer_set:
            self._set_min_timer()

        # We need to jumpstart the first part of the strategy to create the
        # first data point of the strategy

    @abstractmethod
    def _bulk(self) -> StrategyResult:
        """ Strategy bulk calculation function. """

    @abstractmethod
    def _f(self, i: int) -> Optional[tuple]:
        """ Strategy day-by-day calculation function. Must return a tuple
            containing the generated signal in the form:
                <index, date, signal>
            If no (new) signal is generated, None is returned instead.
        """

    @abstractmethod
    def check_order_validity(self, order: list) -> str:
        """ Return the validity of a pending order.
             - 'execute': if the order can be executed immediately
             - 'keep': if the order cannot be executed and remains pending
             - None: if the order is not valid anymore and should be cancelled
        """

    @property
    @abstractmethod
    def min_length(self) -> int:
        """ Return the minimum amount of data required for a single signal
            generation. This represents the minimum amount of data necessary to
            run the strategy.
        """


TyStrategy = TypeVar('TyStrategy', bound=BaseStrategy)
