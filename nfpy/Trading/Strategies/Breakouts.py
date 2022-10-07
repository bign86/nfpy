#
# Breakout Strategies functions
# Strategies based on breakouts from channels or oscillators
#

from typing import (Callable, Optional, Sequence)

import nfpy.Assets as Ast

from .. import Indicators as Ind
from .BaseStrategy import BaseStrategy
from .Enums import (Order, Signal, SignalFlag)


class OscillatorBreakout(BaseStrategy):
    """ Generates a buy signal when the oscillator crosses above the lower
        threshold and a sell signal when it crosses below the upper threshold.

        Input:
            asset [TyAsset]: asset to trade
            indicator [Callable]: indicator function
            params [Sequence]: parameters passed to the indicator
            threshold [Sequence]: upper and lower indicator thresholds
            npc [int]: number of days to go back in time for the check

        Output:
            signals [StrategyResult]: generated signals
    """
    _LABEL = 'Oscillator_Breakout'
    NAME = 'Oscillator Breakout'
    DESCRIPTION = f""

    def __init__(self, asset: Ast.TyAsset, bulk: bool, indicator: Callable,
                 params: Sequence, threshold: tuple[float],
                 npc: Optional[int] = 0):
        super().__init__(asset, bulk, npc)
        self._thr = threshold
        self._params = params

        self._status = b''
        self._ind_f = indicator(self._ts, bulk, *params)
        self._register_indicator([self._ind_f])

    def check_order_validity(self, order: Order) -> tuple[str, int]:
        return 'execute', self._t

    def _signal(self) -> Optional[Signal]:
        osc = self._ind_f.__next__()
        signal = None

        if osc < self._thr[0]:
            self._status = b's'
        elif osc > self._thr[1]:
            self._status = b'b'
        else:
            # We are oversold ('s') and we exit ('n') => buy
            if self._status == b's':
                signal = self.raise_signal(SignalFlag.BUY)

            # We are overbought ('b') and we exit ('n') => sell
            elif self._status == b'b':
                signal = self.raise_signal(SignalFlag.BUY)
            self._status = b'n'

        return signal


class ChannelBreakout(BaseStrategy):
    """ Generates a buy signal when the price crosses above the lower band
        threshold and a sell signal when it crosses below the upper band.

        Input:
            asset [TyAsset]: asset to trade
            indicator [Callable]: indicator function
            params [Sequence]: parameters passed to the indicator
            npc [int]: number of days to go back in time for the check

        Output:
            signals [StrategyResult]: generated signals
    """
    _LABEL = 'Channel_Breakout'
    NAME = 'Channel Breakout'
    DESCRIPTION = f""

    def __init__(self, asset: Ast.TyAsset, bulk: bool, indicator: Callable,
                 params: Sequence, npc: Optional[int] = 0):
        super().__init__(asset, bulk, npc)
        self._params = params

        self._status = b''
        self._ind_f = indicator(self._ts, bulk, *params)
        self._register_indicator([self._ind_f])

    def check_order_validity(self, order: Order) -> tuple[str, int]:
        return 'execute', self._t

    def _signal(self) -> Optional[Signal]:
        high, _, low = self._ind_f.__next__()[:3]
        signal = None

        v = self._ts[self._t]
        if v < low:
            self._status = b's'
        elif v > high:
            self._status = b'b'
        else:
            # We are oversold ('s') and we exit ('n') => buy
            if self._status == b's':
                signal = self.raise_signal(SignalFlag.BUY)

            # We are overbought ('b') and we exit ('n') => sell
            elif self._status == b'b':
                signal = self.raise_signal(SignalFlag.BUY)
            self._status = b'n'

        return signal


class CCIBreakout(OscillatorBreakout):
    _LABEL = 'CCI_Breakout'
    NAME = 'CCI Breakout'
    DESCRIPTION = f""

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w: int,
                 threshold: Optional[tuple[float]] = (-100., 100.),
                 npc: Optional[int] = 0):
        super().__init__(asset, bulk, Ind.Cci, (w,), threshold, npc)


class DonchianBreakout(ChannelBreakout):
    _LABEL = 'Donchian_Breakout'
    NAME = 'Donchian Breakout'
    DESCRIPTION = f""

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w: int,
                 npc: Optional[int] = 0):
        super().__init__(asset, bulk, Ind.Donchian, (w,), npc)


class BollingerBreakout(ChannelBreakout):
    _LABEL = 'Bollinger_Breakout'
    NAME = 'Bollinger Breakout'
    DESCRIPTION = f""

    def __init__(self, asset: Ast.TyAsset, bulk: bool, w: int,
                 alpha: float, npc: Optional[int] = 0):
        super().__init__(asset, bulk, Ind.Bollinger, (w, alpha), npc)
