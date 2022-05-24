#
# Base Strategy
# Base strategy structure
#

from abc import (ABCMeta, abstractmethod)
import numpy as np
from typing import (Optional, TypeVar)

import nfpy.Assets as Ast
import nfpy.Math as Math
import nfpy.Tools.Utilities as Ut


class BaseStrategy(metaclass=ABCMeta):
    """ Base class for strategies. The input may differ for every strategy but
        parameter names should be standardized as much as possible. The main
        output of a strategy are a series of buy/sell signals. Other outputs
        for analysis purposes may be recorded as well.

        Input:
            dt [np.ndarray]: dates array
            p [np.ndarray]: values array
            npc [int]: number of days to go back in time for the check

        Output:
            result [StrategyResult]: strategy results
            data [Optional[dict]]: optional dictionary of debug data
    """

    _LABEL = ''
    NAME = ''
    DESCRIPTION = ''

    def __init__(self, asset: Ast.TyAsset, bulk: bool, npc: Optional[int] = 0):
        self._is_bulk = bulk
        self._dt = asset.prices.index.values

        self._ts = self._extract_ts(asset)
        print(f'Base strat | {id(self._ts)}')

        self._num_p_conf = npc  # Periods to confirm a signal
        self._max_t = self._dt.shape[0]
        self._t = -1

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        self._t += 1
        if self._t < self._max_t:
            return self._signal()
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

    @staticmethod
    def _extract_ts(asset: Ast.TyAsset) -> np.ndarray:
        """ Returns the 1D or 2D time series required to use the strategy. """
        return Math.ffill_cols(asset.prices.values)

    @property
    def max_t(self) -> int:
        """ Returns the max time series index. """
        return self._max_t

    # @abstractmethod
    # def _bulk(self) -> StrategyResult:
    #     """ Strategy bulk calculation function. Should get the results from each
    #         indicator, make necessary controls and generate the series of
    #         signals.
    #     """
    #
    @abstractmethod
    def check_order_validity(self, order: tuple) -> str:
        """ Return the validity of a pending order.
             - 'execute': if the order can be executed immediately
             - 'keep': if the order cannot be executed and remains pending
             - None: if the order is not valid anymore and should be cancelled
        """

    @property
    @abstractmethod
    def min_length(self) -> int:
        """ Return the minimum amount of data required for a single signal
            generation. This represents the minimum amount of data necessary to
            run the strategy.
        """

    @abstractmethod
    def _signal(self) -> Optional[tuple]:
        """ Must return a tuple containing the generated signal in the form:
                <index, date, signal>
            If the bulk mode is used, the pre-calculate signal is returned. If
            the online mode is used, the indicator values are first returned,
            the controls made and the signal generated.
        """

    @abstractmethod
    def start(self, t0: int) -> None:
        """ Call the start() method of each indicator. """


TyStrategy = TypeVar('TyStrategy', bound=BaseStrategy)
