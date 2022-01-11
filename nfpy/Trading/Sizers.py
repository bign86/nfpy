#
# Sizer
# Standard sizers
#

from math import floor
import numpy as np

from .BaseSizer import BaseSizer
from .Enums import Signal


class ConstantSizer(BaseSizer):
    """ Buy using a constant fraction of available cash and sell the same
        fraction of owned stock.
    """

    def __init__(self, size: float):
        super().__init__()
        self._c = max(min(1., float(size)), .0)

    def __call__(self, i: int, s: Signal) -> int:
        p = self._p[i]
        size = 0
        if s == Signal.BUY:
            size = int((self._ptf.cash * self._c) // p)
        elif s == Signal.SELL:
            size = int(floor(self._ptf.shares * self._c))
        return size


class ConstantSplitSizer(BaseSizer):
    """ Buy using a constant fraction of available cash and sell a different
        fraction of owned stock.
    """

    def __init__(self, buy: float, sell: float):
        super().__init__()
        self._b = max(min(1., float(buy)), .0)
        self._s = max(min(1., float(sell)), .0)

    def __call__(self, i: int, s: int) -> int:
        p = self._p[i]
        size = 0
        if s == 1:  # BUY
            size = int((self._ptf.cash * self._b) // p)
        elif s == -1:  # SELL
            size = int(floor(self._ptf.shares * self._s))
        return size
