#
# Base Sizer
# Base class for sizers
#

from abc import ABCMeta, abstractmethod
from typing import TypeVar


class BaseSizer(metaclass=ABCMeta):
    """ Baseclass for all sizers, determines the trade size. """

    @abstractmethod
    def s(self) -> float:
        """ Function returning the size of the trade:
              * for a BUY: the percentage of available funds to be committed
              * for a SELL: the percentage of owned assets to be converted to cash
        """


TySizer = TypeVar('TySizer', bound=BaseSizer)
