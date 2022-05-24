#
# Base Indicator class
# Base class for indicators on time series.
#

from abc import (ABCMeta, abstractmethod)
import numpy as np
from typing import Union

from .Utils import (_check_len, _check_nans)


class BaseIndicator(metaclass=ABCMeta):
    _NAME = ''

    def __init__(self, ts: np.ndarray, is_bulk: bool):
        self._ts = ts
        self._is_bulk = is_bulk

        self._t = -1
        self._max_t = ts.shape[max(0, len(ts.shape) - 1)]

        _check_nans(ts)
        _check_len(ts, self.min_length + 1)

        if is_bulk:
            setattr(self, '_ind', self._ind_bulk)
        else:
            setattr(self, '_ind', self._ind_online)

    def start(self, t0: int) -> None:
        """ Start the indicator. In bulk mode, calculates the whole history.
            In online mode, precalculate in bulk mode up to t0. If t0 is before
            the minimum length of data to start the indicator, raise exception.
        """
        if t0 < self.min_length - 1:
            raise ValueError(f'Indicator {self._NAME}: t0={t0} < {self.min_length - 1}')
        elif t0 >= self._max_t:
            raise ValueError(f'Indicator {self._NAME}: t0={t0} >= {self._max_t}')

        self._t = t0
        self._bulk(t0)

    def __iter__(self):
        return self

    def __next__(self) -> Union[float, tuple]:
        """ Instruction to return next point. """
        self._t += 1
        if self._t >= self._max_t:
            raise StopIteration
        return self._ind()

    @abstractmethod
    def _bulk(self, t0: int) -> None:
        """ Function to calculate in bulk the history. Also used for starting
            the indicator in case online mode is used. Should also allocate the
            memory necessary to hold the indicator history. Note that in bulk
            mode t0 should not be needed.
        """

    @abstractmethod
    def get_indicator(self) -> dict:
        """ Returns the indicator full history in a dictionary. Mainly for
            debug purposes.
        """

    @abstractmethod
    def _ind_bulk(self) -> Union[float, tuple]:
        """ Returns the value of the indicator pre-calculated in bulk mode. """

    @abstractmethod
    def _ind_online(self) -> Union[float, tuple]:
        """ Calculates and returns the next indicator value. """

    @property
    @abstractmethod
    def min_length(self) -> int:
        """ Return the minimum amount of data required for a single evaluation
            of the indicator.
        """
