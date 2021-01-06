#
# Strategies functions
# Functions to compute buy-sell signals
# The output is a list of buy/sell signals
#

import pandas as pd
import numpy as np

import nfpy.Trading.Signals as Sig


def sma_price_cross(v: pd.Series, w: int = 25) -> tuple:
    _sma = Sig.sma(v, w)

    cross = pd.Series(np.where(v > _sma, 1, 0), index=v.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    return _sma, signals


def two_sma_cross(v: pd.Series, fast: int = 25, slow: int = 100) -> tuple:
    fast_sma = Sig.sma(v, fast)
    slow_sma = Sig.sma(v, slow)

    cross = pd.Series(np.where(fast_sma > slow_sma, 1, 0), index=v.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    return fast_sma, slow_sma, signals


def ema_price_cross(v: pd.Series, w: int = 25) -> tuple:
    _ema = Sig.ewma(v, w)

    cross = pd.Series(np.where(v > _ema, 1, 0), index=v.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    return _ema, signals


def two_ema_cross(v: pd.Series, fast: int = 9, slow: int = 21) -> tuple:
    fast_ema = Sig.ewma(v, fast)
    slow_ema = Sig.ewma(v, slow)

    cross = pd.Series(np.where(fast_ema > slow_ema, 1, 0), index=v.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    return fast_ema, slow_ema, signals


def momentum_swing(v: pd.Series, fast: int = 8, slow: int = 25,
                   trend: int = 200, ma_type: str = 'ewma') -> tuple:
    if ma_type == 'ewma':
        _crossf = two_ema_cross
        _smaf = Sig.sma
    elif ma_type == 'sma':
        _crossf = two_sma_cross
        _smaf = Sig.ewma
    else:
        raise ValueError('Moving average type {} not recognized'.format(ma_type))

    fast_sma, slow_sma, signals = _crossf(v, fast, slow)
    trend_sma = _smaf(v, trend)
    trend_sig = (v - trend_sma).loc[signals.index]

    idxnan = trend_sig[np.isnan(trend_sig)].index
    idx1 = signals[(signals > 0.) & (trend_sig > 0.)].index
    idx2 = signals[(signals < 0.) & (trend_sig < 0.)].index
    signals.drop(idxnan, inplace=True)
    signals.drop(idx1, inplace=True)
    signals.drop(idx2, inplace=True)

    last = None
    idxdrop = []
    for i, sig in signals.iteritems():
        if sig == last:
            idxdrop.append(i)
        last = sig
    signals.drop(idxdrop, inplace=True)

    return fast_sma, slow_sma, trend_sma, signals


def macd_swing(v: pd.Series, fast: int = 50, slow: int = 200,
               wmacd: int = 40) -> tuple:
    macd_line, signal_line, histogram, _, _ = Sig.macd(v, fast, slow, wmacd)

    cross = pd.Series(np.where(macd_line > signal_line, 1, 0), index=v.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    trigger = signal_line.loc[signals.index]

    idxnan = trigger[np.isnan(trigger)].index
    idx1 = signals[(signals > 0.) & (trigger > 0.)].index
    idx2 = signals[(signals < 0.) & (trigger < 0.)].index
    signals.drop(idxnan, inplace=True)
    signals.drop(idx1, inplace=True)
    signals.drop(idx2, inplace=True)

    last = None
    idxdrop = []
    for i, sig in signals.iteritems():
        if sig == last:
            idxdrop.append(i)
        last = sig
    signals.drop(idxdrop, inplace=True)

    return macd_line, signal_line, signals
