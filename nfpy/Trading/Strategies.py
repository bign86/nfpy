#
# Strategies functions
# Functions to compute buy-sell signals
# The output is a list of buy/sell signals
#

import numpy as np

from . import Indicators as Sig
from .BaseStrategy import (BaseStrategy, StrategyResult)


class MAStrategy(BaseStrategy):

    @staticmethod
    def _cross_sig_(dt: np.ndarray, v1: np.ndarray, v2: np.ndarray) -> tuple:
        cross = np.where(v1 > v2, 1, 0)
        cross[1:] = np.diff(cross)
        cross[0] = 0

        mask = cross != 0
        idx = np.nonzero(mask)[0]

        # Calculate returned quantities
        dt = dt[idx]
        signals = cross[idx]

        strength = np.zeros(len(idx))
        for n, i in enumerate(idx):
            strength[n] = (v1[i + 1] - v1[i - 1])
        strength /= np.max(np.abs(strength))

        return idx, dt, signals, strength


class SMAPriceCross(MAStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the SMA and a sell signal when the price crosses below the SMA. The side
        of the SMA taken by the price is indicative of the trend.

        Input:
            dt [np.ndarray]: date series
            p [np.ndarray]: price series
            w [int]: rolling window size
            ma [np.ndarray]: pre-computed SMA

        Output:
            dt [np.ndarray]: date series of the signals
            signals [np.ndarray]: signals buy (+1) / sell (-1)
            ma [np.ndarray]: computed SMA series, has the same length as the
                             input price series
            trend [np.ndarray]: price trend up (+1) / sell (0)
            mask [np.ndarray]: mask of signals positions
    """

    def __init__(self, w: int, full_out: bool = False):
        super().__init__(full_out)
        self._w = w

    def _f(self, dt: np.ndarray, p: np.ndarray) -> tuple:
        ma = Sig.sma(p, self._w)
        res = self._cross_sig_(dt, p, ma)

        return StrategyResult(*res), {self._w: ma}


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

    def __init__(self, w_fast: int, w_slow: int, full_out: bool = False):
        super().__init__(full_out)
        self._wf = w_fast
        self._ws = w_slow

    def _f(self, dt: np.ndarray, p: np.ndarray) -> tuple:
        ma_fast = Sig.sma(p, self._wf)
        ma_slow = Sig.sma(p, self._ws)
        res = self._cross_sig_(dt, ma_fast, ma_slow)

        return StrategyResult(*res), {self._wf: ma_fast, self._ws: ma_slow}


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

    def __init__(self, w: int, full_out: bool = False):
        super().__init__(full_out)
        self._w = w

    def _f(self, dt: np.ndarray, p: np.ndarray) -> tuple:
        ma = Sig.ewma(p, self._w)
        res = self._cross_sig_(dt, p, ma)

        return StrategyResult(*res), {self._w: ma}


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

    def __init__(self, w_fast: int, w_slow: int, full_out: bool = False):
        super().__init__(full_out)
        self._wf = w_fast
        self._ws = w_slow

    def _f(self, dt: np.ndarray, p: np.ndarray) -> tuple:
        ma_fast = Sig.ewma(p, self._wf)
        ma_slow = Sig.ewma(p, self._ws)
        res = self._cross_sig_(dt, ma_fast, ma_slow)

        return StrategyResult(*res), {self._wf: ma_fast, self._ws: ma_slow}


class ThreeMAStrategy(BaseStrategy):

    @staticmethod
    def _3ma_swing(dt: np.ndarray, p: np.ndarray, v1: np.ndarray,
                   v2: np.ndarray, v3: np.ndarray) -> tuple:
        # Calculate the trend mask
        mask_tr = (p - v3) > .0

        # Calculate cross MAs
        cross_cr = np.where(v1 > v2, 1, 0)
        cross_cr[1:] = np.diff(cross_cr)
        cross_cr[0] = 0

        # Calculate final mask and indices
        mask = ((cross_cr == 1) & mask_tr) | \
               ((cross_cr == -1) & ~mask_tr)
        idx = np.nonzero(mask)[0]

        # Calculate returned quantities
        dt = dt[idx]
        signals = cross_cr[idx]

        strength = np.zeros(len(idx))
        for n, i in enumerate(idx):
            strength[n] = (v1[i + 1] - v1[i - 1]) / np.abs(p[i] - v3[i])
        strength /= np.nanmax(np.abs(strength))

        return idx, dt, signals, strength


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

    _LABEL = '3SMAMom'

    def __init__(self, w_fast: int, w_slow: int, w_trend: int,
                 full_out: bool = None):
        super().__init__(full_out)
        self._wf = w_fast
        self._ws = w_slow
        self._wt = w_trend

    def _f(self, dt: np.ndarray, p: np.ndarray) -> tuple:
        # Calculate MAs
        ma_fast = Sig.sma(p, self._wf)
        ma_slow = Sig.sma(p, self._ws)
        ma_trend = Sig.sma(p, self._wt)

        res = self._3ma_swing(dt, p, ma_fast, ma_slow, ma_trend)

        return StrategyResult(*res), {self._wf: ma_fast, self._ws: ma_slow,
                                      self._wt: ma_trend}


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
            ma_fast [np.ndarray]: pre-computed fast EMA
            ma_slow [np.ndarray]: pre-computed slow EMA
            ma_trend [np.ndarray]: pre-computed trend EMA

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

    def __init__(self, w_fast: int, w_slow: int, w_trend: int,
                 full_out: bool = None):
        super().__init__(full_out)
        self._wf = w_fast
        self._ws = w_slow
        self._wt = w_trend

    def _f(self, dt: np.ndarray, p: np.ndarray) -> tuple:
        # Calculate MAs
        ma_fast = Sig.ewma(p, self._wf)
        ma_slow = Sig.ewma(p, self._ws)
        ma_trend = Sig.ewma(p, self._wt)

        res = self._3ma_swing(dt, p, ma_fast, ma_slow, ma_trend)

        return StrategyResult(*res), {self._wf: ma_fast, self._ws: ma_slow,
                                      self._wt: ma_trend}


class MACDSwingStrategy(BaseStrategy):

    def __init__(self, w_macd: int, w_fast: int, w_slow: int, w_filter: int,
                 full_out: bool = None):
        super().__init__(full_out)
        # NOTE: common to have 9, 12, 26
        self._wm = w_macd
        self._wf = w_fast
        self._ws = w_slow
        self._filter = w_filter

    def _f(self, dt: np.ndarray, p: np.ndarray) -> tuple:
        res = Sig.macd(p, self._wm, self._wf, self._ws)
        # macd, signal, hist, fast_ema, slow_ema

        cross = np.where(res[2] > 0, 1, 0)  # res[0] > res[1]
        cross[1:] = np.diff(cross)
        cross[0] = 0

        mask_unf = cross != 0

        # Filter signals: if the sign of the histogram does not hold longer
        # than the filtering length the signal is removed
        mask = np.copy(mask_unf)
        for i in np.nonzero(mask_unf)[0]:
            if np.any(cross[i + 1:i + self._filter]):
                mask[i] = False

        dt = dt[mask]
        signals = cross[mask]
        # dt_unf = dt[mask_unf]
        # signals_unf = cross[mask_unf]

        return StrategyResult(dt, signals, None), \
               {self._wf: res[3], self._ws: res[4], 'macd': res[0],
                self._wm: res[1], 'histogram': res[3]}


class ATRStrategy(BaseStrategy):

    def __init__(self, w: int, full_out: bool = None):
        super().__init__(full_out)
        self._w = w

    def _f(self, dt: np.ndarray, p: np.ndarray) -> tuple:
        atr = Sig.atr(p, self._w)

        mask = np.empty(len(atr))
        mask[1:] = p[1:] > atr[:-1]
        mask[0] = False

        dt = dt[mask]
        signals = np.zeros(len(atr), dtype=np.int)
        signals[mask] = 1

        return StrategyResult(dt, signals, None), {self._w: atr}
