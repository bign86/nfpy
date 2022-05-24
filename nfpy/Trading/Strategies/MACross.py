#
# MA Cross Strategies
# Strategies based on crossing between MAs
#

import numpy as np
from typing import Optional

import nfpy.Assets as Ast
import nfpy.Math as Math

from .. import Indicators as Ind
from .BaseStrategy import (BaseStrategy, StrategyResult)


class SMAPriceCross(BaseStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the SMA and a sell signal when the price crosses below the SMA. The side
        of the SMA taken by the price is indicative of the trend.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            w [int]: rolling window size
            npc [int]: number of periods to confirm the signal

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = 'SMA_P_Cross'
    NAME = 'SMA/Price cross'
    DESCRIPTION = f"Generates a buy signal when the price crosses above the " \
                  f"SMA and a sell signal when the price crosses below the " \
                  f"SMA. The side of the SMA taken by the price is indicative " \
                  f"of the trend."

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w: int,
                 npc: int = 0):
        super().__init__(asset, bulk, npc)
        self._w = w

        self._status = b''
        self._ma = Ind.Sma(self._ts, bulk, w)

    def check_order_validity(self, order: tuple) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._ma.min_length + self._num_p_conf

    def _signal(self) -> Optional[tuple]:
        ma = self._ma.__next__()
        d_new = self._ts[self._t] - ma

        signal = None
        if d_new > .0:
            if self._status == b'b':
                signal = self._t, self._dt[self._t], 1  # Signal.BUY
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                signal = self._t, self._dt[self._t], -1  # Signal.SELL
            self._status = b'b'

        return signal

    def start(self, t0: int) -> None:
        self._t = t0
        self._ma.start(t0)


class TwoSMACross(BaseStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast SMA crosses
        above slow SMA and a sell signal when the fast SMA crosses below. The
        side of the slow SMA taken by the fast is indicative of the trend.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            npc [int]: number of periods to confirm the signal

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = '2_SMA_Cross'
    NAME = '2 SMA Cross'
    DESCRIPTION = f"Generates a buy signal when the fast SMA crosses above " \
                  f"slowSMA and a sell signal when the fast SMA crosses below. " \
                  f"The side of the slow SMA taken by the fast is indicative " \
                  f"of the trend."

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w_fast: int,
                 w_slow: int, npc: Optional[int] = 0):
        super().__init__(asset, bulk, npc)
        self._wf = w_fast
        self._ws = w_slow

        self._status = b''
        self._maf = Ind.Sma(self._ts, bulk, w_fast)
        self._mas = Ind.Sma(self._ts, bulk, w_slow)

    def check_order_validity(self, order: tuple) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._mas.min_length + self._num_p_conf

    def _signal(self) -> Optional[tuple]:
        maf = self._maf.__next__()
        mas = self._mas.__next__()
        d_new = maf - mas

        signal = None
        if d_new > .0:
            if self._status == b'b':
                signal = self._t, self._dt[self._t], 1  # Signal.BUY
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                signal = self._t, self._dt[self._t], -1  # Signal.SELL
            self._status = b'b'

        return signal

    def start(self, t0: int) -> None:
        self._t = t0
        self._maf.start(t0)
        self._mas.start(t0)


class EMAPriceCross(BaseStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the EMA and a sell signal when the price crosses below the EMA. The side
        of the EMA taken by the price is indicative of the trend.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            w [int]: fast rolling window size
            npc [int]: number of periods to confirm the signal

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = 'EMA_P_Cross'
    NAME = 'EMA/Price Cross'
    DESCRIPTION = f"Generates a buy signal when the price crosses above the " \
                  f"EMA and a sell signal when the price crosses below the " \
                  f"EMA. The side of the EMA taken by the price is indicative " \
                  f"of the trend."

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w: int,
                 npc: Optional[int] = 0):
        super().__init__(asset, bulk, npc)
        self._w = w

        self._status = b''
        self._ema = Ind.Ewma(self._ts, bulk, w)

    def check_order_validity(self, order: tuple) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._ema.min_length + self._num_p_conf

    def _signal(self) -> Optional[tuple]:
        ema = self._ema.__next__()
        d_new = self._ts[self._t] - ema

        signal = None
        if d_new > .0:
            if self._status == b'b':
                signal = self._t, self._dt[self._t], 1  # Signal.BUY
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                signal = self._t, self._dt[self._t], -1  # Signal.SELL
            self._status = b'b'

        return signal

    def start(self, t0: int) -> None:
        self._t = t0
        self._ema.start(t0)


class TwoEMACross(BaseStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast EMA crosses
        above slow EMA and a sell signal when the fast SMA crosses below. The
        side of the slow EMA taken by the fast is indicative of the trend.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            npc [int]: number of periods to confirm the signal

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = '2_EMA_Cross'
    NAME = '2 EMA Cross'
    DESCRIPTION = f"Generates a buy signal when the fast EMA crosses above " \
                  f"slow EMA and a sell signal when the fast EMA crosses below. " \
                  f"The side of the slow EMA taken by the fast is indicative " \
                  f"of the trend."

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w_fast: int,
                 w_slow: int, npc: Optional[int] = 0):
        super().__init__(asset, bulk, npc)
        self._wf = w_fast
        self._ws = w_slow

        self._status = b''
        self._emaf = Ind.Ewma(self._ts, bulk, w_fast)
        self._emas = Ind.Ewma(self._ts, bulk, w_slow)

    def check_order_validity(self, order: tuple) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._emas.min_length + self._num_p_conf

    def _signal(self) -> Optional[tuple]:
        emaf = self._emaf.__next__()
        emas = self._emas.__next__()
        d_new = emaf - emas

        signal = None
        if d_new > .0:
            if self._status == b'b':
                signal = self._t, self._dt[self._t], 1  # Signal.BUY
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                signal = self._t, self._dt[self._t], -1  # Signal.SELL
            self._status = b'b'

        return signal

    def start(self, t0: int) -> None:
        self._t = t0
        self._emaf.start(t0)
        self._emas.start(t0)


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


class ThreeSMAMomentumStrategy(BaseStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast SMA crosses
        above slow SMA if the price is above the trending (longest) SMA, and a
        sell signal when the fast SMA crosses below the slow SMA and the price
        is above the trending SMA.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            w_trend [int]: slowest rolling window size for general trend
            npc [int]: number of periods to confirm the signal

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = '3_SMA_Mom'
    NAME = '3 SMA Momentum Cross'
    DESCRIPTION = f"Generates a buy signal when the fast SMA crosses above " \
                  f"slow SMA if the price is above the trending (longest) SMA, " \
                  f"and a sell signal when the fast SMA crosses below the slow " \
                  f"SMA and the price is above the trending SMA."

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w_fast: int,
                 w_slow: int, w_trend: int, npc: Optional[int] = 0):
        super().__init__(asset, bulk, npc)
        self._wf = w_fast
        self._ws = w_slow
        self._wt = w_trend

        self._status = b''
        self._maf = Ind.Sma(self._ts, bulk, w_fast)
        self._mas = Ind.Sma(self._ts, bulk, w_slow)
        self._mat = Ind.Sma(self._ts, bulk, w_trend)

    def check_order_validity(self, order: tuple) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._mas.min_length + self._num_p_conf

    def _signal(self) -> Optional[tuple]:
        maf = self._maf.__next__()
        mas = self._mas.__next__()
        mat = self._mat.__next__()
        d_new = maf - mas

        signal = None
        if d_new > .0:
            if self._status == b'b':
                if self._ts[self._t] > mat:
                    signal = self._t, self._dt[self._t], 1  # Signal.BUY
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                if self._ts[self._t] < mat:
                    signal = self._t, self._dt[self._t], -1  # Signal.SELL
            self._status = b'b'

        return signal

    def start(self, t0: int) -> None:
        self._t = t0
        self._maf.start(t0)
        self._mas.start(t0)
        self._mat.start(t0)


class ThreeEMAMomentumStrategy(ThreeMAStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the fast EMA crosses
        above slow EMA if the price is above the trending (longest) EMA, and a
        sell signal when the fast EMA crosses below the slow EMA and the price
        is above the trending EMA.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            w_trend [int]: slowest rolling window size for general trend
            npc [int]: number of periods to confirm the signal

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = '3_EMA_Mom'
    NAME = '3 EMA Momentum Cross'
    DESCRIPTION = f"Generates a buy signal when the fast EMA crosses above " \
                  f"slow EMA if the price is above the trending (longest) EMA, " \
                  f"and a sell signal when the fast EMA crosses below the " \
                  f"slow EMA and the price is above the trending EMA."

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w_fast: int,
                 w_slow: int, w_trend: int, npc: Optional[int] = 0):
        super().__init__(asset, bulk, npc)
        self._wf = w_fast
        self._ws = w_slow
        self._wt = w_trend

        self._status = b''
        self._emaf = Ind.Ewma(self._ts, bulk, w_fast)
        self._emas = Ind.Ewma(self._ts, bulk, w_slow)
        self._emat = Ind.Ewma(self._ts, bulk, w_trend)

    def check_order_validity(self, order: tuple) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._emas.min_length + self._num_p_conf

    def _signal(self) -> Optional[tuple]:
        emaf = self._emaf.__next__()
        emas = self._emas.__next__()
        emat = self._emat.__next__()
        d_new = emaf - emas

        signal = None
        if d_new > .0:
            if self._status == b'b':
                if self._ts[self._t] > emat:
                    signal = self._t, self._dt[self._t], 1  # Signal.BUY
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                if self._ts[self._t] < emat:
                    signal = self._t, self._dt[self._t], -1  # Signal.SELL
            self._status = b'b'

        return signal

    def start(self, t0: int) -> None:
        self._t = t0
        self._emaf.start(t0)
        self._emas.start(t0)
        self._emat.start(t0)


class MACDHistReversalStrategy(BaseStrategy):
    """ Generates a buy signal when the MACD histogram crosses into positive
        and a sell signal when it crosses into negative.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            w_fast [int]: fast rolling window size
            w_slow [int]: slow rolling window size
            w_trend [int]: slowest rolling window size for general trend
            npc [int]: number of periods to confirm the signal

        Output:
            signals [StrategyResult]: generated signals
    """

    _LABEL = 'MACD_Hist_Rev'
    NAME = 'MACD Histogram Reversal'
    DESCRIPTION = f"Generates a buy signal when the histogram of the MACD " \
                  f"crosses from negative to positive, and a sell signal " \
                  f"when it crosses from positive to negative. "

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w_fast: int,
                 w_slow: int, w_macd: int, npc: Optional[int] = 0):
        super().__init__(asset, bulk, npc)
        self._wf = w_fast
        self._ws = w_slow
        self._wm = w_macd

        self._status = b''
        self._macd = Ind.Macd(self._ts, bulk, w_slow, w_fast, w_macd)

    def check_order_validity(self, order: tuple) -> str:
        return 'execute'

    @property
    def min_length(self) -> int:
        return self._macd.min_length + self._num_p_conf

    def _signal(self) -> Optional[tuple]:
        hist = self._macd.__next__()[2]

        signal = None
        if hist > .0:
            if self._status == b'b':
                signal = self._t, self._dt[self._t], 1  # Signal.BUY
            self._status = b'a'
        elif hist < .0:
            if self._status == b'a':
                signal = self._t, self._dt[self._t], -1  # Signal.SELL
            self._status = b'b'

        return signal

    def start(self, t0: int) -> None:
        self._t = t0
        self._macd.start(t0)
