#
# Base Strategy
# Base strategy structure
#

from abc import (ABCMeta, abstractmethod)
import numpy as np
from typing import (Optional, TypeVar, Union)

import nfpy.Financial.Math as Math
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

    def __next__(self) -> []:
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

    def __init__(self, dt: np.ndarray, p: np.ndarray, npc: Optional[int] = 0):
        self._dt = dt
        self._p = p

        # Number of periods to confirm a signal
        self._num_p_conf = npc

        # Variables for the on-line version of the strategy
        self._is_timer_set = False
        self._start_time = None
        self._curr_time = None
        self._i = None
        self._max_i = len(dt)

    @property
    @abstractmethod
    def min_length(self) -> int:
        """ Return the minimum amount of data required for a single signal
            generation. This represents the minumum amount of data necessary to
            run the strategy.
        """

    def check_length(self) -> None:
        useful_length = self._p.shape[0] - self.min_length

        if useful_length < 0:
            msg = f'{self._LABEL}: The series is {-useful_length} periods too short'
            raise ValueError(msg)

        if useful_length - Math.next_valid_index(self._p) < 0:
            msg = f'{self._LABEL}: The are too many nans at the beginning'
            raise ValueError(msg)

    # Apply the strategy day-by-day
    def set_timer(self, start: Union[int, np.datetime64] = None) -> None:
        """ Set the timer to <dt> for the day-by-day execution. """
        if isinstance(start, np.datetime64):
            start = max(
                np.searchsorted(self._dt, [start])[0],
                self.min_length
            )
        elif isinstance(start, int):
            start = max(start, self.min_length)
        else:
            raise TypeError('The <date> in Strategy.set_timer() is not correct')

        self._i = max(start, self.min_length)
        self._start_time = self._dt[self._i]
        self._is_timer_set = True

    def _set_min_timer(self) -> None:
        """ Set the timer to start at the latest date that makes still possible
            to generate a single evaluation.
        """
        self._i = self._p.shape[0] - self.min_length
        self._start_time = self._dt[self._i]
        self._is_timer_set = True

    def start(self) -> None:
        self.check_length()
        if not self._is_timer_set:
            self._set_min_timer()

        # We need to headstart the first part of the strategy to create the
        # first data point of the strategy

    def __iter__(self):
        return self

    def __next__(self) -> []:
        i = self._i
        if i < self._max_i:
            self._i += 1
            return self._f(i)
        else:
            raise StopIteration

    @abstractmethod
    def _f(self, i: int) -> []:
        """ Strategy day-by-day calculation function. """

    # Apply the strategy in bulk
    def bulk_exec(self) -> StrategyResult:
        """ Apply the strategy to the whole time series in bulk. """
        self.check_length()
        return self._bulk()

    @abstractmethod
    def _bulk(self) -> StrategyResult:
        """ Strategy bulk calculation function. """

    # def plot(self, label: str, f_dir: str = '', fmt: str = 'png'):
    #     sig = self._res['sig']
    #
    #     buy = sig.signals > 0
    #     dt_buy = sig.dates[buy]
    #     dt_sell = sig.dates[~buy]
    #     idx_buy = sig.indices[buy]
    #     idx_sell = sig.indices[~buy]
    #     str_buy = 1000 * np.abs(sig.strength[buy])
    #     str_sell = 1000 * np.abs(sig.strength[~buy])
    #
    #     plt = IO.Plotter()
    #     plt.lplot(0, self._dt, self._p, color='C0', linewidth=1.)
    #     plt.scatter(0, dt_buy, self._p[idx_buy], s=str_buy, color='C1', marker='o')
    #     plt.scatter(0, dt_sell, self._p[idx_sell], s=str_sell, color='C2', marker='o')
    #     plt.plot()
    #
    #     if f_dir:
    #         img = '.'.join([label, self._LABEL, fmt])
    #         f_name = os.path.join(f_dir, img)
    #         plt.save(f_name, fmt)
    #     else:
    #         plt.show()


TyStrategy = TypeVar('TyStrategy', bound=BaseStrategy)
