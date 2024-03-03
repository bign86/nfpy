#
# Base Indicator class
# Base class for indicators on time series.
#

from abc import (ABCMeta, abstractmethod)
import numpy as np
from typing import (Optional, TypeVar, Union)

from .Utils import (_check_len, _check_nans)


class BaseIndicator(metaclass=ABCMeta):
    _NAME = ''

    def __init__(self, ts: np.ndarray, is_bulk: bool, dims: set):
        self._ts = ts
        self._is_bulk = is_bulk

        self._t = -1
        self._max_t = ts.shape[ts.ndim - 1]

        self._check_dims(ts, dims)
        _check_nans(ts)
        _check_len(ts, self.min_length)  # + 1)

        if is_bulk:
            setattr(self, '_ind', self._ind_bulk)
        else:
            setattr(self, '_ind', self._ind_online)

    def _check_dims(self, _ts: np.ndarray, _dims: set):
        """ Check the dimensionality of the array is possible. """
        _ERR = f'Indicator {self._NAME}: ts shape={_ts.shape} not conformant to {_dims}'
        if _ts.ndim == 1:
            if 1 not in _dims:
                raise ValueError(_ERR)
        elif _ts.ndim == 2:
            if _ts.shape[0] not in _dims:
                raise ValueError(_ERR)
        else:
            raise ValueError(_ERR)

    def start(self, t0: Optional[int] = None) -> None:
        """ Start the indicator. In bulk mode, calculates the whole history.
            In online mode, precalculate in bulk mode up to t0. If t0 is before
            the minimum length of data to start the indicator, raise exception.

            t0 represents the first time step for which we want to generate a
            data point. The minimum acceptable is <min_length> that is also the
            default, the maximum is the length in period of the series max_t.
        """
        if t0 is None:
            t0 = self.min_length
        elif t0 < self.min_length:
            raise ValueError(f'Indicator {self._NAME}: t0={t0} < {self.min_length}')
        elif t0 > self._max_t:
            raise ValueError(f'Indicator {self._NAME}: t0={t0} > {self._max_t}')

        # We go to t0 - 1 because we need the INDEX, not the step number, of
        # the PREVIOUS element. Hence, 1 before.
        self._t = t0 - 1
        self._bulk(t0 - 1)

    def __iter__(self):
        return self

    def __next__(self) -> Union[int, tuple]:
        """ Instruction to return next point. """
        self._t += 1
        if self._t >= self._max_t:
            raise StopIteration
        return self._t, self._ind()
        # return self._ind()

    @abstractmethod
    def _bulk(self, t0: int) -> None:
        """ Function to calculate in bulk the history. Also used for starting
            the indicator in case online mode is used. Should also allocate the
            memory necessary to hold the indicator history. Note that in bulk
            mode t0 is ignored.
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


TyIndicator = TypeVar('TyIndicator', bound=BaseIndicator)
