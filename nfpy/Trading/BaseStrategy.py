#
# Base Strategy
# Base strategy structure
#

from abc import ABCMeta, abstractmethod
from enum import Enum
import numpy as np
import os
from typing import (Dict, TypeVar, Tuple, Union)

import nfpy.IO as IO


class Signal(Enum):
    NONE = 0
    BUY = 1
    SELL = 2


class StrategyResult(object):

    def __init__(self, idx: np.ndarray, dt: np.ndarray = None,
                 sig: np.ndarray = None, strength: np.ndarray = None):
        self._indices = idx
        self._dates = dt
        self._signals = sig
        self._strength = strength

    @property
    def indices(self) -> np.ndarray:
        return self._indices

    @property
    def dates(self) -> np.ndarray:
        return self._dates

    @property
    def signals(self) -> np.ndarray:
        return self._signals

    @property
    def strength(self) -> np.ndarray:
        return self._strength

    def __iter__(self):
        return StrategyResIterator(self).__iter__()


class StrategyResIterator(object):

    def __init__(self, strat: StrategyResult):
        self._idx = strat.indices
        self._dt = strat.dates
        self._s = strat.signals
        self._st = strat.strength
        self._i = 0
        self._max = len(self._idx)

    def __next__(self):
        return self

    def __iter__(self) -> tuple:
        while self._i < self._max:
            i = self._i
            self._i += 1
            yield (self._idx[i], self._dt[i], self._s[i], self._st[i])


class BaseStrategy(metaclass=ABCMeta):
    """ Base class for strategies. The input may differ for every strategy but
        parameter names should be standardized as much as possible. The main
        output of a strategy are a series of buy/sell signals. Other outputs
        for analysis purposes may be recorded as well.
    """

    _LABEL = ''

    def __init__(self, full_out: bool = False):
        self._full_out = full_out

    def plot(self, label: str, f_dir: str = '', fmt: str = 'png'):
        sig = self._res['sig']

        buy = sig.signals > 0
        dt_buy = sig.dates[buy]
        dt_sell = sig.dates[~buy]
        idx_buy = sig.indices[buy]
        idx_sell = sig.indices[~buy]
        str_buy = 1000 * np.abs(sig.strength[buy])
        str_sell = 1000 * np.abs(sig.strength[~buy])

        plt = IO.Plotter()
        plt.lplot(0, self._dt, self._p, color='C0', linewidth=1.)
        plt.scatter(0, dt_buy, self._p[idx_buy], s=str_buy, color='C1', marker='o')
        plt.scatter(0, dt_sell, self._p[idx_sell], s=str_sell, color='C2', marker='o')
        plt.plot()

        if f_dir:
            img = '.'.join([label, self._LABEL, fmt])
            f_name = os.path.join(f_dir, img)
            plt.save(f_name, fmt)
        else:
            plt.show()

    def f(self, dt: np.ndarray, p: np.ndarray) \
            -> Union[StrategyResult, Tuple[StrategyResult, Dict]]:
        """ Strategy calculation function. """
        res = self._f(dt, p)
        if self._full_out:
            return res
        else:
            return res[0]

    @abstractmethod
    def _f(self, dt: np.ndarray, p: np.ndarray) -> Tuple[StrategyResult, Dict]:
        """ Strategy calculation function. """


TyStrategy = TypeVar('TyStrategy', bound=BaseStrategy)
