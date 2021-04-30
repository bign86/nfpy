#
# Enums
# Types for the backtester
#

from enum import Enum


class Order(Enum):
    MKT = 0
    LMT = 1
    STP = 2
    TRL = 3


class Signal(Enum):
    BUY = 0
    SELL = 1
    CL_BUY = 2
    CL_SELL = 3
