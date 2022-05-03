#
# Breakout Strategies functions
# Strategies based on breakouts from channels or oscillators
#

from abc import abstractmethod
import numpy as np
from typing import (Callable, Optional, Sequence)

from .. import Indicators as Ind
from .BaseStrategy import (BaseStrategy, StrategyResult)


class IndicatorBreakout(BaseStrategy):
    """ Generates a buy signal when the indicator crosses above the upper
        threshold and a sell signal when it crosses below the lower threshold.

        Input:
            dt [np.ndarray]: date series
            ts [np.ndarray]: price series
            indicator [Callable]: indicator function
            params [Sequence]: parameters passed to the indicator
            threshold [Sequence]: upper and lower indicator thresholds
            npc [int]: number of days to go back in time for the check

        Output:
            signals [StrategyResult]: generated signals
    """
    _LABEL = 'Indicator_Breakout'
    NAME = 'Indicator Breakout'
    DESCRIPTION = f""

    def __init__(self, dt: np.ndarray, ts: np.ndarray, indicator: Callable,
                 params: Sequence, threshold: Optional[tuple[float]],
                 npc: Optional[int] = 0):
        super().__init__(dt, ts, npc)
        self._ind_f = indicator
        self._thr = threshold
        self._params = params

    def _bulk(self) -> StrategyResult:
        buy_cross, sell_cross = self._indicator_check()
        buy_cross[buy_cross == -1] = 0
        sell_cross[sell_cross == 1] = 0

        dead_time = sum(*self._params)
        buy_cross[:dead_time - 1] = 0

        cross = buy_cross & sell_cross
        mask = cross != 0

        idx = np.nonzero(mask)[0] + 1
        dt = self._dt[1:][mask]
        signals = cross[mask]

        return StrategyResult(idx, dt, signals)

    def _f(self, i: int) -> tuple:
        return -999,

    @abstractmethod
    def _indicator_check(self) -> tuple[np.ndarray, np.ndarray]:
        pass

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return sum(*self._params) + self._num_p_conf


class OscillatorBreakout(IndicatorBreakout):

    def _indicator_check(self) -> tuple[np.ndarray, np.ndarray]:
        sig = self._ind_f(self._ts, *self._params)
        return (
            np.diff(np.where(sig > self._thr, 1, 0)),
            np.diff(np.where(sig < self._thr, -1, 0))
        )


class ChannelBreakout(IndicatorBreakout):

    def _indicator_check(self) -> tuple[np.ndarray, np.ndarray]:
        high, low = self._ind_f(self._ts, *self._params)[:2]
        return (
            np.diff(np.where(high > self._thr, 1, 0)),
            np.diff(np.where(low < self._thr, -1, 0))
        )


class CCIBreakout(OscillatorBreakout):
    _LABEL = 'CCI_Breakout'
    NAME = 'CCI Channel Breakout'
    DESCRIPTION = f""

    def __init__(self, dt: np.ndarray, ts: np.ndarray, w: int,
                 threshold: Optional[tuple[float]] = (100., -100.),
                 npc: Optional[int] = 0):
        super().__init__(dt, ts, Ind.cci, (w,), threshold, npc)


class DonchianBreakout(BaseStrategy):
    _LABEL = 'Donchian_Breakout'
    NAME = 'Donchian Breakout'
    DESCRIPTION = f""

    def __init__(self, dt: np.ndarray, p: np.ndarray, w: int,
                 threshold: Optional[tuple[float]] = (.2, .8),
                 npc: Optional[int] = 0):
        super().__init__(dt, p, npc)
        self._thr = threshold
        self._w = w
