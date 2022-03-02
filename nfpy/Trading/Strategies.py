#
# Strategies functions
# Functions to compute buy-sell signals
# The output is a list of buy/sell signals
#

import numpy as np
from typing import (Any, Generator, Optional)

import nfpy.Math as Math

from . import Indicators as Sig
from .BaseStrategy import (BaseStrategy, StrategyResult)
from .SR import Trends as Tr


class MAStrategy(BaseStrategy):

    @staticmethod
    def _cross_sig_(dt: np.ndarray, v1: np.ndarray, v2: np.ndarray, w: int) \
            -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        v1 = Math.ffill_cols(v1)
        cross = np.diff(np.where(v1 > v2, 1, 0))
        cross[:w - 1] = 0

        mask = cross != 0
        idx = np.nonzero(mask)[0]
        signals = cross[idx]

        # Calculate returned quantities
        idx = idx + 1
        dt = dt[idx]

        return idx, dt, signals


class SMAPriceCross(MAStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the SMA and a sell signal when the price crosses below the SMA. The side
        of the SMA taken by the price is indicative of the trend.

        Input:
            dt [np.ndarray]: date series
            p [np.ndarray]: price series
            w [int]: rolling window size
            check [Optional[int]]: number of periods to confirm the signal

        Output:
            dt [np.ndarray]: date series of the signals
            signals [np.ndarray]: signals buy (+1) / sell (-1)
            ma [np.ndarray]: computed SMA series, has the same length as the
                             input price series
            trend [np.ndarray]: price trend up (+1) / sell (0)
            mask [np.ndarray]: mask of signals positions
    """

    _LABEL = 'SMA_P_Cross'
    NAME = 'SMA/Price cross'
    DESCRIPTION = f"Generates a buy signal when the price crosses above the " \
                  f"SMA and a sell signal when the price crosses below the " \
                  f"SMA. The side of the SMA taken by the price is indicative " \
                  f"of the trend."

    def __init__(self, dt: np.ndarray, p: np.ndarray,
                 w: int, npc: Optional[int] = 0):
        super().__init__(dt, p, npc)
        self._w = w

    @property
    def min_length(self) -> int:
        return self._w + self._num_p_conf

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    def _bulk(self) -> StrategyResult:
        self._ma = Sig.sma(self._p, self._w)
        return StrategyResult(
            *self._cross_sig_(self._dt, self._p, self._ma, self._w)
        )


class TwoSMACross(MAStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast SMA crosses
        above slow SMA and a sell signal when the fast SMA crosses below. The
        side of the slow SMA taken by the fast is indicative of the trend.

        Input:
            dt [np.ndarray]: date series
            p [np.ndarray]: price series
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            ma_fast [np.ndarray]: pre-computed fast SMA
            ma_slow [np.ndarray]: pre-computed slow SMA

        Output:
            dt [np.ndarray]: date series of the signals
            signals [np.ndarray]: signals buy (+1) / sell (-1)
            trend [np.ndarray]: price trend up (+1) / sell (0)
            ma_fast [np.ndarray]: computed fast SMA series, has the same length
                                  as the input price series
            ma_slow [np.ndarray]: computed slow SMA series, has the same length
                                  as the input price series
    """

    _LABEL = '2_SMA_Cross'
    NAME = '2 SMA Cross'
    DESCRIPTION = f"Generates a buy signal when the fast SMA crosses above slow " \
                  f"SMA and a sell signal when the fast SMA crosses below. The " \
                  f"side of the slow SMA taken by the fast is indicative of the " \
                  f"trend."

    def __init__(self, dt: np.ndarray, p: np.ndarray, w_fast: int,
                 w_slow: int, npc: Optional[int] = 0):
        super().__init__(dt, p, npc)
        self._wf = w_fast
        self._ws = w_slow

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    def _bulk(self) -> StrategyResult:
        self._ma_fast = Sig.sma(self._p, self._wf)
        self._ma_slow = Sig.sma(self._p, self._ws)
        return StrategyResult(
            *self._cross_sig_(self._dt, self._ma_fast, self._ma_slow, self._ws)
        )


class EMAPriceCross(MAStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the EMA and a sell signal when the price crosses below the EMA. The side
        of the EMA taken by the price is indicative of the trend.

        Input:
            dt [np.ndarray]: date series
            v [np.ndarray]: price series
            w [int]: fast rolling window size
            ma [np.ndarray]: pre-computed fast EMA

        Output:
            dt [np.ndarray]: date series of the signals
            signals [np.ndarray]: signals buy (+1) / sell (-1)
            trend [np.ndarray]: price trend up (+1) / sell (0)
            ma [np.ndarray]: computed EMA series, has the same length as the
                             input price series
    """

    _LABEL = 'EMA_P_Cross'
    NAME = 'EMA/Price Cross'
    DESCRIPTION = f"Generates a buy signal when the price crosses above the EMA " \
                  f"and a sell signal when the price crosses below the EMA. The " \
                  f"side of the EMA taken by the price is indicative of the " \
                  f"trend."

    def __init__(self, dt: np.ndarray, p: np.ndarray,
                 w: int, npc: Optional[int] = 0):
        super().__init__(dt, p, npc)
        self._w = w

    @property
    def min_length(self) -> int:
        return self._w + self._num_p_conf

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    def _bulk(self) -> StrategyResult:
        self._ma = Sig.ewma(self._p, self._w)
        return StrategyResult(
            *self._cross_sig_(self._dt, self._p, self._ma, self._w)
        )


class TwoEMACross(MAStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast EMA crosses
        above slow EMA and a sell signal when the fast SMA crosses below. The
        side of the slow EMA taken by the fast is indicative of the trend.

        Input:
            dt [np.ndarray]: date series
            v [np.ndarray]: price series
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            ma_fast [np.ndarray]: pre-computed fast EMA
            ma_slow [np.ndarray]: pre-computed slow EMA

        Output:
            dt [np.ndarray]: date series of the signals
            signals [np.ndarray]: signals buy (+1) / sell (-1)
            trend [np.ndarray]: price trend up (+1) / sell (0)
            ma_fast [np.ndarray]: computed fast EMA series, has the same length
                                  as the input price series
            ma_slow [np.ndarray]: computed slow EMA series, has the same length
                                  as the input price series
    """

    _LABEL = '2_EMA_Cross'
    NAME = '2 EMA Cross'
    DESCRIPTION = f"Generates a buy signal when the fast EMA crosses above slow " \
                  f"EMA and a sell signal when the fast EMA crosses below. The " \
                  f"side of the slow EMA taken by the fast is indicative of the " \
                  f"trend."

    def __init__(self, dt: np.ndarray, p: np.ndarray, w_fast: int,
                 w_slow: int, npc: Optional[int] = 0):
        super().__init__(dt, p, npc)
        self._wf = w_fast
        self._ws = w_slow

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    def _bulk(self) -> StrategyResult:
        self._ma_fast = Sig.ewma(self._p, self._wf)
        self._ma_slow = Sig.ewma(self._p, self._ws)
        return StrategyResult(
            *self._cross_sig_(self._dt, self._ma_fast, self._ma_slow, self._ws)
        )


class ThreeMAStrategy(BaseStrategy):

    @staticmethod
    def _3ma_swing(dt: np.ndarray, p: np.ndarray, v1: np.ndarray,
                   v2: np.ndarray, v3: np.ndarray, w: int) -> []:
        # Calculate the trend mask
        p = Math.ffill_cols(p)
        mask_tr = (p - v3) > .0

        # Calculate cross MAs
        cross_cr = np.diff(np.where(v1 > v2, 1, 0))
        cross_cr[:w - 1] = 0

        # Calculate final mask and indices
        mask = ((cross_cr == 1) & mask_tr[1:]) | \
               ((cross_cr == -1) & ~mask_tr[1:])
        idx = np.nonzero(mask)[0]
        signals = cross_cr[idx]

        # Calculate returned quantities
        idx = idx + 1
        dt = dt[idx]

        return idx, dt, signals


class ThreeSMAMomentumStrategy(ThreeMAStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast SMA crosses
        above slow SMA if the price is above the trending (longest) SMA, and a
        sell signal when the fast SMA crosses below the slow SMA and the price
        is above the trending SMA.

        Input:
            dt [np.ndarray]: date series
            v [np.ndarray]: price series
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            w_trend [int]: slowest rolling window size for general trend

        Output:
            dt [np.ndarray]: date series of the signals
            signals [np.ndarray]: signals buy (+1) / sell (-1)
            trend [np.ndarray]: price trend up (+1) / sell (0)
            ma_fast [np.ndarray]: computed fast SMA series, has the same length
                as the input price series
            ma_slow [np.ndarray]: computed slow SMA series, has the same length
                as the input price series
            ma_trend [np.ndarray]: computed trend SMA series, has the same
                length as the input price series
    """

    _LABEL = '3_SMA_Mom'
    NAME = '3 SMA Momentum Cross'
    DESCRIPTION = f"Generates a buy signal when the fast SMA crosses above slow " \
                  f"SMA if the price is above the trending (longest) SMA, and a " \
                  f"sell signal when the fast SMA crosses below the slow SMA and " \
                  f"the price is above the trending SMA."

    def __init__(self, dt: np.ndarray, p: np.ndarray, w_fast: int,
                 w_slow: int, w_trend: int, npc: Optional[int] = 0):
        super().__init__(dt, p, npc)
        self._wf = w_fast
        self._ws = w_slow
        self._wt = w_trend

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    def _bulk(self) -> StrategyResult:
        self._ma_fast = Sig.sma(self._p, self._wf)
        self._ma_slow = Sig.sma(self._p, self._ws)
        self._ma_trend = Sig.sma(self._p, self._wt)
        return StrategyResult(
            *self._3ma_swing(self._dt, self._p, self._ma_fast,
                             self._ma_slow, self._ma_trend, self._ws)
        )


class ThreeEMAMomentumStrategy(ThreeMAStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast EMA crosses
        above slow EMA if the price is above the trending (longest) EMA, and a
        sell signal when the fast EMA crosses below the slow EMA and the price
        is above the trending EMA.

        Input:
            dt [np.ndarray]: date series
            v [np.ndarray]: price series
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            w_trend [int]: slowest rolling window size for general trend

        Output:
            dt [np.ndarray]: date series of the signals
            signals [np.ndarray]: signals buy (+1) / sell (-1)
            trend [np.ndarray]: price trend up (+1) / sell (0)
            ma_fast [np.ndarray]: computed fast EMA series, has the same length
                as the input price series
            ma_slow [np.ndarray]: computed slow EMA series, has the same length
                as the input price series
            ma_slow [np.ndarray]: computed slow EMA series, has the same length
                as the input price series
    """

    _LABEL = '3_EMA_Mom'
    NAME = '3 EMA Momentum Cross'
    DESCRIPTION = f"Generates a buy signal when the fast EMA crosses above slow " \
                  f"EMA if the price is above the trending (longest) EMA, and a " \
                  f"sell signal when the fast EMA crosses below the slow EMA and " \
                  f"the price is above the trending EMA."

    def __init__(self, dt: np.ndarray, p: np.ndarray, w_fast: int,
                 w_slow: int, w_trend: int, npc: Optional[int] = 0):
        super().__init__(dt, p, npc)
        self._wf = w_fast
        self._ws = w_slow
        self._wt = w_trend

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    def _bulk(self) -> StrategyResult:
        self._ma_fast = Sig.ewma(self._p, self._wf)
        self._ma_slow = Sig.ewma(self._p, self._ws)
        self._ma_trend = Sig.ewma(self._p, self._wt)
        return StrategyResult(
            *self._3ma_swing(self._dt, self._p, self._ma_fast,
                             self._ma_slow, self._ma_trend, self._ws)
        )


class MACDHistReversalStrategy(BaseStrategy):
    _LABEL = 'MACD_Hist_Rev'
    NAME = 'MACD Histogram Reversal'
    DESCRIPTION = f"Generates a buy signal when the histogram of the MACD " \
                  f"crosses from negative to positive, and a sell signal " \
                  f"when it crosses from positive to negative. "

    def __init__(self, dt: np.ndarray, p: np.ndarray, w_fast: int, w_slow: int,
                 w_macd: int, npc: Optional[int] = 0):
        super().__init__(dt, p, npc)
        self._wm = w_macd
        self._wf = w_fast
        self._ws = w_slow

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    def _bulk(self) -> StrategyResult:
        sig = Sig.macd(self._p, self._ws, self._wf, self._wm)
        # macd, signal, hist, fast_ema, slow_ema

        cross = np.diff(np.where(sig[2] > 0, 1, 0))
        cross[:self._ws - 1] = 0
        mask = cross != 0

        # Filter signals: if the sign of the histogram does not hold longer
        # than the filtering length the signal is removed
        # mask = np.copy(mask_unf)
        # idx_prefilter = np.nonzero(mask)[0]
        # idx = []
        # for i in idx_prefilter:
        #     if np.any(cross[i + 1:i + self._filter]):
        #         mask[i] = False
        #     else:
        #         idx.append(i+1)
        # idx = np.array(idx)

        idx = np.nonzero(mask)[0] + 1
        dt = self._dt[1:][mask]
        signals = cross[mask]

        self._macd = sig[0]
        self._signal = sig[1]
        self._histogram = sig[2]
        self._ma_fast = sig[3]
        self._ma_slow = sig[4]
        return StrategyResult(idx, dt, signals)


class SRBreachStrategy(BaseStrategy):

    def __init__(self, dt: np.ndarray, p: np.ndarray, w_fast: int, w_slow: int,
                 sr_mult: float, confidence: float, npc: Optional[int] = 0):
        super().__init__(dt, p, npc)
        self._wf = w_fast
        self._ws = w_slow
        self._srm = sr_mult
        self._cnf = confidence

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf

    def _calculate_sr(self, dt: np.ndarray, p: np.ndarray) \
            -> Generator[np.ndarray, Any, None]:
        return (
            Tr.search_maxmin(
                dt[-int(w * self._srm):],
                p[-int(w * self._srm):],
                w=w, tol=1.
            )
            for w in (self._ws, self._wf)
        )

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    def _bulk(self) -> StrategyResult:
        vola = float(np.nanstd(
            Math.ret(self._p)[-self._num_p_conf:]
        ))

        # Calculate S/R lines
        sr_list = np.sort(
            np.concatenate(
                Tr.merge_sr(
                    list(self._calculate_sr(self._dt, self._p)),
                    vola
                )
            )
        )

        # Get the min and max value of the price series over the cross window
        p_c = self._p[-self._num_p_conf:]
        p_min = np.nanmin(p_c)
        p_max = np.nanmax(p_c)
        vola *= self._cnf

        # Run over S/R lines and search for lines in the price range
        idx = np.searchsorted(
            sr_list,
            (
                p_min * (1. - vola),
                p_max * (1. + vola)
            )
        )
        sr_list = sr_list[range(*idx)]
        if sr_list.shape[0] > 0:
            final = np.where(
                sr_list <= Math.next_valid_value(p_c)[0],
                sr_list / p_min - 1.,
                p_max / sr_list - 1.
            )
            breach = sr_list[np.where(final > vola)[0]]
            # testing = sr_list[np.where((-vola < final) & (final < vola))[0]]
        else:
            breach = np.empty(0)

        return StrategyResult(idx, self._dt, None)
        # return breach
