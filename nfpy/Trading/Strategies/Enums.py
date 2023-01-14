#
# Enums
# Types for the backtester
#

from collections import namedtuple
from enum import Enum


class OrderType(Enum):
    MKT = 0
    LMT = 1
    STP = 2
    TRL = 3


class SignalFlag(Enum):
    BUY = 1
    SELL = -1
    CL_BUY = 2
    CL_SELL = -2


Signal = namedtuple('Signal', ['t', 'date', 'signal'])

Order = namedtuple('Order', ['type', 't', 'date', 'signal'])
