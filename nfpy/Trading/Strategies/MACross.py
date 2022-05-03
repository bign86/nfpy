#
# MA Cross Strategies
# Strategies based on crossing between MAs
#

import numpy as np
from typing import Optional

import nfpy.Math as Math

from .. import Indicators as Ind
from .BaseStrategy import (BaseStrategy, StrategyResult)


class MACrossStrategy(BaseStrategy):

    @staticmethod
    def _2ma_swing_(dt: np.ndarray, v1: np.ndarray, v2: np.ndarray, w: int) \
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


class SMAPriceCross(MACrossStrategy):
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

    _LABEL = 'SMA_P_Cross'
    NAME = 'SMA/Price cross'
    DESCRIPTION = f"Generates a buy signal when the price crosses above the " \
                  f"SMA and a sell signal when the price crosses below the " \
                  f"SMA. The side of the SMA taken by the price is indicative " \
                  f"of the trend."

    def __init__(self, dt: np.ndarray, ts: np.ndarray, w: int,
                 npc: Optional[int] = 0):
        super().__init__(dt, ts, npc)
        self._w = w

    def _bulk(self) -> StrategyResult:
        ts = self._ts.reshape((self._ts.shape[1],))
        self._ma = Ind.sma(ts, self._w)
        return StrategyResult(
            *self._2ma_swing_(self._dt, ts, self._ma, self._w)
        )

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._w + self._num_p_conf


class TwoSMACross(MACrossStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast SMA crosses
        above slow SMA and a sell signal when the fast SMA crosses below. The
        side of the slow SMA taken by the fast is indicative of the trend.

        Input:
            dt [np.ndarray]: date series
            ts [np.ndarray]: price series
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            ma_fast [np.ndarray]: pre-computed fast SMA
            ma_slow [np.ndarray]: pre-computed slow SMA

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = '2_SMA_Cross'
    NAME = '2 SMA Cross'
    DESCRIPTION = f"Generates a buy signal when the fast SMA crosses above " \
                  f"slowSMA and a sell signal when the fast SMA crosses below. " \
                  f"The side of the slow SMA taken by the fast is indicative " \
                  f"of the trend."

    def __init__(self, dt: np.ndarray, ts: np.ndarray, w_fast: int,
                 w_slow: int, npc: Optional[int] = 0):
        super().__init__(dt, ts, npc)
        self._wf = w_fast
        self._ws = w_slow

    def _bulk(self) -> StrategyResult:
        ts = self._ts.reshape((self._ts.shape[1],))
        self._ma_fast = Ind.sma(ts, self._wf)
        self._ma_slow = Ind.sma(ts, self._ws)
        return StrategyResult(
            *self._2ma_swing_(self._dt, self._ma_fast, self._ma_slow, self._ws)
        )

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf


class EMAPriceCross(MACrossStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the EMA and a sell signal when the price crosses below the EMA. The side
        of the EMA taken by the price is indicative of the trend.

        Input:
            dt [np.ndarray]: date series
            ts [np.ndarray]: price series
            w [int]: fast rolling window size
            ma [np.ndarray]: pre-computed fast EMA

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = 'EMA_P_Cross'
    NAME = 'EMA/Price Cross'
    DESCRIPTION = f"Generates a buy signal when the price crosses above the " \
                  f"EMA and a sell signal when the price crosses below the " \
                  f"EMA. The side of the EMA taken by the price is indicative " \
                  f"of the trend."

    def __init__(self, dt: np.ndarray, ts: np.ndarray,
                 w: int, npc: Optional[int] = 0):
        super().__init__(dt, ts, npc)
        self._w = w

    def _bulk(self) -> StrategyResult:
        ts = self._ts.reshape((self._ts.shape[1],))
        self._ma = Ind.ewma(ts, self._w)
        return StrategyResult(
            *self._2ma_swing_(self._dt, ts, self._ma, self._w)
        )

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._w + self._num_p_conf


class TwoEMACross(MACrossStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast EMA crosses
        above slow EMA and a sell signal when the fast SMA crosses below. The
        side of the slow EMA taken by the fast is indicative of the trend.

        Input:
            dt [np.ndarray]: date series
            ts [np.ndarray]: price series
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            ma_fast [np.ndarray]: pre-computed fast EMA
            ma_slow [np.ndarray]: pre-computed slow EMA

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = '2_EMA_Cross'
    NAME = '2 EMA Cross'
    DESCRIPTION = f"Generates a buy signal when the fast EMA crosses above " \
                  f"slow EMA and a sell signal when the fast EMA crosses below. " \
                  f"The side of the slow EMA taken by the fast is indicative " \
                  f"of the trend."

    def __init__(self, dt: np.ndarray, ts: np.ndarray, w_fast: int,
                 w_slow: int, npc: Optional[int] = 0):
        super().__init__(dt, ts, npc)
        self._wf = w_fast
        self._ws = w_slow

    def _bulk(self) -> StrategyResult:
        ts = self._ts.reshape((self._ts.shape[1],))
        self._ma_fast = Ind.ewma(ts, self._wf)
        self._ma_slow = Ind.ewma(ts, self._ws)
        return StrategyResult(
            *self._2ma_swing_(self._dt, self._ma_fast, self._ma_slow, self._ws)
        )

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf


class ThreeMAStrategy(BaseStrategy):

    @staticmethod
    def _3ma_swing_(dt: np.ndarray, p: np.ndarray, v1: np.ndarray,
                    v2: np.ndarray, v3: np.ndarray, w: int) -> tuple:
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
            ts [np.ndarray]: price series
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            w_trend [int]: slowest rolling window size for general trend

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = '3_SMA_Mom'
    NAME = '3 SMA Momentum Cross'
    DESCRIPTION = f"Generates a buy signal when the fast SMA crosses above " \
                  f"slow SMA if the price is above the trending (longest) SMA, " \
                  f"and a sell signal when the fast SMA crosses below the slow " \
                  f"SMA and the price is above the trending SMA."

    def __init__(self, dt: np.ndarray, ts: np.ndarray, w_fast: int,
                 w_slow: int, w_trend: int, npc: Optional[int] = 0):
        super().__init__(dt, ts, npc)
        self._wf = w_fast
        self._ws = w_slow
        self._wt = w_trend

    def _bulk(self) -> StrategyResult:
        ts = self._ts.reshape((self._ts.shape[1],))
        self._ma_fast = Ind.sma(ts, self._wf)
        self._ma_slow = Ind.sma(ts, self._ws)
        self._ma_trend = Ind.sma(ts, self._wt)
        return StrategyResult(
            *self._3ma_swing_(self._dt, ts, self._ma_fast,
                              self._ma_slow, self._ma_trend, self._ws)
        )

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf


class ThreeEMAMomentumStrategy(ThreeMAStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast EMA crosses
        above slow EMA if the price is above the trending (longest) EMA, and a
        sell signal when the fast EMA crosses below the slow EMA and the price
        is above the trending EMA.

        Input:
            dt [np.ndarray]: date series
            ts [np.ndarray]: price series
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            w_trend [int]: slowest rolling window size for general trend

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = '3_EMA_Mom'
    NAME = '3 EMA Momentum Cross'
    DESCRIPTION = f"Generates a buy signal when the fast EMA crosses above " \
                  f"slow EMA if the price is above the trending (longest) EMA, " \
                  f"and a sell signal when the fast EMA crosses below the " \
                  f"slow EMA and the price is above the trending EMA."

    def __init__(self, dt: np.ndarray, ts: np.ndarray, w_fast: int,
                 w_slow: int, w_trend: int, npc: Optional[int] = 0):
        super().__init__(dt, ts, npc)
        self._wf = w_fast
        self._ws = w_slow
        self._wt = w_trend

    def _bulk(self) -> StrategyResult:
        ts = self._ts.reshape((self._ts.shape[1],))
        self._ma_fast = Ind.ewma(ts, self._wf)
        self._ma_slow = Ind.ewma(ts, self._ws)
        self._ma_trend = Ind.ewma(ts, self._wt)
        return StrategyResult(
            *self._3ma_swing_(self._dt, ts, self._ma_fast,
                              self._ma_slow, self._ma_trend, self._ws)
        )

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf


class MACDHistReversalStrategy(BaseStrategy):
    """ Generates a buy signal when the MACD histogram crosses into positive
        and a sell signal when it crosses into negative.

        Input:
            dt [np.ndarray]: date series
            ts [np.ndarray]: price series
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            w_trend [int]: slowest rolling window size for general trend

        Output:
            signals [StrategyResult]: generated signals
    """
    _LABEL = 'MACD_Hist_Rev'
    NAME = 'MACD Histogram Reversal'
    DESCRIPTION = f"Generates a buy signal when the histogram of the MACD " \
                  f"crosses from negative to positive, and a sell signal " \
                  f"when it crosses from positive to negative. "

    def __init__(self, dt: np.ndarray, ts: np.ndarray, w_fast: int, w_slow: int,
                 w_macd: int, npc: Optional[int] = 0):
        super().__init__(dt, ts, npc)
        self._wm = w_macd
        self._wf = w_fast
        self._ws = w_slow

    def _bulk(self) -> StrategyResult:
        ts = self._ts.reshape((self._ts.shape[1],))
        sig = Ind.macd(ts, self._ws, self._wf, self._wm)
        # macd, signal, hist, fast_ema, slow_ema = sig

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

    def _f(self, i: int) -> tuple:
        return -999,

    def check_order_validity(self, order: list) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._ws + self._num_p_conf
