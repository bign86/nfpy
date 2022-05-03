#
# Level Breach Strategies
# Strategies based on breaching some given price level
#

import numpy as np
from typing import (Optional, Sequence)

from .. import Indicators as Ind
from .BaseStrategy import (BaseStrategy, StrategyResult)


class SRBreachStrategy(BaseStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the SMA and a sell signal when the price crosses below the SMA. The side
        of the SMA taken by the price is indicative of the trend.

        Input:
            dt [np.ndarray]: date series
            ts [np.ndarray]: price series
            w [int]: rolling window size
            check [Optional[int]]: number of periods to confirm the signal

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = 'SR_Breach'
    NAME = 'SR breach'
    DESCRIPTION = f""

    def __init__(self, dt: np.ndarray, ts: np.ndarray, w: Sequence[int],
                 depth: float, tol: float, vola: float, npc: Optional[int] = 0):
        super().__init__(dt, ts, npc)
        self._depth = depth
        self._tol = tol
        self._vola = vola
        self._w = w

    def _bulk(self) -> StrategyResult:
        ts = self._ts.reshape((self._ts.shape[1],))

        groups = []
        for w in self._w:
            span = round(w * self._depth)
            p = ts[-span:]
            dt = self._dt[-span:]
            groups.append(
                Ind.sr_smooth(dt, p, w, self._tol)
            )

        return StrategyResult(idx, dt, signals)

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._w + self._num_p_conf
