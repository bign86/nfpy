#
# Sizer
# Standard sizers
#

from math import floor

from .BaseSizer import BaseSizer
from .Enums import Signal


class ConstantSizer(BaseSizer):
    """ Sizer that returns a constant value. """

    def __init__(self, c: float):
        super().__init__()
        self._c = max(min(1., float(c)), .0)

    def __call__(self, i: int, s: Signal) -> int:
        p = self._p[i]
        if s == Signal.BUY:
            return int((self._ptf.cash * self._c) // p)
        else:
            return int(floor(self._ptf.shares * self._c))
