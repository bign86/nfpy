#
# MA Cross Strategies
# Strategies based on crossing between MAs
#

from typing import Optional

import nfpy.Assets as Ast

from .. import Indicators as Ind
from .BaseStrategy import BaseStrategy
from .Enums import (Order, Signal, SignalFlag)


class SMAPriceCross(BaseStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the SMA and a sell signal when the price crosses below the SMA. The side
        of the SMA taken by the price is indicative of the trend.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            w [int]: rolling window size
            npc [int]: number of periods to confirm the signal
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
        self._register_indicator([self._ma])

    def check_order_validity(self, order: Order) -> tuple[str, int]:
        return 'execute', self._t

    def _signal(self) -> Optional[Signal]:
        ma = self._ma.__next__()
        d_new = self._ts[self._t] - ma

        signal = None
        if d_new > .0:
            if self._status == b'b':
                signal = self.raise_signal(SignalFlag.BUY)
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                signal = self.raise_signal(SignalFlag.SELL)
            self._status = b'b'

        return signal


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
        self._register_indicator([self._maf, self._mas])

    def check_order_validity(self, order: Order) -> tuple[str, int]:
        return 'execute', self._t

    def _signal(self) -> Optional[Signal]:
        maf = self._maf.__next__()
        mas = self._mas.__next__()
        d_new = maf - mas

        signal = None
        if d_new > .0:
            if self._status == b'b':
                signal = self.raise_signal(SignalFlag.BUY)
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                signal = self.raise_signal(SignalFlag.SELL)
            self._status = b'b'

        return signal


class EMAPriceCross(BaseStrategy):
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the EMA and a sell signal when the price crosses below the EMA. The side
        of the EMA taken by the price is indicative of the trend.

        Input:
            asset [TyAsset]: asset to trade
            bulk [bool]: use the "bulk" or the "online" mode
            w [int]: fast rolling window size
            npc [int]: number of periods to confirm the signal
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
        self._register_indicator([self._ema])

    def check_order_validity(self, order: Order) -> tuple[str, int]:
        return 'execute', self._t

    def _signal(self) -> Optional[Signal]:
        ema = self._ema.__next__()
        d_new = self._ts[self._t] - ema

        signal = None
        if d_new > .0:
            if self._status == b'b':
                signal = self.raise_signal(SignalFlag.BUY)
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                signal = self.raise_signal(SignalFlag.SELL)
            self._status = b'b'

        return signal


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
        self._register_indicator([self._emaf, self._emas])

    def check_order_validity(self, order: Order) -> tuple[str, int]:
        return 'execute', self._t

    def _signal(self) -> Optional[Signal]:
        emaf = self._emaf.__next__()
        emas = self._emas.__next__()
        d_new = emaf - emas

        signal = None
        if d_new > .0:
            if self._status == b'b':
                signal = self.raise_signal(SignalFlag.BUY)
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                signal = self.raise_signal(SignalFlag.SELL)
            self._status = b'b'

        return signal


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
        self._register_indicator([self._maf, self._mas, self._mat])

    def check_order_validity(self, order: Order) -> tuple[str, int]:
        return 'execute', self._t

    def _signal(self) -> Optional[Signal]:
        maf = self._maf.__next__()
        mas = self._mas.__next__()
        mat = self._mat.__next__()
        d_new = maf - mas

        signal = None
        if d_new > .0:
            if self._status == b'b':
                if self._ts[self._t] > mat:
                    signal = self.raise_signal(SignalFlag.BUY)
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                if self._ts[self._t] < mat:
                    signal = self.raise_signal(SignalFlag.SELL)
            self._status = b'b'

        return signal


class ThreeEMAMomentumStrategy(BaseStrategy):
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
        self._register_indicator([self._emaf, self._emas, self._emat])

    def check_order_validity(self, order: Order) -> tuple[str, int]:
        return 'execute', self._t

    def _signal(self) -> Optional[Signal]:
        emaf = self._emaf.__next__()
        emas = self._emas.__next__()
        emat = self._emat.__next__()
        d_new = emaf - emas

        signal = None
        if d_new > .0:
            if self._status == b'b':
                if self._ts[self._t] > emat:
                    signal = self.raise_signal(SignalFlag.BUY)
            self._status = b'a'
        elif d_new < .0:
            if self._status == b'a':
                if self._ts[self._t] < emat:
                    signal = self.raise_signal(SignalFlag.SELL)
            self._status = b'b'

        return signal


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
        self._register_indicator([self._macd])

    def check_order_validity(self, order: Order) -> tuple[str, int]:
        return 'execute', self._t

    def _signal(self) -> Optional[Signal]:
        hist = self._macd.__next__()[2]

        signal = None
        if hist > .0:
            if self._status == b'b':
                signal = self.raise_signal(SignalFlag.BUY)
            self._status = b'a'
        elif hist < .0:
            if self._status == b'a':
                signal = self.raise_signal(SignalFlag.SELL)
            self._status = b'b'

        return signal
