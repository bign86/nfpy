#
# Base Sizer
# Base class for sizers
#

from abc import ABCMeta, abstractmethod
import numpy as np
from typing import TypeVar

from .Strategies import Signal


class BaseSizer(metaclass=ABCMeta):
    """ Baseclass for all sizers, determines the trade size. """

    def __init__(self):
        self._p = None
        self._ptf = None

    def set(self, p: np.ndarray, ptf) -> None:
        self._p = p
        self._ptf = ptf

    def clean(self) -> None:
        self._p = None
        self._ptf = None

    @abstractmethod
    def __call__(self, i: int, s: Signal) -> int:
        """ Returns the size of the trade:
              * for a BUY: the percentage of available funds to be committed
              * for a SELL: the percentage of owned assets to be cashed out
        """


TySizer = TypeVar('TySizer', bound=BaseSizer)
