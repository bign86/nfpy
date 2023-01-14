#
# Base Strategy
# Base strategy structure
#

from abc import (ABCMeta, abstractmethod)
import numpy as np
from typing import (Optional, TypeVar)

import nfpy.Assets as Ast
import nfpy.Math as Math

from .Enums import (Order, Signal, SignalFlag)
from ..Indicators import TyIndicator


class BaseStrategy(metaclass=ABCMeta):
    """ Base class for strategies. The input may differ for every strategy but
        parameter names should be standardized as much as possible. The main
        output of a strategy are a series of buy/sell signals. Other outputs
        for analysis purposes may be recorded as well.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            npc [int]: number of days to go back in time for the check
    """

    _LABEL = ''
    NAME = ''
    DESCRIPTION = ''

    def __init__(self, asset: Ast.TyAsset, bulk: bool, npc: Optional[int] = 0):
        self._is_bulk = bulk
        self._dt = asset.prices.index.values

        self._ts = self._extract_ts(asset)

        self._num_p_conf = npc  # Periods to confirm a signal
        self._max_t = self._dt.shape[0]
        self._t = -1
        self._indicators = []
        self._unconfirmed = []

    def __iter__(self):
        return self

    def __next__(self) -> Optional[Signal]:
        self._t += 1
        if self._t < self._max_t:
            return self._confirm_signal(self._signal())
        else:
            raise StopIteration

    @property
    def dt(self) -> np.ndarray:
        return self._dt

    @property
    def ts(self) -> np.ndarray:
        return self._ts

    def _check_length(self) -> None:
        if len(self._ts.shape) == 1:
            useful_len = self._ts.shape[0] - self.min_length
        else:
            useful_len = self._ts.shape[1] - self.min_length

        if useful_len < 0:
            msg = f'{self._LABEL}: The series is {-useful_len} periods too short'
            raise ValueError(msg)

        if useful_len - Math.next_valid_index(self._ts) < 0:
            msg = f'{self._LABEL}: The are too many nans at the beginning'
            raise ValueError(msg)

    def _confirm_signal(self, new_sig: Optional[Signal]) -> Optional[Signal]:
        """ Does the bookkeeping of generated signals to confirmation. """
        signal = None
        if self._num_p_conf == 0:
            signal = new_sig
        else:
            if len(self._unconfirmed) > 0:
                delta = self._t - self._unconfirmed[0].t
                if delta >= self._num_p_conf:
                    signal = self._unconfirmed.pop(0)
            if new_sig:
                self._unconfirmed.append(new_sig)

        return signal

    @staticmethod
    def _extract_ts(asset: Ast.TyAsset) -> np.ndarray:
        """ Returns the 1D or 2D time series required to use the strategy. """
        return Math.ffill_cols(asset.prices.values)

    @property
    def max_t(self) -> int:
        """ Returns the max time series index. """
        return self._max_t

    @property
    def min_length(self) -> int:
        """ Return the minimum amount of data required for a single signal
            generation. This represents the minimum amount of data necessary to
            run the strategy.
        """
        n = max([i.min_length for i in self._indicators])
        return n + self._num_p_conf

    def raise_signal(self, flag: SignalFlag) -> Signal:
        return Signal(self._t, self._dt[self._t], flag)

    def _register_indicator(self, ind: list[TyIndicator]) -> None:
        self._indicators.extend(ind)

    def start(self, t0: Optional[int] = None) -> None:
        """ Call the start() method of each indicator. """
        t0 = self.min_length + 1 if t0 is None else t0
        self._t = t0
        for ind in self._indicators:
            ind.start(t0)

    @abstractmethod
    def check_order_validity(self, order: Order) -> tuple[str, int]:
        """ Return the validity of a pending order.
             - 'execute': if the order can be executed immediately
             - 'keep': if the order cannot be executed and remains pending
             - None: if the order is not valid anymore and should be cancelled
        """

    @abstractmethod
    def _signal(self) -> Optional[Signal]:
        """ Must return a tuple containing the generated signal in the form:
                <index, date, signal>
            If the bulk mode is used, the pre-calculate signal is returned. If
            the online mode is used, the indicator values are first returned,
            the controls made and the signal generated.
        """


TyStrategy = TypeVar('TyStrategy', bound=BaseStrategy)
